# Signalpost

Evidence-backed Norwegian company research, by **Bhavy Garg · 24BAI1088 · VIT Chennai**. Python 3.12+, SQLite, async HTTP, no model, no API keys, no Docker, $0 paid API calls. Terminal JSONL results preserve the evaluator's inputs and order. A separate local viewer exposes facts, evidence and history.

This is a self-tested entry, not an official qualification. Read [verification report](docs/verification-report.md) for measured coverage, costs, audited examples and remaining gaps. Sparse legal entities are kept in the sample; a returned identity is not a complete externally researched profile.

## Install

Windows **CMD**, from the project directory:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock.txt
```

Linux:

Use Python 3.12+ with working `venv`/`ensurepip` support (`python3-venv` on Debian/Ubuntu). The verification report records the alternative pip bootstrap used on the available WSL interpreter, which lacked that distribution component. WSL temporary-file capture can use `python -m pytest --capture=sys`.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
```

Activate the environment to use the same `python` command on either platform (`.venv\Scripts\activate.bat` in CMD, `source .venv/bin/activate` in Bash). No global installation or account login is required. The package is also installable with `python -m pip install .` if desired; the pinned requirements are the reproducible installation used in verification.

## One evaluator command

Run from the repository root with the isolated environment activated:

```sh
python scripts/run_competition_batch.py --organisations INPUT.jsonl --bulk BRREG.csv.gz --output OUTPUT.jsonl --report REPORT.json --state STATE --run-id official-001 --max-requests 2000 --max-seconds 2700 --strategy balanced --identity-policy corroborated --site-pages 3
```

Replace the three filenames and STATE directory with evaluator-supplied locations. The primary command explicitly requires the frozen registry supplied by Builderr as `BRREG.csv.gz` (CSV or native BRREG JSONL is accepted). See docs/reproducibility.md for mandatory provisioning/checksum/acquisition metadata. Omit `--bulk` only for the separately measured live-identity configuration. This removes live identity requests and leaves more budget for enrichment. Acquisition metadata can be adjacent as `BRREG.csv.gz.metadata.json`, or supplied with `--bulk-retrieved-at UTC_TIMESTAMP`. An unannotated evaluator snapshot is explicitly marked as a local snapshot read, not a live retrieval. The input list is never chosen by the runner. Without a bulk snapshot it uses the live entity API, with subunit fallback only after a 404.

The same flags work through `python -m signalpost batch`. Add `--profiles-output PROFILES.jsonl` for a simplified profile export. `--expected-count N` is optional and checks the supplied batch size; there is no 100-row maximum. The retrieved documents do not prescribe numeric resource caps; 2,700 seconds / 2,000 HTTP starts are conservative provisional defaults from the supplied task, overridden by official flags. Paid API calls remain disabled even if a nonzero cost cap is supplied. See [contract notes](docs/contract.md).

The selected defaults are `--extraction expanded --page-policy adaptive`: literal operational paragraphs and explicitly labelled contacts on verified pages, followed by actual navigation for categories still missing. The selected command keeps exact organisation-number proof and adds narrowly corroborated AS/STI name presentation only with exact registered street/postcode; conflicting numbers remain blocked. Optional depth is bounded by `--site-pages 3`; mandatory same-host identity proof may require additional pages even with `--site-pages 1`. `--extraction baseline --page-policy baseline` reproduces the extraction/allocation control, including current mandatory attribution corrections. [Experiments](docs/experiments.md) separates cold development comparisons, retrospective replay and untouched validation.

Exit 0: output is structurally valid and every input has a terminal outcome (some may be blocked/failed). Exit 1: output validation failed. Exit 2: invalid input/configuration. JSON/JSONL syntax errors and duplicate normalised organisation numbers are rejected at batch level, matching the starter. Invalid individual numbers get failed envelopes while other rows continue. Progress goes to stderr, results to files, and no batch logs go to stdout.

Input JSONL example:

```json
{"organisation_number":"923609016","id":"example-1"}
```

The source JSONL schema is in `schemas/`. Lists of strings, JSON `organisation_numbers` arrays and line-separated numbers are also supported. A result includes legal identity, six-state availability, claims, evidence IDs, source snapshots, changes, errors and operations. The compatible starter `state/modules/profile` structure is included alongside the minimal `run/claims/evidence` structure. Full genuine examples are in `artifacts/` after verification; the schemas are normative for our additional fields.

## Development and viewer

```sh
python -m signalpost one 923609016 --output out/one.jsonl --report out/one-report.json --state private/state --run-id one-001
python -m signalpost validate --input out/one.jsonl
python -m signalpost report --input out/one.jsonl --output out/coverage.json
python -m signalpost viewer --state private/state --port 8765
python -m pytest -q
```

