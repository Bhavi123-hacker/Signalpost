from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .batch import atomic_json, coverage_report, read_inputs, run_batch
from .models import utcnow, validate_envelopes


def parser():
    p = argparse.ArgumentParser(description="Signalpost evidence-backed company research ($0 APIs)")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("batch", "refresh", "one"):
        b = sub.add_parser(name)
        if name == "one":
            b.add_argument("organisation_number")
        else:
            b.add_argument("--organisations", "--input", required=True)
        b.add_argument("--output", required=True)
        b.add_argument("--profiles-output")
        b.add_argument("--report", required=True)
        b.add_argument("--state", required=True, help="Local state directory containing SQLite and private evidence")
        b.add_argument("--bulk", help="Evaluator-provided frozen BRREG CSV(.gz) or native JSONL snapshot; optional")
        b.add_argument("--bulk-retrieved-at")
        b.add_argument("--run-id", required=True)
        b.add_argument("--expected-count", type=int)
        b.add_argument("--max-requests", type=int, default=2000)
        b.add_argument("--max-seconds", type=float, default=2700)
        b.add_argument("--max-cost-usd", type=float, default=0, help="Declared cap; implementation never calls paid services")
        b.add_argument("--workers", type=int, default=8)
        b.add_argument("--per-company-requests", type=int, default=16)
        b.add_argument("--site-pages", type=int, default=3)
        b.add_argument("--strategy", choices=["balanced", "official-first"], default="balanced")
        b.add_argument("--modules", default="registry,financials,roles,locations,group,website")
        b.add_argument("--resume", action="store_true", help="Same-run restart only; refresh uses a NEW run ID")
    v = sub.add_parser("validate")
    v.add_argument("--input", required=True, help="Output JSONL to validate")
    v.add_argument("--organisations")
    v.add_argument("--reference-root", help="Optional locally supplied official starter root; not bundled")
    r = sub.add_parser("report")
    r.add_argument("--input", required=True)
    r.add_argument("--output", required=True)
    v = sub.add_parser("viewer")
    v.add_argument("--state", required=True)
    v.add_argument("--port", type=int, default=8765)
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        if args.command in {"batch", "refresh", "one"}:
            if args.max_requests < 0 or args.max_seconds <= 0 or not 1 <= args.workers <= 32 or args.per_company_requests < 0 or args.max_cost_usd < 0 or not 1 <= args.site_pages <= 10:
                raise ValueError("Invalid resource limits")
            if args.command == "one":
                folder = Path(args.state)
                folder.mkdir(parents=True, exist_ok=True)
                args.organisations = folder / "one-input.jsonl"
                args.organisations.write_text(json.dumps({"organisation_number": args.organisation_number}) + "\n", encoding="utf-8")
                args.expected_count = 1
            return asyncio.run(run_batch(args))
        if args.command in {"validate", "report"}:
            rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
            if args.command == "report":
                atomic_json(args.output, coverage_report(rows))
                return 0
            inputs = read_inputs(args.organisations) if args.organisations else None
            result = validate_envelopes(rows, inputs)
            if args.reference_root:
                sys.path.insert(0, str(Path(args.reference_root).resolve() / "src"))
                from norway_company_agent.batch import validate_envelopes as official_validate
                result["official_starter_validation"] = official_validate(rows, len(inputs) if inputs is not None else len(rows))
                result["passed"] &= result["official_starter_validation"]["passed"]
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
        if args.command == "viewer":
            from .viewer import serve
            serve(args.state, args.port)
            return 0
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print("Input/configuration error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
