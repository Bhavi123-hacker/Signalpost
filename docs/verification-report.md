# Final handoff verification — 16 October 2026

Author: Bhavy Garg,24BAI1088,VIT Chennai. This is local verification, not qualification or a private scoring result. No research feature changed during handoff.

## Configuration and provisioning

The current technical contract explicitly says Builderr provides the frozen official registry snapshot. The primary command therefore includes `--bulk BRREG.csv.gz`; the organiser stages its file and trusted checksum/acquisition metadata. [Provisioning, timestamps and accounting](reproducibility.md) distinguishes source acquisition, dataset generation, import time and the official cutoff. No private cache or uncounted automatic download is required. Local snapshot reading uses zero HTTP starts but its processing time is inside the wall budget. Missing/malformed bulk can fall back to counted live lookups; that must not be called an exact frozen-snapshot replay.

```sh
python scripts/run_competition_batch.py --organisations INPUT.jsonl --bulk BRREG.csv.gz --output OUTPUT.jsonl --report REPORT.json --state STATE --run-id official-001 --max-requests 2000 --max-seconds 2700
```

INPUT always comes from the evaluator; there is no100-company maximum. Numerical caps2000/2700 remain provisional until Builderr supplies actual limits. The private harness and exact cutoff enforcement remain unverified.

## Measured configurations, not assumed equivalent

| Same1,000 supplied IDs, fresh state | Development snapshot | No bulk: live identity |
| --- | ---: | ---: |
| Terminal envelopes | 1000 | 1000 |
| Registry identities | 1000 | 1000 |
| Financial companies | 995 | 995 |
| Substantive external companies | 17 | 17 |
| Registered-role companies | 366 | 333 |
| HTTP starts | 2000 | 2000 |
| Runtime seconds | 620.703 | 683.031 |
| Paid API USD | 0 | 0 |

The snapshot experiment used public BRREG CSV acquired2026-10-15T14:28:56.442993+00:00, SHA256cfd5738e1c0bf808dae004fffd9dfe9a549467b0d5038c872f6df91b828d3041. It is NOT Builderr's final official snapshot. It included2 live identity fallback starts. Do not replace it with today's public CSV and claim an exact replay. Both timed runs actually executed source0607183400744697596a57322af38890b123678a; publication cleanup changes lineage/docs/generated artifacts, with byte-for-byte runtime/test/schema/runner/dependency equivalence recorded separately. No configuration-equivalence or speed-generalisation claim is made.

Snapshot claim counts and earlier cold100/heldout100/refresh results remain separately labelled under artifacts/overnight. The new live1000 typed and supplied starter validators pass; binding audit checks51062 references/15953 financial observations with zero binding failures. Binding does not establish financial meaning or private-harness acceptance.

Fresh Windows3.12.4 and Linux/WSL3.14.4 environments each pass111 tests and pip check, using only pinned declared dependencies on the clean publication worktree. Detailed environment imports/XML and actual argv are under artifacts/handoff. No personal session, paid API, model, cloud deployment or email was used.

Financial semantic review remains10 original filings/31 observations,NOK/SEK/USD,negative/zero and company/group cases; no amount discrepancy in that sample. Total operating income is distinguished from sales-only revenue and NUF scope from Norwegian branch-only results. Other accounts/periods are not independently PDF-audited. Missing is not zero; no model repairs amounts.

## Publication safety and remaining actions

Original public main is d400e03. The earlier tested and packaging commits are descendants, but an audit of every newly reachable blob found one older company-source brand projection in a generated export. No secrets/raw company HTML/PDF/birthdate records were found. A clean branch handoff-publication starts at public main and omits that private pending history, preserving all old commits/packages locally. Audit the new branch, not merely the ZIP; deleting the latest copy alone would not remove a historical blob from a push.

The final manifest supplies the frozen publication source commit and later packaging identity without a self-hash cycle. Publish only with the documented normal refspec, verify remote main and source accessibility, then fill the explicit contact placeholder and submit manually. Do not push the preserved old local main. See submission/PUBLICATION.md. No push or email has occurred.