Open http://127.0.0.1:8765. The viewer reads actual local SQLite records; it does not seed fixtures or make public-source requests. It provides company name/number search, profiles, evidence links, timestamps, unknown/blocked/ambiguous statuses, changes and JSON download. External content is escaped. The viewer is not part of batch execution.

To inspect the bundled **real official-data export** without collecting new sources:

```sh
python scripts/load_export.py --input artifacts/coverage-cycle/scale-1000/envelopes.jsonl.gz --state private/export-viewer
python -m signalpost viewer --state private/export-viewer --port 8765
```

This export is labelled as a rights-filtered subset. Original company-site evidence remains local; its measured coverage is reported separately. It contains no synthetic/demo companies.

Refresh with a **new run ID** using `python -m signalpost refresh` and the evaluator flags above. Normal reruns make live/conditional source requests and preserve prior observations. Add `--resume` only to restart the **same run ID, exact input bytes and configuration** after interruption. Request reservations and the original wall deadline persist across resume; it cannot reset the budget. A completed checkpoint is reported as resumed, not freshly researched. Failed/blocked refreshes retain last-known values with `stale=true` and their original last-checked times. BRREG 410 legal removals are a documented retention exception.

To compare actual output with an independently downloaded and reviewed official starter:

```sh
python -m signalpost validate --input OUTPUT.jsonl --organisations INPUT.jsonl --reference-root PATH_TO_STARTER
```

This runs the supplied starter's `validate_envelopes`; it does not reproduce Builderr's private scoring harness. No downloaded benchmark answers are used for research.

## Reproduce live samples

```sh
python scripts/prepare_public.py universe
python scripts/prepare_public.py bulk
python scripts/select_samples.py --universe private/preparation/universe.jsonl.gz --output data/inputs
python scripts/run_competition_batch.py --organisations data/inputs/smoke-100.jsonl --bulk private/preparation/brreg-enheter.csv.gz --output out/smoke.jsonl --report out/smoke-report.json --state private/reproduction --run-id smoke-reproduction --expected-count 100 --max-requests 2000 --max-seconds 2700
```

Use `data/inputs/scale-1000.jsonl` and expected-count 1000 for the larger test. `data/inputs/selection.json` records seed, universe hashes and disjoint splits. The 20-company validation input is held back from tuning. Preparation downloads are explicit, separately logged and not silently performed by the evaluator. Never provide our local test list instead of an official input file.

All implementation and audit details: [architecture](docs/architecture.md), [sources](docs/source-policy.md), [identity/evidence](docs/identity-and-evidence.md), [refresh](docs/refresh.md), [limitations](docs/limitations.md), [costs](docs/model-api-costs.md). No publication or email is performed by running this project. Packaging instructions are in `submission/PUBLICATION.md`.

## Revision 2 verification

The original e0d90f5 baseline and d400e03 package are preserved. Revised results are reported separately in docs/verification-report.md and submission/verification-revision2.json. External enrichment now requires a substantive sourced site fact; a URL alone is counted separately as a verified website. Cold starts use documented exact-ID filtered registry calls with bounded fallback; no private precomputed answers are loaded. Read docs/financial-audit.md for the 10-filing semantic sample and unresolved corpus-wide limits.

Optional original-filing review tools are isolated from the evaluator: install requirements-audit.txt and run scripts/review_financial_filings.py with explicit --input, --output, --state and optional --render. It collects documents for review and never automatically certifies numbers.

## Overnight verified revision

The overnight timed source was `0607183400744697596a57322af38890b123678a`; the final publication source and explicit runtime-equivalence proof are recorded in the handoff manifest/report. Exact new Windows/Linux installations each passed 111 tests. Final measured results, comparisons, costs and limitations are in [verification report](docs/verification-report.md), with permitted data under `artifacts/overnight/`. Older source/package commits remain recovery checkpoints. This revision has not been pushed or emailed. The 07:00 IST delivery checkpoint was missed; the report records actual completion times.

## Previous handoff (preserved fallback)

The primary official command includes the supplied snapshot; its17-company external result is not attributed to a command without --bulk. Both configurations are independently measured in docs/verification-report.md and artifacts/handoff/configuration-comparison.json. Final source identity is recorded in the submission manifest after freezing. Application bytes match the prior timed source; publication lineage is cleaned without rewriting the preserved original branch. Use submission/PUBLICATION.md, and publish the tested source before sending the draft.

## Latest coverage cycle

The selected command above retains balanced allocation after three alternative schedulers failed to increase substantive development coverage. It enables only the audited corroborated legal-form policy, removes guessed domains and prevents a conflicting contact proof from being superseded. See docs/coverage-cycle.md for actual comparisons and limitations. Source freeze, exact-commit clean checks, current profiles and ZIP are recorded by the new coverage manifest; prior handoff/overnight results remain historical fallback measurements. No publication/email is performed.
