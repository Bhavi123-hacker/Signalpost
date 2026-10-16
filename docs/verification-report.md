# Final coverage-cycle verification —16 October2026

Author Bhavy Garg,24BAI1088,VIT Chennai. Tested source `0f0ca16f762d1df8865743b2beacd7f118f3e591`. This is local verification, not private-harness qualification or an official score. All prior tested commits and four ZIP hashes remain intact.

The selected configuration retains balanced allocation/3pages after three scheduling alternatives tied development company breadth and reduced role coverage. It adds literal exact-org/name-core/registered-street/postcode proof for narrow AS/ASA/STI presentation variants, removes guessed domains, and prevents conflicting proof from being superseded. Financial parser/dependencies are unchanged.

## Actual comparisons

| Configuration | Inputs | Substantive | Verified | Roles | Requests | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| control | 200 | 4 | 4 | 132 | 400 | 221.469 |
| allocation | 200 | 4 | 4 | 95 | 400 | 226.921 |
| corroborated | 200 | 4 | 4 | 95 | 400 | 200.984 |
| fair | 200 | 4 | 4 | 96 | 400 | 272.125 |
| pre-fix-selected | 200 | 4 | 4 | 133 | 400 | 235.031 |
| pre-fix-validation-control | 200 | 5 | 5 | 73 | 400 | 264.250 |
| pre-fix-validation-selected | 200 | 5 | 5 | 73 | 400 | 254.688 |
| pre-fix-clean-windows | 6 | 0 | 0 | 6 | 33 | 41.735 |
| pre-fix-clean-linux | 3 | 0 | 0 | 3 | 20 | 28.763 |
| selected | 200 | 4 | 4 | 133 | 400 | 207.421 |
| validation-control | 100 | 3 | 3 | 43 | 200 | 118.594 |
| validation-selected | 100 | 4 | 4 | 44 | 200 | 125.609 |
| scale | 1000 | 20 | 21 | 402 | 2000 | 631.203 |
| smoke | 100 | 2 | 2 | 100 | 464 | 255.594 |
| clean-windows | 6 | 0 | 0 | 6 | 33 | 41.906 |
| clean-linux | 3 | 0 | 0 | 3 | 20 | 39.795 |

Development uses200 supplied IDs/400 reservations/900seconds. Final newly sealed validation uses100 supplied IDs/200 reservations/900seconds. All comparisons use the same declared public snapshot and empty external state; earlier200 validation is explicitly labelled pre-fix. New validation was selected before edits from the full universe excluding earlier explicit input IDs (independent overlap check:zero), then run once per policy after source freeze. No subsequent tuning. Sealed control and selected fingerprints match. Development controls were earlier source-fingerprint variants; mandatory no-guesses/conflict safety/missingness clarifications are disclosed in coverage-cycle.md.

The previous snapshot1000 measured17 substantive companies/18 sites/366 role companies at2000 starts/620.703s. Final uses identical input bytes and public development snapshot hash; sequential source conditions vary, so this is not a causal precision or official recall estimate. Neither test snapshot is Builderr's final official snapshot.

| External family | Previous1000 companies / facts | Final1000 companies / facts |
| --- | ---: | ---: |
| website_description | 17 / 18 | 20 / 21 |
| website_email | 11 / 16 | 15 / 26 |
| website_phone | 13 / 15 | 14 / 21 |
| website_service | 0 / 0 | 0 / 0 |
| website_location | 1 / 1 | 0 / 0 |
| website_leadership | 0 / 0 | 0 / 0 |
| job_posting | 0 / 0 | 0 / 0 |
| dated_activity | 0 / 0 | 0 / 0 |
| public_brand | 1 / 1 | 1 / 1 |

## Reproduce and verify

```sh
python scripts/run_competition_batch.py --organisations INPUT.jsonl --bulk BRREG.csv.gz --output OUTPUT.jsonl --report REPORT.json --state STATE --run-id official-001 --max-requests 2000 --max-seconds 2700 --strategy balanced --identity-policy corroborated --site-pages 3
```

Builderr's current technical contract supplies a frozen registry. Stage its actual file/checksum/acquisition metadata as docs/reproducibility.md describes. No private prepared snapshot or automatic uncounted download is assumed. Local snapshot reading is timed/zero HTTP; all live fallback, accounts, robots, redirects, retries and failed DNS reservations count.2000starts/2700seconds remain provisional until official limits arrive. Selected no-bulk1000 was not measured; the historical17-company no-bulk result is a different configuration, not equivalent evidence.

Exact raw measured inputs and their hashes are under artifacts/coverage-cycle/inputs and selection.json. Windows-selected dev/validation input bytes contain CRLF; canonical source examples contain LF with the same ordered IDs. Both hashes are declared; exact raw input bytes are preserved by Git attributes. Never substitute these test lists for official input.

Fresh Windows3.12.4 and WSL/Linux3.14.4 installations each pass126 tests, pip check and actual real-input evaluator commands.3590 frozen checkout files matched Git blobs; initial checkout-only EOL differences were restored to exact bytes. Linux lacked ensurepip; an existing pip installed only pinned requirements into its new isolated --without-pip venv. Two initial PyPI metadata timeouts retried successfully. All final outputs pass typed validation, independently supplied starter structural validation and source binding/dimension audits. These do not prove private-harness acceptance or semantic precision. Viewer checks use actual new1000 SQLite, escaped queries/evidence/financial dimensions/export/history and no public fetching.

## Accuracy, costs and remaining limits

Assistant source review and metadata-only findings are in artifacts/coverage-cycle/manual-audit.json. Four companies gained substantive evidence and one previously enriched company lost live access (Fjellfix), giving a net gain of three. Description/email/phone company coverage improves; location coverage falls from one to zero. The final heldout gain includes an explicitly supported audio product, while the scale batch still has zero product/job/dated-activity companies. No independent human/corpus-wide precision rate is claimed. Company self-descriptions can contain marketing or aspirational language and remain attributed; contact counts do not inflate company breadth. Unlicensed company HTML/claims and raw roles birth dates stay local; bundled real profiles are clearly labelled official-data subsets, with unmodified original-run coverage reports and source access metadata.

Financial interpretation remains independently checked on10 original filings/31 observations only, including currency/scale/sign/period/company/group cases. No discrepancy was observed in that sample; this does not establish a whole-corpus guarantee. Source-binding checks do not establish amount semantics; missing is never zero. Website stale-contact and B2B offering limitations remain in limitations.md. Jobs/activity/product breadth remains limited; no unsupported completion claim is made.

This cycle records8170 application starts plus12 discovery-feasibility and5 rule-check starts; summed application time3872.713s. Paid model/search/data API charges USD0 for every run. Dependency/documentation browsing is separately scoped, not fully metered; internet/electricity/hardware/assistant plan are not API charges. Wikidata returned0 random-development matches and is not enabled. No cloud/billing/publication/email occurred.

Public repository remains at d400e03 until the author publishes coverage-cycle:main. Source and packaging commits descend from that public tip; the pending history/package are scanned before handoff. Fill `[AUTHOR: CONFIRM CONTACT DETAILS BEFORE SENDING]`, publish/remotely verify the exact tested source, confirm organiser staging/limits/cutoff, then send the local email draft manually. No qualification claim.
