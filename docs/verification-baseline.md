# Verification report — 15 October 2026

This is an implementation/self-test report, not official qualification, independent truth verification or a score estimate. Author: Bhavy Garg, 24BAI1088, VIT Chennai. Project D:\Signalpost. No unrelated project was modified. The public repository is https://github.com/Bhavi123-hacker/Signalpost . The author explicitly authorised public visibility after the source was initially pushed privately. Exact frozen commit, clean-checkout results, final aggregate costs and ZIP hash are recorded after source freeze in `submission/manifest.json` and `submission/verification-final.json` inside the local package.

## Environment and automated checks

Windows: Python 3.12.4, isolated `.venv`. Linux: WSL2 Ubuntu, Linux 6.18.33.2, Python 3.14.4, isolated `.venv-linux`. Initial WSL lacked pip/ensurepip; a normal pip wheel bootstrapped the project-local environment without changing system Python or requiring Docker. Every application/test dependency is pinned in requirements.lock.txt. `pip check` reports no broken requirements. Both platforms passed **80 tests**; JUnit XML is in artifacts/verification/. Byte compilation passed.

Commands used (Windows CMD form; Linux uses its isolated Python):

```bat
.venv\Scripts\python -m pytest -q --junitxml=out/tests/windows.xml
.venv\Scripts\python -m compileall -q signalpost scripts
.venv\Scripts\python -m pip check
```

Focused synthetic fixtures cover checksum/normalisation, wrong same-name identity, parent/subunit separation, conflicting site numbers, evidence/value binding, exact financial decimals/currency/period/group scope, unknown scale quarantine, HTTP blocks/429, timeouts, redirect/private-DNS safety and pinning, robots and 304, retries, decoded-byte bounds, time/request/company caps, duplicate rejection, >100 inputs and input order, invalid-row isolation, malformed official responses, all-input deadline outcomes, unchanged/changed/removed/stale refresh, evidence history, durable resume caps/configuration, CLI exit codes, CSV quoting and zero-network frozen snapshots, viewer HTML escaping/Host/CSP/JSON routes. Fixtures are not live evidence.

## Sample selection and live commands

Published universe: 411,160 rows, compressed SHA-256 `1c89710e5b01f8617e86d09fbdff4a52f2f8dbbba297e74f7164b5984f5a0384`, uncompressed SHA-256 `b82d6a3e7231d1759a958c282bc4366b80ec2fab8095053d8ed7fa9cd01bc838`; both verified. Seed `20261015-signalpost-v1`; ascending SHA-256(seed + ':' + organisation_number). First 100 smoke, next 1,000 scale, next 20 untouched validation. No filtering for prominence, employees or websites. Metadata/distributions/checksums are in data/inputs/selection.json. Smoke has seven legal forms and only 12 registry-listed sites; scale has twelve forms and 113 listed sites. Many employee counts are legitimately not provided. Organisation splits are disjoint; website-host disjointness is not guaranteed (property managers/parent groups can be shared and are rejected as identities).

The optional full BRREG CSV was fetched at 2026-10-15T14:28:56Z, SHA-256 `cfd5738e1c0bf808dae004fffd9dfe9a549467b0d5038c872f6df91b828d3041` (155,030,478 compressed bytes). It is a declared local registry snapshot, not a new live identity request on each run. API/site enrichment was fetched live within each measured run. Preparation downloads and diagnostics are separate and not included in evaluator request totals.

Representative large-run command:

```sh
python scripts/run_competition_batch.py --organisations data/inputs/scale-1000.jsonl --bulk private/preparation/brreg-enheter.csv.gz --output out/final-scale/envelopes.jsonl --profiles-output out/final-scale/profiles.jsonl --report out/final-scale/report.json --state private/final-scale-state --run-id scale-1000-final --expected-count 1000 --max-requests 2000 --max-seconds 2700
```

