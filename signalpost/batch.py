from __future__ import annotations

import asyncio
import csv
import gzip
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .http import Budget, FetchError, Fetcher, REQUEST_SCOPE, Result
from .models import canonical, digest, org_number, utcnow, validate_envelopes
from .research import Profile, official, registry, website, website_candidates
from .store import Store


def read_inputs(path: str | Path) -> list[dict]:
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    if p.suffix.lower() == ".json":
        body = json.loads(text)
        values = body if isinstance(body, list) else body["organisation_numbers"]
    elif p.suffix.lower() == ".jsonl":
        values = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        values = [line.strip() for line in text.splitlines() if line.strip()]
    result = []
    for index, item in enumerate(values):
        raw = item.get("organisation_number") if isinstance(item, dict) else item
        error = None
        try:
            org = org_number(raw)
        except ValueError as exc:
            org, error = str(raw if raw is not None else ""), str(exc)
        result.append({"organisation_number": org, "input_id": item.get("id", item.get("input_id", index)) if isinstance(item, dict) else index, "input_error": error})
    orgs = [r["organisation_number"] for r in result]
    if len(orgs) != len(set(orgs)):
        raise ValueError("Duplicate organisation numbers are rejected, matching the official starter input convention")
    return result


def atomic_json(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_name(p.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(p)


def write_jsonl(path, rows):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_name(p.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(canonical(row) + "\n")
    temporary.replace(p)


def normalize_csv(row: dict) -> dict:
    # CSV is an official flattened JSON representation, not enrichment truth.
    entity = {}
    for key, raw in row.items():
        if raw in (None, ""):
            continue
        key = {"registreringsdatoenhetsregisteret": "registreringsdatoEnhetsregisteret"}.get(key, key)
        target = entity
        parts = key.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        value = raw
        if raw.lower() in {"true", "false"}:
            value = raw.lower() == "true"
        elif key == "antallAnsatte" and raw.isdigit():
            value = int(raw)
        target[parts[-1]] = value
    entity["_source_csv_row"] = row
    return entity


def load_bulk(path, wanted: set[str], store: Store, budget: Budget, retrieved_at=None) -> dict[str, Result]:
    p = Path(path)
    # Hash streaming rather than loading the full snapshot in RAM.
    import hashlib
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            budget.check_time()
            h.update(chunk)
    sha = h.hexdigest()
    side = p.with_suffix(p.suffix + ".metadata.json")
    meta = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
    if meta.get("sha256") and meta["sha256"] != sha:
        raise ValueError("Registry bulk hash differs from its acquisition metadata")
    retrieval = retrieved_at or meta.get("retrieved_at") or utcnow()
    kind = "source_download" if retrieved_at or meta.get("retrieved_at") else "evaluator_supplied_local_snapshot_read"
    with p.open("rb") as f:
        compressed = f.read(2) == b"\x1f\x8b"
    opener = gzip.open if compressed else open
    results = {}
    with opener(p, "rt", encoding="utf-8-sig", newline="") as f:
        if p.name.endswith(("jsonl", "jsonl.gz")):
            rows = (json.loads(line) for line in f if line.strip())
            is_csv = False
        else:
            sample = f.read(8192)
            f.seek(0)
            # Sniffer may infer doublequote=False from an early sample with no
            # embedded quotes. Official CSV uses doubled quotes throughout.
            header = sample.splitlines()[0]
            delimiter = max((",", ";", "\t"), key=header.count)
            rows = csv.DictReader(f, delimiter=delimiter, doublequote=True, quotechar='"')
            is_csv = True
        for index, row in enumerate(rows):
            if index % 5000 == 0:
                budget.check_time()
            org = str(row.get("organisasjonsnummer", ""))
            if org not in wanted:
                continue
            if None in row:
                # A malformed source row cannot contaminate other companies.
                # Leave it out so exact live-API fallback handles this input.
                continue
            if store.db.execute("SELECT 1 FROM tombstones WHERE org=?", (org,)).fetchone():
                continue
            entity = normalize_csv(row) if is_csv else row
            data = canonical(entity).encode("utf-8")
            snapshot = store.snapshot({"source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv", "final_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "source_class": "official_registry_bulk", "retrieved_at": retrieval, "imported_at": utcnow(), "retrieval_kind": kind,
                "http_status": 200, "content_type": "application/json", "redirect_chain": [], "revalidated": False,
                "parent_bulk_sha256": sha, "source_row_key": org, "extraction_method": "official CSV row to typed nested JSON; original flat row retained"}, data)
            results[org] = Result(snapshot, data)
            if len(results) == len(wanted):
                break
    return results


def coverage_report(rows: list[dict]) -> dict:
    fields = Counter()
    companies = Counter()
    external = baseline = financial = stale = 0
    for row in rows:
        populated = [c for c in row["claims"] if c["availability"] == "available" and not c["stale"]]
        fields.update(c["field"] for c in populated)
        companies.update({c["field"] for c in populated})
        baseline += row["legal_identity"]["status"] == "available"
        external += any(c["field"] in {"official_website", "website_description", "website_email", "website_phone", "job_posting", "dated_activity"} for c in populated)
        financial += any(c["field"].startswith("financial.") for c in populated)
        stale += sum(c["stale"] for c in row["claims"])
    return {"envelopes": len(rows), "distinct_inputs": len({r["organisation_number"] for r in rows}), "registry_anchored_companies": baseline,
            "externally_enriched_companies": external, "financial_companies": financial,
            "current_claims_by_field": dict(sorted(fields.items())), "companies_by_populated_field": dict(sorted(companies.items())),
            "terminal_availability_counts": dict(Counter(r["availability"] for r in rows)),
            "module_states": {m: dict(Counter(r["modules"][m]["availability"] for r in rows)) for m in rows[0]["modules"]} if rows else {}, "stale_claims": stale}


async def run_batch(args, *, transport=None):
    inputs = read_inputs(args.organisations)
    if args.expected_count is not None and len(inputs) != args.expected_count:
        raise ValueError(f"Expected {args.expected_count} inputs; received {len(inputs)}")
    input_hash = digest(Path(args.organisations).read_bytes())
    started_at = utcnow()
    source_files = sorted((Path(__file__).parent).glob("*.py"))
    source_tree_hash = digest(canonical({p.name: digest(p.read_bytes()) for p in source_files}).encode())
    budget = Budget(args.max_requests, args.max_seconds, margin=5 + .05 * len(inputs))
    store = Store(args.state)
    bulk_hash = None
    if args.bulk and Path(args.bulk).is_file():
        import hashlib
        bulk_hasher = hashlib.sha256()
        with Path(args.bulk).open('rb') as bulk_handle:
            while chunk := bulk_handle.read(1024 * 1024):
                budget.check_time()
                bulk_hasher.update(chunk)
        bulk_hash = bulk_hasher.hexdigest()
    config_hash = digest(canonical({"input_hash": input_hash, "modules": args.modules, "strategy": args.strategy,
        "bulk": str(Path(args.bulk).resolve()) if args.bulk else None, "max_requests": args.max_requests,
        "bulk_sha256": bulk_hash, "source_tree_sha256": source_tree_hash,
        "max_seconds": args.max_seconds, "per_company_requests": args.per_company_requests, "site_pages": args.site_pages}).encode())
    saved_run = store.db.execute("SELECT input_hash,config_hash,started_at FROM runs WHERE run_id=?", (args.run_id,)).fetchone()
    if saved_run:
        if not args.resume:
            store.close()
            raise ValueError("Run ID already exists; use --resume for interruption recovery or a new --run-id for refresh")
        if saved_run[0] != input_hash or saved_run[1] != config_hash:
            store.close()
            raise ValueError("Resume input/configuration differs from the checkpointed run")
        started_at = saved_run[2]
        elapsed = max(0, (datetime.now(UTC) - datetime.fromisoformat(started_at.replace("Z", "+00:00"))).total_seconds())
        budget.started -= elapsed
        budget.deadline -= elapsed
        for _, host, company in store.db.execute("SELECT request_number,host,company FROM request_journal WHERE run_id=?", (args.run_id,)):
            budget.requests += 1
            budget.by_host[host] += 1
            if company:
                budget.by_company[company] += 1
    else:
        store.db.execute("INSERT INTO runs VALUES(?,?,?,?)", (args.run_id, input_hash, config_hash, started_at))
        store.db.commit()
    previous_requests = budget.requests

    def reserve_request(number, host, company):
        store.db.execute("INSERT INTO request_journal VALUES(?,?,?,?,?)", (args.run_id, number, host, company, utcnow()))
        store.db.commit()

    budget.on_take = reserve_request
    fetcher = Fetcher(store, budget, transport=transport)
    profiles = {r["organisation_number"]: Profile(r["organisation_number"], args.run_id, started_at, r["input_id"]) for r in inputs}
    previous = {org: store.load(org) for org in profiles}
    rows_by_org = {}
    resumed = 0
    if args.resume:
        for org in profiles:
            saved = store.checkpoint(args.run_id, input_hash, org)
            if saved and saved.get("checkpoint_phase") == "finished":
                rows_by_org[org] = saved
                resumed += 1
    bulk = {}
    requested = [m.strip() for m in args.modules.split(",") if m.strip()]
    invalid_modules = set(requested) - {"registry", "registry_live", "accounting_obligation", "financials", "roles", "locations", "group", "website"}
    if invalid_modules:
        raise ValueError("Unknown modules: " + ",".join(sorted(invalid_modules)))
    sem = asyncio.Semaphore(args.workers)

    async def identity_task(record):
        org = record["organisation_number"]
        if org in rows_by_org:
            return
        p = profiles[org]
        async with sem:
            token = REQUEST_SCOPE.set({"org": org, "allowance": 4, "used": 0})
            try:
                if record["input_error"]:
                    raise FetchError("failed", "Invalid input: " + record["input_error"])
                await registry(p, fetcher, bulk.get(org))
                if p.entity.get("_legal_removal"):
                    previous[org] = None
            except FetchError as exc:
                p.failure("registry", exc)
            except Exception as exc:
                p.mark("registry", "failed", "Registry schema/extraction error: " + type(exc).__name__)
                p.errors.append({"module": "registry", "state": "failed", "message": type(exc).__name__})
            finally:
                REQUEST_SCOPE.reset(token)
            checkpoint = p.finalize(previous[org])
            checkpoint["checkpoint_phase"] = "identity"
            # Persist progress, but final diff is calculated from the previous run.
            store.db.execute("INSERT OR REPLACE INTO checkpoints VALUES(?,?,?,?)", (args.run_id, input_hash, org, canonical(checkpoint)))
            store.db.commit()

    async def enrich_task(p, allowance, sequence_override=None, finish=True):
        org = p.org
        if org in rows_by_org:
            return
        async with sem:
            token = REQUEST_SCOPE.set({"org": org, "allowance": allowance, "used": 0})
            try:
                if p.modules["registry"]["availability"] == "available":
                    # Balanced mode gives websites first chance only for a real official URL/email.
                    sequence = sequence_override if sequence_override is not None else [m for m in requested if m in {"financials", "website", "roles", "locations", "group"}]
                    if args.strategy == "balanced" and (p.entity.get("hjemmeside") or p.entity.get("epostadresse")) and "website" in sequence:
                        sequence.remove("website")
                        sequence.insert(0, "website")
                    for module in sequence:
                        try:
                            if module == "website":
                                await website(p, fetcher, max_pages=args.site_pages)
                            else:
                                await official(p, fetcher, module)
                        except FetchError as exc:
                            p.failure(module, exc)
                        except Exception as exc:
                            p.mark(module, "failed", "Source schema/extraction error: " + type(exc).__name__)
                            p.errors.append({"module": module, "state": "failed", "message": type(exc).__name__})
            finally:
                REQUEST_SCOPE.reset(token)
            if not finish:
                return
            row = p.finalize(previous[org])
            row["checkpoint_phase"] = "finished"
            row["operations"]["requests"] = budget.by_company[org]
            rows_by_org[org] = store.save(row, input_hash)
            if len(rows_by_org) % 25 == 0:
                print(f"Finished {len(rows_by_org)}/{len(inputs)}; {budget.requests} HTTP requests", file=sys.stderr, flush=True)

    timed_out = False
    try:
        async with asyncio.timeout(max(.01, budget.deadline - time.monotonic())):
            if args.bulk:
                if not Path(args.bulk).is_file():
                    raise ValueError("Supplied bulk snapshot does not exist")
                try:
                    bulk = load_bulk(args.bulk, {r["organisation_number"] for r in inputs if not r["input_error"]}, store, budget, args.bulk_retrieved_at)
                except (OSError, ValueError, UnicodeError, csv.Error, EOFError, AttributeError) as exc:
                    print(f"Bulk source unreadable ({type(exc).__name__}); using bounded exact-API fallback", file=sys.stderr)
                    for p in profiles.values():
                        p.errors.append({"module": "registry_bulk", "state": "failed", "message": "Bulk source parse/read error: " + type(exc).__name__})
            await asyncio.gather(*(identity_task(r) for r in inputs))
            pending = [p for org, p in profiles.items() if org not in rows_by_org and p.modules["registry"]["availability"] == "available"]
            if args.strategy == "balanced" and "financials" in requested:
                # Give EVERY anchored company its filed-accounts opportunity before
                # any website can consume scarce requests. This is an observable
                # phase, not an estimate of coverage from registry-only envelopes.
                share, extra = divmod(budget.remaining, max(1, len(pending)))
                await asyncio.gather(*(enrich_task(p, min(2, share + (i < extra), args.per_company_requests), ["financials"], finish=False) for i, p in enumerate(pending)))
                print(f"Accounts phase finished for {len(pending)} identities; {budget.requests} HTTP requests", file=sys.stderr, flush=True)
                sequence = [m for m in requested if m in {"website", "roles", "locations", "group"}]
                priority = [p for p in pending if "website" in requested and any(c["method"] in {"registry_listed", "registry_business_email_domain"} for c in website_candidates(p.entity))]
                remaining = [p for p in pending if p not in priority]
                # Source-aware allocation: registry URL/email candidates receive
                # enough starts to check robots + redirects + a page. All other
                # companies already got identity/accounts, and share unused starts
                # afterwards (including reproducible name-domain discovery).
                share, extra = divmod(budget.remaining, max(1, len(priority)))
                await asyncio.gather(*(enrich_task(p, min(args.per_company_requests, share + (i < extra)), sequence) for i, p in enumerate(priority)))
                share, extra = divmod(budget.remaining, max(1, len(remaining)))
                await asyncio.gather(*(enrich_task(p, min(args.per_company_requests, share + (i < extra)), sequence) for i, p in enumerate(remaining)))
                await asyncio.gather(*(enrich_task(p, 0, []) for org,p in profiles.items() if org not in rows_by_org))
            else:
                share, extra = divmod(budget.remaining, max(1, len(pending)))
                allocations = {p.org: min(args.per_company_requests, share + (i < extra)) for i, p in enumerate(pending)}
                await asyncio.gather(*(enrich_task(p, allocations.get(org, 0)) for org, p in profiles.items() if org not in rows_by_org))
    except (TimeoutError, FetchError) as exc:
        timed_out = True
        print(f"Resource cutoff: {type(exc).__name__}; serializing every remaining input", file=sys.stderr)
    finally:
        await fetcher.close()
    for org, p in profiles.items():
        if org not in rows_by_org:
            if p.modules["registry"]["availability"] == "failed":
                p.mark("registry", "failed", "Not completed before resource cutoff")
            p.errors.append({"module": "run", "state": "failed", "message": "Resource cutoff; remaining research not completed"})
            row = p.finalize(previous[org])
            row["operations"]["requests"] = budget.by_company[org]
            row["checkpoint_phase"] = "finished"
            rows_by_org[org] = store.save(row, input_hash)
    rows = [rows_by_org[r["organisation_number"]] for r in inputs]
    validation = validate_envelopes(rows, inputs)
    write_jsonl(args.output, rows)
    if args.profiles_output:
        write_jsonl(args.profiles_output, [r["profile"] for r in rows])
    operations = budget.report()
    operations["requests_this_invocation"] = budget.requests - previous_requests
    operations["request_accounting"] = "Durable reservations before DNS/HTTP; redirects, robots and retries count. Resume retains original wall-clock deadline and cumulative request cap."
    runtimes = sorted(r["operations"]["runtime_ms"] for r in rows)
    report = {"run_id": args.run_id, "started_at": started_at, "completed_at": utcnow(), "input_sha256": input_hash,
              "expected_count": len(inputs), "emitted_envelopes": len(rows), "resumed_profiles": resumed,
              "source_tree_sha256": source_tree_hash,
              "limits": {"requests": args.max_requests, "seconds": args.max_seconds, "cost_usd": 0, "workers": args.workers, "per_company_requests": args.per_company_requests},
              "resource_cutoff": timed_out, "operations": operations, "coverage": coverage_report(rows), "validation": validation,
              "profile_p50_ms": runtimes[len(runtimes) // 2] if runtimes else None,
              "profile_p95_ms": runtimes[min(len(runtimes) - 1, int(len(runtimes) * .95))] if runtimes else None,
              "cache_declaration": "SQLite response validators; no unvalidated response reuse. Optional evaluator bulk declared in source_snapshots.",
              "qualification": "Self-test only; no official score or qualification claimed"}
    atomic_json(args.report, report)
    write_jsonl(str(args.report) + ".requests.jsonl", fetcher.events)
    store.db.execute("INSERT OR REPLACE INTO run_reports VALUES(?,?)", (args.run_id, canonical(report)))
    store.db.commit()
    store.close()
    print(canonical({"report": str(args.report), "envelopes": len(rows), "requests": operations["requests"], "validation_passed": validation["passed"]}), file=sys.stderr)
    return 0 if validation["passed"] else 1
