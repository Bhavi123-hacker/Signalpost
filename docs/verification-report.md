# Final overnight verification — 16 October 2026, India time

Author Bhavy Garg,24BAI1088,VIT Chennai. Local self-tests/source audits, not official qualification or a score. Frozen executable source **0607183400744697596a57322af38890b123678a**. Later packaging commit contains reports/metadata only. Original e0d90f5/d400e03 and recovery4d209fe/ZIPs are preserved. Revised source is LOCAL; public origin/main remains the earlier baseline.

## Comparable scale results

Same 1,000 supplied company IDs/order and same declared frozen BRREG CSV SHA256 cfd5738e1c0bf808dae004fffd9dfe9a549467b0d5038c872f6df91b828d3041. Separate empty state;2,000-start/2,700-second provisional caps. All1,000 inputs have terminal envelopes, with 1000 registry anchors and 995 financial companies. Substantive external companies:12 original→13 recovery→**17 final**. Old reported14 included URL-only matches; these comparisons use one substantive definition. Identity-only records are not fully externally researched profiles.

| Company field family | Original e0 | Recovery4d | Selected |
| --- | ---: | ---: | ---: |
| official_website | 14 | 17 | 18 |
| website_description | 9 | 13 | 17 |
| website_email | 10 | 11 | 11 |
| website_phone | 8 | 7 | 13 |
| website_service | 0 | 2 | 0 |
| website_location | 0 | 0 | 1 |
| website_leadership | 0 | 0 | 0 |
| dated_activity | 0 | 0 | 0 |
| job_posting | 0 | 0 | 0 |
| public_brand | 0 | 1 | 1 |
| leadership_role | 126 | 363 | 366 |
| registered_workplace | 88 | 0 | 0 |
| official_group_structure | 3 | 0 | 0 |

Final scale: 2,000 HTTP starts,620.703 seconds,55,175,211 decoded bytes,largest observed per-process Windows peak working set 270,487,552 bytes,USD 0 paid APIs. Baseline times are recorded measurements, not isolated speed benchmarks. The allocation tradeoff is explicit: registered-workplace and official-group coverage falls from the original baseline to zero in this scale run while site descriptions and registered roles increase; no official weighted-score improvement is inferred. Memory was sampled every second across the launcher and its own descendants, retaining the largest OS per-process peak; it is not summed process-tree memory and can miss a final sub-second peak. The supplied snapshot establishes identity freshness as of its declared acquisition, not a new live identity lookup.

## Experiments and held-out validation

Four cold-state dev200 comparisons used400 requests/900seconds each and identical executable bytes:control4 substantive/76 role companies; expanded5/76; focused5/76; thin5/83. Focused's extra service claim failed semantic review and is not an improvement: an advisory heading under a service URL is insufficient. The adaptive follow-up retained5 substantive companies and8 descriptions, with80 role companies/400starts/156.781s. Selected defaults expanded/adaptive skip already populated page categories while protecting missing descriptions. No assumed score weights or company-ID tuning. Full category/claim counts and rejected experiments are in experiments.md and comparison.json.

Sealed100 selected over the entire verified universe before experiments, excluding all prior IDs without website/size/sector conditioning, then run once per implementation after freeze: recovery5→selected5 substantive companies. Selection seed/checksum and actual host overlap are recorded in the supplement; host disjointness was not guaranteed during selection. No further tuning used this sample. Breadth remains5 versus5; phone companies increase1 to2, but two genuine industrial offerings are withheld by the conservative final offering rule. This is a disclosed false-negative, not a claimed precision benefit. Linux cold smoke100 (no bulk, new state):100 identities/100 financial/2 substantive external companies,572 starts/324.039s. Sealed selected cold100:601 starts/198.578s. Separate refresh results are in the selected reports. No official recall denominator, score or generalisation guarantee is inferred.

## Accuracy, environment and failure recovery

**111 tests passed on Windows and111 on Linux**, zero failures/errors/skips, using new isolated environments with only pinned declared application/test dependencies. All 4,918 archived files match Git blobs; three archive EOL changes on non-executable root files were restored. Linux lacked ensurepip: a --without-pip target was populated using pip's --python installer option. Initial WSL/DrvFS FD-capture failure ran no tests; --capture=sys resolved the test-runner issue without changing application code. No global OS/WSL changes or unrelated deletion. Exact environment imports, XML hashes, commands and recovery record are in verification-overnight.json.

Actual scale/smoke/validation/refresh output passed own typed and separately reviewed supplied starter validators. The private official harness and numerical caps remain unverified. Scale evidence audit checked 51,551 references / 15,953 financial observations, zero binding failures. Binding checks do not establish semantic truth. Manual exact-entity/span review is an assistant inspection, not independent human adjudication or a corpus precision rate. Two retained literal descriptions have limited relevance (a recruitment introduction and a narrow postage-service excerpt); they are disclosed in manual-review.json rather than treated as comprehensive summaries.

Review found quoted installer/group contacts and an unsupported headline-to-offering inference. Generic guards and explicit evidence-backed retractions now prevent current publication while preserving history; ordinary source failure still preserves stale prior evidence. A brand alias leaking through an export projection was also removed. Description review also found privacy/contact/navigation blurbs classified as business descriptions; the final source restricts that field to home/about context and product excerpts to product scope. No failure is hidden or counted as a verified improvement. Unknown dates and incomplete searches remain explicit; URL-only is not substantive coverage.

Financial semantic sample: 10 original filed PDFs / 31 observations,NOK/SEK/USD,negative amounts,explicit zeros,standalone/group tables; no amount discrepancy in that sample. Total operating income is distinguished from sales revenue; NUF foreign-enterprise context is explicit. Remaining accounts/periods are not independently PDF-audited. Unknown explicit scales and non-finite amounts are withheld; no model/guess/repair/conversion. See financial-audit.md.

Second six-company refresh:25 starts, 10 conditional hits,10 newly observed contacts from a newly visited page and 5 old contacts retained as stale. No timestamp-only value change was observed; all existing available values retain first_seen. The bounded/prior-aware website extractor does not reverify every known contact, so complete website freshness/idempotency is NOT claimed. A separate fresh-state6-company registry/financial-only control has zero changes/zero stale claims on its second run; its exact operations and binding audit are in refresh-analysis.json. Fixtures separately exercise real changes, removals, failures, retractions and restart budgets.

## Resources and handoff

The requested 07:00 IST delivery checkpoint was exceeded. All completion times below and in reports are actual later timestamps; no on-time delivery is claimed. Source remained frozen during final checks.

Overnight evaluator ledger: 14 runs / 7,842 starts / 2,897.258 summed seconds,USD 0 paid APIs. Aggregate and exclusions are in run-ledger.json; overlapping company runs are never summed as distinct profiles. Separate documented-source diagnostics are counted separately. No personal-session/API key, paid model/search service,cloud resource,email or push was used.

From an activated isolated environment, one evaluator command:

```sh
python scripts/run_competition_batch.py --organisations INPUT.jsonl --output OUTPUT.jsonl --report REPORT.json --state STATE --run-id official-001 --max-requests 2000 --max-seconds 2700
```

Append --bulk BRREG.csv.gz for the organiser's supplied frozen registry and use its actual caps/cutoff. Necessary source, permitted official-data exports/reports, exact hashes and local draft are in Signalpost-submission-overnight.zip. Raw company HTML/roles birth dates/PDF notes/credentials/environments remain local. Contact details require author completion; later publication and submission are manual author actions. No official qualification or private-pool score is claimed.
