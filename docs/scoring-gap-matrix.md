# Scoring gaps and revision priorities — 15 October 2026

Current challenge/contract/guide/source policy and starter re-fetched at the times/hashes in rules/retrieval-revision2.json. All five text/archive hashes match the earlier retrieved contract. Scoring remains 50 recall/coverage, 30 exact identity/evidence, 12 supported synthesis, 8 UX. Each external family uses 70% company recall and 30% claim recall against a private checked collection; family weights/denominators and numerical resource caps are not published. No local score or qualification is inferred. Variable official batches, one ordered terminal result per supplied organisation, six availability states, immutable dated evidence and reproducible refresh remain mandatory. Starter structural checks do not constitute official scoring.

Baseline below is frozen-exact-source-1000 (e0d90f5), same 2,000-request provisional limit used for comparisons. Registry identity comes from the declared evaluator-style frozen snapshot; external sources were cold/live. Source preparation and diagnostic investigation are separate from evaluator ledger operations.

| Information family | Actual baseline company coverage / 1,000 | Permitted candidate source | Identity/evidence risk | Expected starts | Priority |
| --- | ---: | --- | --- | ---: | --- |
| Legal identity/registered activity | 1,000 / 998 | Supplied BRREG snapshot; documented exact-org filtered API | Low if response IDs and row paths checked; never merge subunits | One filtered request per 25 identities, then exact fallback where absent | P0 reduce cold-start cost |
| Official company website | 14 verified; only 12 have substantive site facts | Registry URL, business-email domain, bounded legal-name hypothesis | High: managers/parents/shared sites; conflicting orgs must block | Typically 2–6 incl robots/redirects/proof | P0 queue quality and full proof allowance |
| Business descriptions | 9 | Verified site home/about, exact structured/DOM excerpts | Industry label is not company activity; promotional text attributed | 0–2 after proof | P0 broaden extraction |
| Products/services | 0 explicit | Actual site navigation/structured Product/Service | Avoid navigation labels as product claims | 0–2 after proof | P1 |
| Company-site email/phone | 10 / 8 | Verified contact/footer links and structured data | Avoid publisher/developer contacts or group attribution | 0–1 after proof | P0 |
| Registered roles | 126 | BRREG official role endpoint | Company roles, not inferred CEO; raw birth dates stay private | 1/company, no verified batch filter found | P1 after discovery |
| Registered workplaces | 88 | BRREG underenhet exact-parent filtered API | Branch vs legal entity; preserve parent IDs | 1/company (bounded page) | P1 after site proof |
| Financial metrics | 995; revenue 810 | BRREG normalized accounts and original filed PDF | Currency, scale, period, signs, consolidated scope need semantic audit | 1/company; no documented financial batch endpoint found | P0 audit, preserve honest tradeoff |
| Jobs / dated activity | 0 / 0 | Verified company careers/news pages, embedded structured records | Expired vs open; actual publication date, exact employer | 1–3 after proof | P1 actual navigation, bounded extraction |
| Public brand / linked company profiles | 0 / 0 | Explicit exact-company structured identity and outbound site links | Parent brands/platform restrictions; linked URL is not scraped profile evidence | 0 after proof | P2 only explicit proof |
| Synthesis / UX | Deterministic source-linked facts and viewer | Stored supported facts/history only | Unsupported summaries or misleading missingness | No network | P1 once coverage works |

## Measured bottleneck

1,000 identities → 984 generated candidates → 230 companies with any candidate/robots attempt → 113 companies with candidate HTML → 14 verified ownership → **12 with substantive external facts**. Missing candidate generation on an unattempted profile is not proof there is no website. Website primary outcomes: 833 request/allocation starvation, 49 ambiguous, 16 blocked, 16 no candidate/absent source, 72 other failures, 14 available; these are bounded-run outcomes, not independently established information absence.

2,000 outbound starts: 1,000 accounts, 445 robots, 271 other company-page requests, 126 roles, 103 workplace, 53 group, 2 registry fallbacks. Giving ~3 requests to an email-domain candidate often cannot finish robots + redirects + proof. Generic mailbox/manager domains consume scarce coverage budget. Roles/workplaces/group currently consume requests inside each company before all website candidates finish. Two verified URLs produced no substantive fact, so the revision reports URL verification separately from substantive external coverage.

Implementation order: exact-org filtered cold registry; run-local shared responses/robots redirect reuse; real-URL-first website-only pass with enough per-attempt capacity; fair lower-confidence discovery and accounts; richer bounded verified-page extraction; financial PDF/schema audit; blind comparison and final package. Do not weaken entity checks or count generic registry activity as external enrichment. Baseline source/reports/ZIP are retained under private/revision2/fallback-d400e03 and original Git commits remain intact.

Overnight recovery and selected measurements are in docs/verification-report.md and artifacts/overnight/comparison.json. This matrix preserves the initial measured gaps; it is not a statement of final coverage. The tested bounded cold-lookup chunk is25 IDs; larger documented filters were slow under the download deadline, so no100-ID throughput is assumed.

## Latest coverage-cycle decision

The initial matrix above is historical; guessed legal-name domains are now removed. Actual latest baseline and source/request risks are in docs/coverage-cycle.md. Priority is exact ownership-proof completion and source-derived breadth; optional role collection must not consume website proof capacity unnoticed. No financial/role batch endpoint is assumed. Source-independent Wikidata exact-ID discovery returned0/200 development matches at11 requests and was rejected for default use. The selected configuration is chosen from measured comparisons, not hypothetical family weights or an invented official score.

Final selected measurement:1000 identities,995 financial,21 verified sites/20 substantive,402 registered-role companies at2000 reservations/631.203s/USD0. Descriptions20,email15,phone14 companies; locations0 versus prior1; products/jobs/activity0 in scale. Independent100 strict3 versus selected4, including one supported product. These are category measurements, never an official score.
