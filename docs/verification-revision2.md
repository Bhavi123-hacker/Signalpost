# Final revision verification — 16 October 2026, India time

Local self-tests and collected-source audits, not official qualification or a score estimate. Author Bhavy Garg,24BAI1088,VIT Chennai. Frozen executable source **4d209fe189fcc9b3e4b234c4098383729e260a34**; later commit contains packaging/reports only. Original e0d90f5/d400e03 source, ZIP and baseline reports are preserved (verification-baseline.md and private/revision2/fallback-d400e03). Current public repository contains the earlier baseline; revised source remains local because publication was not authorised for this mission.

## Measured before/after

Same scale input1000, same declared frozen BRREG CSV (SHA256cfd5738e1c0bf808dae004fffd9dfe9a549467b0d5038c872f6df91b828d3041), fresh independent state,2000-start/2700-second provisional limits. Every input has an ordered terminal result. Registry identities: 1000; financial companies: 995. Baseline substantive site coverage **12**, revised **13**. Old reported14 included URL-only matches and is not compared against the stricter new definition. Websites verified separately: 17. No company with only registry facts or a URL is called externally enriched.

| Company field family | Baseline companies | Revised companies |
| --- | ---: | ---: |
| official_website | 14 | 17 |
| website_description | 9 | 13 |
| website_email | 10 | 11 |
| website_phone | 8 | 7 |
| website_service | 0 | 2 |
| website_location | 0 | 0 |
| website_leadership | 0 | 0 |
| dated_activity | 0 | 0 |
| job_posting | 0 | 0 |
| leadership_role | 126 | 363 |
| registered_workplace | 88 | 0 |
| official_group_structure | 3 | 0 |

Selected scale: 2000 HTTP starts, 756.422seconds, 53997511decoded bytes, USD0 paid API cost. Baseline:2000 starts,766.750seconds. These are live collection measurements under concurrent local workloads, not an isolated speed benchmark. Strong site candidates precede a fair official-role opportunity; speculative unmatched domains follow. Baseline roles 126 → 363; this preserves another field family rather than spending the entire remainder on guessed domains. Full claim counts, states, error breakdown and discovery funnel are in artifacts/revision2/comparison.json and verification-revision2.json.

The original independently selected100 validation companies initially gave4 baseline substantive matches and6 before manual scope review. That review found a staff-profile attribution problem. It was quarantined by a generic guard and rechecked; this100 is now a **regression validation set**, not an untouched final set. Final measured comparison: 4 → 5. A further independent20-company input was selected over the full eligible universe after the guard freeze, excluding every prior ID and without website/industry/size conditioning. It was run once per implementation: 0 → 0. Sample sizes are small; no official recall or general precision rate is inferred. The original100 smoke: 1 → 2, 573requests on Linux with cold live identity.

## Accuracy and reproducibility

**97 tests passed on Windows and97 on Linux**, zero failures/errors/skips, against the exact frozen source and only pinned declared core dependencies. All2484 source files were compared to Git blobs; three Git archive EOL conversions on non-executable files were restored. Requirements were byte-identical from the clean-environment creation commit to final source; no old installed application or research-state cache was reused. Linux was recovered with process-local TEMP/TMP on D:, without deleting unrelated files or changing global WSL settings. Exact XML, source fingerprint, install details and every selected live report are in submission/verification-revision2.json.

Own typed validator and independently downloaded/reviewed starter validator accepted actual selected outputs; private official scoring compatibility remains unverified. Evidence-binding audits passed for scale, smoke, validation and refresh. Scale checked 51541source references and 15953financial observations with zero binding failures. The binding auditor's old PDF boilerplate describes that automated check only; the separate semantic sample below was also performed. Manual identity/fact review findings are recorded without raw copyrighted HTML in the supplement.

Financial semantic audit: **10 original filed PDFs,31 observations**, including NOK/SEK/USD, explicit zeros, negative signs and separate company/group tables. No amount discrepancy observed in that sample; no corpus-wide factual error rate claimed. Revenue now explicitly means total operating income, not sales-only revenue. NUF is labelled foreign-enterprise filing, not Norwegian branch-only performance. Unknown explicit units/non-finite numbers are withheld; no LLM, scaling guess, currency conversion or numeric repair. See financial-audit.md and revision2-financial-review.json.

Second six-company refresh: 27requests, 11conditional hits, **zero false changes and zero stale claims**. Fixture tests separately force changed/removed/failed histories. Viewer uses actual stored profiles with escaped text, identity/status, source-linked descriptions, financial periods/units, history and JSON export; no framework rewrite or remote HTML rendering.

Revision evaluator ledger: 22runs, 15207HTTP starts, 6790.754summed seconds, USD0 paid API cost. This includes rejected iterations and validation reruns; excludes preparation, installation and separately logged PDF diagnostics. Do not add overlapping reruns to the distinct-company count. Every default adapter uses the shared durable counter, including redirects/retries/robots; same-run shared-response reuse is measured and new runs recheck sources.

## Run and handoff

One evaluator command, from activated isolated environment:

```sh
python scripts/run_competition_batch.py --organisations INPUT.jsonl --output OUTPUT.jsonl --report REPORT.json --state STATE --run-id official-001 --max-requests 2000 --max-seconds 2700
```

Append --bulk BRREG.csv.gz for the supplied frozen registry and use organiser's actual limits/cutoff. Smoke, original1000 and independent validation inputs/reports plus permitted exports are bundled; raw company pages, roles birth dates, PDF notes, keys, environments and personal sessions are excluded. Exact source/package hashes and metadata overlays are explicit in the manifest. Revised ZIP is Signalpost-submission-revision2.zip; original ZIP is untouched. Fill author contact, review publication commands and send the local draft manually. No revised push, email, paid call, cloud provisioning, official score or qualification occurred.