| Live run | Registry anchored | Financial companies | External companies | HTTP starts | Seconds | API USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial 100 smoke | 100 | 100 | 0 | 642 | 211.454 | 0 |
| Initial 1,000 scale | 1,000 | 756 | 7 | 2,000 | 658.050 | 0 |
| Revised 100 smoke | 100 | 100 | 1 | 650 | 223.515 | 0 |
| Revised 1,000 scale | 1,000 | 995 | 14 | 2,000 | 691.515 | 0 |
| Refresh 1, six companies | 6 | 6 | 4 | 32 | 31.359 | 0 |
| Refresh 2, same six | 6 | 6 | 4 | 32 | 29.172 | 0 |

The two main samples contain **1,100 distinct real companies**. A separate live vertical slice researched Equinor 923609016. Overlapping reruns are not counted as new companies. Do not describe these as 1,000 complete external profiles: the revised large run has 14 companies with verified site evidence, nine with page descriptions, ten with site email, eight with site phone; zero publishable jobs or dated activity. All 1,000 have legal identity, 998 have actual self-reported registered activity, 134 have disclosed employee counts, 126 have registered roles, 88 have registered workplaces and three have official group structure. There are 15,953 available financial metric/period/scope observations across 995 companies, and revenue is provided for 810 companies. Availability of a family means at least one returned record, not necessarily that every metric/latest year is present.

All 1,000 envelopes are terminal in input order. The revised large run downloaded 43,644,830 decoded bytes, had ten conditional cache revalidations, request p50 343 ms and p95 4,937 ms. It used the exact 2,000-start cap; unattempted later modules are failed/incomplete rather than claimed absent. All five financial failures returned HTTP 500: 920284833, 982512069, 984187114, 997642589, 925057517. They are preserved as source failures, never zero values. Two eligible-universe companies now have deleted registry records; their current official deletion dates are retained. The revised allocation increases financial and site breadth at the cost of fewer roles than the initial run; no official score is inferred from this tradeoff.

Both own typed validator and the reviewed local starter `validate_envelopes` accepted the actual 100 and 1,000 outputs. The starter code is not redistributed and its minimal validation is not the private official scoring harness.

```sh
python -m signalpost validate --input out/final-scale/envelopes.jsonl --organisations data/inputs/scale-1000.jsonl --reference-root reference/signalpost-starter-kit
python scripts/audit_evidence.py --input out/final-scale/envelopes.jsonl --state private/final-scale-state --output out/audit/scale-final.json
```

## Evidence and source review

Revised scale binding audit: **48,796 evidence references and 15,953 financial observations**, zero binding failures. Revised smoke: 6,798 references and 1,690 financial observations, zero failures. Refresh 2: 318 references and 94 financial observations, zero failures. These compare immutable bytes/hashes, JSON paths or source spans, value bindings and exact financial company/currency/period/scope. They do not independently validate underlying accounting accuracy or official recall.

Assistant source-span review inspected all 14 revised-scale website identity proofs plus the smoke site's proof (Bodø Næringsforum). It confirmed collected legal-name and organisation-number text. Examples include Solund Verft, Fjordweb Solutions, Helping Hands and the NEMS contact page. See manual-identity-audit.json. This is not an independent human adjudication. In the smoke sample, Sameiet Bragernes Strand 3-4 (890049052) points to NBBO's site, which displays a different organisation number (952527827); it remains ambiguous. Property-manager, parent-brand and shared email-domain candidates are not attached merely by similar names.

Financial spot review compared collected API records for Eines AS (company revenue 2023 NOK 86,277,817.00), Koan Appartement AS (company revenue 2023 NOK 2,116,664.00), and Equinor's separate company/group 2025 records with their exact metric pointers and period/scope metadata. No currency conversion or thousand-unit multiplication was applied. **Independent PDF/table scale corroboration was not performed**; the current API OpenAPI does not explicitly annotate scale. Values are presented as raw normalised API currency amounts with scale=1, and this limitation is disclosed rather than claimed resolved.

## Refresh and viewer

The six-company refresh sample includes three randomly selected smoke companies and three verified sites from the development scale set; it is not a holdout for tuning. The second run made new live requests, recorded ten conditional hits, and generated **zero claim changes and zero stale claims**. Raw HTML content may vary; observation values, not retrieval timestamps, determine changes. Synthetic tests separately force added/changed/removed/blocked cases.

