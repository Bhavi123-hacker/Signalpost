# Models, APIs and actual costs

No model, embedding, paid search/data API, API key, personal browser session, cloud hosting or billing integration is enabled. No optional paid adapter was built or used. The author's coding-assistant login is never an application credential.

Enabled sources are the free documented BRREG entity/subunit, roles, accounts, workplace and group APIs plus anonymous company HTTP subject to source policy and robots. Original code is MIT; BRREG data is NLOD. Dependency licences are in THIRD_PARTY_NOTICES.md and docs/dependency-licences.json. Raw company pages and role birth-date responses are not redistributed.

Frozen source0607183400744697596a57322af38890b123678a; actual selected runs:

| Run | Inputs | HTTP starts | Seconds | Paid API USD |
| --- | ---: | ---: | ---: | ---: |
| scale | 1000 | 2000 | 620.703 | 0.00 |
| smoke | 100 | 572 | 324.039 | 0.00 |
| validation | 100 | 601 | 198.578 | 0.00 |
| refresh1 | 6 | 24 | 21.375 | 0.00 |
| refresh2 | 6 | 25 | 27.078 | 0.00 |

Scale uses a declared supplied registry snapshot and fresh external state. Smoke and sealed validation use fresh state/live identity. Website refresh2 has10 new observations and5 retained stale contacts; it is not claimed fully idempotent. The separate registry/financial-only control is documented in artifacts/overnight/refresh-analysis.json.

Recorded overnight evaluator ledger: 14 runs, 7842 starts, 2897.258 summed seconds, USD0. All recorded evaluator runs across recovery/development: 36 runs, 23243 starts, 9797.695 summed seconds, USD0. Overlapping companies are not summed as distinct profiles. Rejected diagnostic runs remain in the ledger.

Rule/Wikidata/NAV investigation counters are separate in run-ledger.json. Dependency downloads, web-tool documentation browsing and earlier preparation/diagnostic downloads are not comprehensively metered; they made no paid API calls. Internet, electricity, hardware, coding time and assistant-plan charges are separate and unestimated.

Expected official-run paid API charges remain USD0 at any input size because there is no charging adapter. This is not a guarantee of source availability or information completeness. The retrieved contract does not confirm numeric resource caps; use organiser-supplied limits. Default2700seconds/2000starts are provisional, with USD0 external paid spend.

Optional local financial-review tools were actually used: pypdf6.20.1 (BSD-3-Clause) and PyMuPDF1.26.7 (AGPL-3.0), declared separately in requirements-audit.txt. They are not imported by the evaluator/viewer. No LLM repaired or generated a financial value. Ten original filings/31 observations were visually reviewed; other accounts remain unaudited against original PDFs.

Handoff no-bulk1000 control: 2000 HTTP starts/683.031seconds,USD0. It is a separate measured configuration, not the17-company snapshot result. Five current-rule diagnostic HTTP calls were separately recorded; fresh dependency installation is outside evaluator counts and incurred no paid API calls.
