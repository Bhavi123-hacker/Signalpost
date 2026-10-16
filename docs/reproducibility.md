# Reproducible evaluator configuration

The re-fetched technical contract says Builderr provides the frozen official registry snapshot for identity anchoring. The reviewed starter accepts `--bulk`. Source rules permit BRREG bulk/entity data. Retrieval metadata and hashes are in `docs/rules/retrieval-handoff.json`; full downloaded documents remain local because redistribution rights were not established.

## Primary official configuration: supplied snapshot

Builderr stages its frozen registry as `BRREG.csv.gz` in the cloned repository, or supplies an absolute path for the same flag. It also supplies the snapshot acquisition time, evidence cutoff and a trusted file checksum. This provisioning is an explicit prerequisite; the application does not download a hidden registry or depend on the author's private cache.

Place acquisition metadata next to the file as `BRREG.csv.gz.metadata.json`. The supported keys are `url`, `final_url`, `retrieved_at` (actual acquisition time in UTC) and `sha256` (SHA-256 of the exact compressed file). Use the organiser's real values. If acquisition time is separately supplied, `--bulk-retrieved-at` can convey it. Do not invent an acquisition/effective/publication time or use the local import time as source freshness. Dataset generation time and evidence cutoff remain separate from acquisition time; the application cannot reconstruct an arbitrary historical cutoff.

Before running, compare the organiser's trusted checksum with `certutil -hashfile BRREG.csv.gz SHA256` on Windows CMD or `sha256sum BRREG.csv.gz` on Linux. Inspect the file/sidecar paths and supplied cutoff. A sidecar hash mismatch is detected by the importer; unreadable/malformed bulk data causes a visibly logged live-API fallback. Such a run is NOT a successful frozen-snapshot reproduction. Missing rows may also require counted exact-API fallbacks and must be reviewed against the organiser's cutoff policy.

From an activated isolated environment:

```sh
python scripts/run_competition_batch.py --organisations INPUT.jsonl --bulk BRREG.csv.gz --output OUTPUT.jsonl --report REPORT.json --state STATE --run-id official-001 --max-requests 2000 --max-seconds 2700
```

INPUT is always the organiser's file, never our smoke list. Batch size is variable. The numerical caps above remain provisional; the public contract specifies equal supplied budgets but does not confirm these numbers. No paid API is enabled.

The provided local file costs zero outbound HTTP starts to read; hashing/import time is inside the application wall budget. All live registry fallbacks, accounts, robots, redirects, retries and discovery use the shared counter. Organiser provisioning/accounting outside the process is governed by its official environment, not assumed free or unmetered by us. If a builder downloads a snapshot as part of an official run, that download must be included in the official resource accounting; our developer preparation utility is NOT an uncounted automatic pre-stage of the submitted command.

## What the existing snapshot experiment actually proves

The measured 1,000-company snapshot run used an explicitly supplied development snapshot obtained from `https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv`, acquired `2026-10-15T14:28:56.442993+00:00`, compressed SHA-256 `cfd5738e1c0bf808dae004fffd9dfe9a549467b0d5038c872f6df91b828d3041`, 155,030,478 bytes. It is a public BRREG development acquisition, not claimed to be Builderr's final official snapshot. Its acquisition time does not establish the effective date of every row. Private acquisition headers/cookies are not distributed.

That run produced 1,000 terminal envelopes/1,000 registry identities/995 financial companies/17 substantively externally enriched companies, 2,000 HTTP starts and 620.703 seconds. The exact executed argv and checksum are in `artifacts/overnight/scale-invocation.json` and report. It included two live identity fallback starts. The actual snapshot file is not bundled; official provisioning replaces the private local path. Re-downloading today's public CSV will generally produce a different hash and must not be called an exact replay of this old experiment.

## Snapshot-free control

Omitting `--bulk` performs live exact-ID filtered identity requests from an empty state. This is independently measured on the same 1,000 inputs in `artifacts/handoff/`; it is a separate configuration, not assumed equivalent to the snapshot experiment. It requires no registry acquisition or personal account. Live identity results may differ from an older frozen cutoff. The final handoff report records its actual requests, runtime, output states and coverage when complete.

## Remaining contract limits

Public starter/typed validation is structural, not private-harness acceptance. Exact private schema, numerical caps, snapshot staging path/acquisition metadata and official evidence-cutoff enforcement still come from Builderr's run configuration. Financial semantic review remains a sample of 10 original filings/31 observations, not a guarantee across all accounts. Website refresh and offering-recall limitations remain documented; this handoff adds no research feature.