The loopback viewer returned HTTP 200 for name search, profile and JSON export against real stored records. Tests verify escaping, CSP, Host validation and absence of a raw-evidence file route. CSS provides a narrow-screen layout. No independent browser/mobile visual audit is claimed. The viewer is not needed by the evaluator. `scripts/load_export.py` also successfully loaded the 1,000 genuine public-export profiles with zero network requests.

## Reproducibility and handoff

Exact-commit clean installation and held-out checks occur after source freeze so the source hash cannot refer to its own generated package. Their commands, outputs, source commit and final counts are in the generated verification-final.json supplied in the ZIP. The submission manifest hashes the payload; its external copy additionally hashes the ZIP without a self-reference cycle. Full raw HTML, roles responses containing birth dates, credentials, environments, reference code and unrelated projects are excluded. Official-data exports are explicitly labelled filtered subsets, while report counts describe original local runs.

Remaining handoff: confirm contact detail, apply the organiser's supplied limits/cutoff, and manually send the prepared email. The repository is public following explicit authorisation; no email, paid API call or competition submission was performed. Coverage gaps and private-schema/numeric-budget uncertainties are documented in contract.md and limitations.md.

## Final exact-source verification

Frozen research source: **e0d90f5e985477bce05b4212c51d5bfdd8340105**. All 2,472 source-archive files were compared against Git blob bytes; three top-level non-executable files converted by Windows Git archive were restored to exact bytes before verification. Executable fingerprint across every clean live run: `5d0883bae7e354450402bc159a0de0af3580fb767558b34768bd95e235c3743d`. Later commits change reports and packaging metadata only, not the tested research runtime, tests, schemas or dependencies. Manifest metadata overlays are explicit.

Fresh Windows Python 3.12.4 and WSL Linux Python 3.14.4 virtual environments installed only requirements.lock.txt. `pip check` passed in both. The frozen source passed **80 tests on Windows and 80 on Linux**, with zero failures/errors/skips. Exact XML and environment details are in submission/verification-final.json. Linux's relative interpreter invocation produced a prefix-normalisation warning; its absolute interpreter path is correct and warning-free. No global application dependency or original research-state cache was reused.

| Exact-source live run | Identity | Financial companies | Verified external | HTTP starts | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Windows smoke, no bulk | 100 | 100 | 1 | 752 | 230.516 |
| Untouched validation, one run | 20 | 20 | 1 | 150 | 81.531 |
| Linux live batch | 3 | 3 | 0 | 6 | See embedded report |
| Windows 1,000, declared frozen bulk | 1,000 | 995 | 14 | 2,000 | 766.750 |

The final 1,000 run started at 15:47:57 UTC and completed at 16:00:43 UTC on 15 October 2026. It emitted exactly 1,000 ordered terminal envelopes, downloaded 43,166,785 decoded bytes and recorded 11 conditional cache hits. Both own typed and reviewed starter structural validators accepted the actual output. Its evidence audit checked **48,795 source references and 15,953 financial observations**, with zero binding failures. The distinct financial-company count is 995; source errors are preserved rather than converted to missing values or zero. A terminal module can still be failed/incomplete under the request cap. The outer `resource_cutoff=false` does not imply every module was researched: request-allocation and global-cap failures are recorded in module errors.

Across all 13 recorded evaluator live runs: **1,121 distinct registry-anchored companies**, **16 distinct companies ever verified externally**, 8,281 HTTP starts, 2,997.449 summed run seconds, 132,464,456 decoded bytes and **USD 0.00 paid API charges**. Overlapping reruns do not increase the distinct-company count. Preparation/dependency downloads and diagnostic requests are outside these totals and are not claimed comprehensively metered. Durable request totals/original deadlines persist on resume, while byte/cache-hit/latency/failure statistics describe the current invocation; the final verification runs were uninterrupted.

Private exact outputs/state remain under private/clean-verify/. Public packaged exports are the earlier genuine 100/1,000 official-data subsets, with their original measured reports; they are not relabelled as the later exact-source rerun. The detailed exact-source reports and audits are in submission/verification-final.json. No model, paid integration, personal application API credential, cloud resource or email was used. Official private-harness compatibility, independent financial PDF scale corroboration and broad external/news/jobs coverage remain unverified or limited as described above.
