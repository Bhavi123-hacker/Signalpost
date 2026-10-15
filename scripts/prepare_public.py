"""Explicit development-only downloads from fixed public official URLs.

Not imported by the evaluator. All preparation HTTP starts (including redirects)
are logged separately from measured research runs. No downloaded code is executed.
"""
import argparse
import gzip
import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "private" / "preparation"


class LoggedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        log({"event": "redirect", "from": req.full_url, "to": newurl, "status": code})
        if not newurl.startswith("https://"):
            raise ValueError("Only HTTPS preparation redirects permitted")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def log(row):
    DEST.mkdir(parents=True, exist_ok=True)
    with (DEST / "requests.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now(UTC).isoformat(), **row}) + "\n")


def download(name, url, maximum=300_000_000):
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / name
    if target.exists() and target.with_suffix(target.suffix + ".metadata.json").exists():
        return target
    log({"event": "request", "url": url})
    opener = urllib.request.build_opener(LoggedRedirect())
    req = urllib.request.Request(url, headers={"User-Agent": "SignalpostResearch/1.0"})
    hasher, total = hashlib.sha256(), 0
    temporary = target.with_suffix(target.suffix + ".part")
    with opener.open(req, timeout=120) as r, temporary.open("wb") as f:
        while chunk := r.read(1024 * 1024):
            total += len(chunk)
            if total > maximum:
                raise ValueError("Preparation download size cap")
            hasher.update(chunk)
            f.write(chunk)
        meta = {"url": url, "final_url": r.url, "retrieved_at": datetime.now(UTC).isoformat(), "sha256": hasher.hexdigest(), "bytes": total,
                "headers": {k: v for k, v in r.headers.items() if k.lower() in {"etag", "last-modified", "content-length", "content-type", "content-disposition"}}}
    temporary.replace(target)
    target.with_suffix(target.suffix + ".metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta))
    return target


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["bulk", "universe", "accounts-docs", "official-api-tree", "learning"])
    args = p.parse_args()
    sources = {
        "bulk": ("brreg-enheter.csv.gz", "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv"),
        "universe": ("universe.jsonl.gz", "https://www.builderr.ai/signalpost-company-universe-2025.jsonl.gz"),
        "accounts-docs": ("accounts-openapi.json", "https://data.brreg.no/regnskapsregisteret/regnskap/v3/api-docs"),
        "official-api-tree": ("official-api-tree.json", "https://api.github.com/repos/brreg/regnskapsregister-api/git/trees/main?recursive=1"),
        "learning": ("signalpost-learning-harness.md", "https://www.builderr.ai/starter-briefs/signalpost-learning-harness.md"),
    }
    path = download(*sources[args.kind])
    if args.kind == "universe":
        raw = gzip.decompress(path.read_bytes())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == "1c89710e5b01f8617e86d09fbdff4a52f2f8dbbba297e74f7164b5984f5a0384"
        assert hashlib.sha256(raw).hexdigest() == "b82d6a3e7231d1759a958c282bc4366b80ec2fab8095053d8ed7fa9cd01bc838"
        print("Verified", len(raw.splitlines()), "universe rows")
