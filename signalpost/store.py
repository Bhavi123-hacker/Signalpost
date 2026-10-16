from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import canonical, digest, utcnow


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "evidence").mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / "signalpost.sqlite")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY, metadata TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cache(url TEXT PRIMARY KEY, snapshot_id TEXT, etag TEXT, modified TEXT, checked TEXT);
        CREATE TABLE IF NOT EXISTS observations(org TEXT, claim_id TEXT, value_hash TEXT, claim TEXT,
          first_seen TEXT, last_checked TEXT, PRIMARY KEY(org,claim_id,value_hash));
        CREATE TABLE IF NOT EXISTS current_profiles(org TEXT PRIMARY KEY, envelope TEXT);
        CREATE TABLE IF NOT EXISTS history(org TEXT, run_id TEXT, envelope TEXT, PRIMARY KEY(org,run_id));
        CREATE TABLE IF NOT EXISTS checkpoints(run_id TEXT, input_hash TEXT, org TEXT, envelope TEXT,
          PRIMARY KEY(run_id,input_hash,org));
        CREATE TABLE IF NOT EXISTS run_reports(run_id TEXT PRIMARY KEY, report TEXT);
        CREATE TABLE IF NOT EXISTS tombstones(org TEXT PRIMARY KEY, checked_at TEXT, reason TEXT);
        CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, input_hash TEXT, config_hash TEXT, started_at TEXT);
        CREATE TABLE IF NOT EXISTS request_journal(run_id TEXT, request_number INTEGER, host TEXT, company TEXT, reserved_at TEXT,
          PRIMARY KEY(run_id, request_number));
        """)

    def blob(self, data: bytes) -> tuple[str, str]:
        sha = digest(data)
        ref = f"evidence/{sha[:2]}/{sha}.bin"
        path = self.root / ref
        if not path.exists():
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data)
        return sha, ref

    def snapshot(self, metadata: dict, data: bytes) -> dict:
        sha, ref = self.blob(data)
        record = {**metadata, "content_sha256": sha, "storage_ref": ref}
        record["id"] = "snapshot-" + digest(canonical(record).encode())[:24]
        self.db.execute("INSERT OR IGNORE INTO snapshots VALUES(?,?)", (record["id"], canonical(record)))
        self.db.commit()
        return record

    def cache(self, url: str) -> dict | None:
        row = self.db.execute("SELECT snapshot_id,etag,modified,checked FROM cache WHERE url=?", (url,)).fetchone()
        if not row:
            return None
        s = self.db.execute("SELECT metadata FROM snapshots WHERE id=?", (row[0],)).fetchone()
        if not s:
            return None
        return {"snapshot": json.loads(s[0]), "etag": row[1], "modified": row[2], "checked": row[3]}

    def set_cache(self, url: str, snapshot: dict, headers: dict):
        self.db.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?,?,?)", (url, snapshot["id"], headers.get("etag"), headers.get("last-modified"), utcnow()))
        self.db.commit()

    def load(self, org: str) -> dict | None:
        row = self.db.execute("SELECT envelope FROM current_profiles WHERE org=?", (org,)).fetchone()
        return json.loads(row[0]) if row else None

    def checkpoint(self, run_id: str, input_hash: str, org: str) -> dict | None:
        row = self.db.execute("SELECT envelope FROM checkpoints WHERE run_id=? AND input_hash=? AND org=?", (run_id, input_hash, org)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, envelope: dict, input_hash: str):
        org = envelope["organisation_number"]
        run_id = envelope["run_id"]
        previous = self.load(org)
        old = {c["id"]: c for c in (previous or {}).get("claims", []) if c["availability"] == "available"}
        changes = []
        for claim in envelope["claims"]:
            if claim["availability"] != "available":
                continue
            vh = digest(canonical(claim["value"]).encode())
            row = self.db.execute("SELECT first_seen FROM observations WHERE org=? AND claim_id=? AND value_hash=?", (org, claim["id"], vh)).fetchone()
            claim["first_seen"] = row[0] if row else claim["last_checked"]
            # Stale carry-forward is not a successful observation or a change.
            if not claim.get("stale"):
                self.db.execute("INSERT INTO observations VALUES(?,?,?,?,?,?) ON CONFLICT(org,claim_id,value_hash) DO UPDATE SET last_checked=excluded.last_checked,claim=excluded.claim", (org, claim["id"], vh, canonical(claim), claim["first_seen"], claim["last_checked"]))
                before = old.get(claim["id"])
                if before is None or canonical(before["value"]) != canonical(claim["value"]):
                    changes.append({"claim_id": claim["id"], "field": claim["field"], "type": "added" if before is None else "changed", "previous": before, "current": claim})
        # A value is removed only when its source was successfully checked and explicitly absent.
        for claim in envelope["claims"]:
            if claim.get('retracted') and claim['id'] in old and claim.get('evidence_ids'):
                changes.append({'claim_id':claim['id'],'field':claim['field'],'type':'retracted','previous':old[claim['id']],'current':claim})
            if claim["availability"] == "not_available" and claim["id"] in old and claim.get("evidence_ids"):
                changes.append({"claim_id": claim["id"], "field": claim["field"], "type": "removed", "previous": old[claim["id"]], "current": claim})
        envelope["changes"] = changes
        # A change publishes a previous value too: retain its actual evidence in
        # this envelope as well as in the immutable prior history entry.
        required_old = {eid for change in changes for eid in (change.get('previous') or {}).get('evidence_ids', [])}
        existing = {e['id'] for e in envelope['evidence']}
        for e in (previous or {}).get('evidence', []):
            if e['id'] in required_old and e['id'] not in existing:
                envelope['evidence'].append(e)
                existing.add(e['id'])
        old_hashes = {e['content_sha256'] for e in envelope['evidence'] if e['id'] in required_old}
        snapshots = {s['id'] for s in envelope['source_snapshots']}
        for snapshot in (previous or {}).get('source_snapshots', []):
            if snapshot['content_sha256'] in old_hashes and snapshot['id'] not in snapshots:
                envelope['source_snapshots'].append(snapshot)
                snapshots.add(snapshot['id'])
        body = canonical(envelope)
        self.db.execute("INSERT OR REPLACE INTO current_profiles VALUES(?,?)", (org, body))
        self.db.execute("INSERT OR REPLACE INTO history VALUES(?,?,?)", (org, run_id, body))
        self.db.execute("INSERT OR REPLACE INTO checkpoints VALUES(?,?,?,?)", (run_id, input_hash, org, body))
        self.db.commit()
        return envelope

    def close(self):
        self.db.close()

    def legal_removal(self, org: str):
        """BRREG 410 is an explicit legal-removal request, unlike a failed refresh.

        Remove only this company's cached observations/history. Keep an identifier-only
        tombstone; never alter the evaluator's input snapshot or unrelated files.
        """
        from .models import org_number
        org_number(org)
        envelopes = [json.loads(row[0]) for row in self.db.execute("SELECT envelope FROM history WHERE org=?", (org,))]
        refs = {e["storage_ref"] for row in envelopes for e in row.get("evidence", [])}
        for table in ("current_profiles", "history", "observations", "checkpoints"):
            self.db.execute(f"DELETE FROM {table} WHERE org=?", (org,))
        for url, in self.db.execute("SELECT url FROM cache").fetchall():
            if org in url:
                self.db.execute("DELETE FROM cache WHERE url=?", (url,))
        other_bodies = [r[0] for r in self.db.execute("SELECT envelope FROM history")]
        for ref in refs:
            if any(ref in body for body in other_bodies):
                continue
            path = (self.root / ref).resolve()
            if path.is_relative_to((self.root / "evidence").resolve()) and path.is_file():
                path.unlink()
            for sid, metadata in self.db.execute("SELECT id,metadata FROM snapshots").fetchall():
                if json.loads(metadata).get("storage_ref") == ref:
                    self.db.execute("DELETE FROM snapshots WHERE id=?", (sid,))
        self.db.execute("INSERT OR REPLACE INTO tombstones VALUES(?,?,?)", (org, utcnow(), "BRREG HTTP 410 legal removal"))
        self.db.commit()
