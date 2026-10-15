"""Deterministic, uniform hash selection from the published universe.

Only organisation numbers are evaluator inputs; names and benchmark answers
are never substituted by the batch runner. No competitor data is read.
"""
import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from signalpost.batch import atomic_json, write_jsonl

ARCHIVE_SHA = "1c89710e5b01f8617e86d09fbdff4a52f2f8dbbba297e74f7164b5984f5a0384"
CONTENT_SHA = "b82d6a3e7231d1759a958c282bc4366b80ec2fab8095053d8ed7fa9cd01bc838"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--universe", required=True)
    p.add_argument("--output", default="data/inputs")
    p.add_argument("--seed", default="20261015-signalpost-v1")
    args=p.parse_args()
    archive=Path(args.universe).read_bytes()
    assert hashlib.sha256(archive).hexdigest()==ARCHIVE_SHA
    content=gzip.decompress(archive)
    assert hashlib.sha256(content).hexdigest()==CONTENT_SHA
    rows=[json.loads(line) for line in content.splitlines() if line]
    assert len(rows)==411160
    rows.sort(key=lambda r:hashlib.sha256((args.seed+":"+r["organisation_number"]).encode()).digest())
    slices={"smoke-100":rows[:100],"scale-1000":rows[100:1100],"untouched-validation-20":rows[1100:1120]}
    out=Path(args.output)
    metadata={"seed":args.seed,"method":"Ascending SHA-256(seed + ':' + organisation_number), first 1120 rows, disjoint slices; no prominence or website filtering",
              "universe_archive_sha256":ARCHIVE_SHA,"universe_content_sha256":CONTENT_SHA,"population":len(rows),"slices":{}}
    for name,selected in slices.items():
        path=out/(name+'.jsonl')
        write_jsonl(path,[{"organisation_number":r["organisation_number"],"id":name+":"+str(i),"evaluation_split":name} for i,r in enumerate(selected)])
        metadata["slices"][name]={"count":len(selected),"input_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "legal_forms":dict(Counter(r["legal_form"] for r in selected)),"registry_listed_websites":sum(bool(r.get("website")) for r in selected),
                "employee_bands":dict(Counter("unknown" if r["employees"] is None else "0" if r["employees"]==0 else "1-4" if r["employees"]<5 else "5-19" if r["employees"]<20 else "20+" for r in selected)),
                "industry_divisions":dict(Counter(str(r.get("industry_code") or "unknown").split('.')[0] for r in selected))}
    atomic_json(out/'selection.json',metadata)
    print(json.dumps(metadata,indent=2))


if __name__=='__main__': main()
