# Models, APIs and actual costs

No LLM, embedding model, model weights, paid search, paid data feed, paid API key, cloud resource or hosting is used. No optional paid adapter is implemented or activated. Environment variables and the author's coding-assistant login are never used as application credentials. All runs are fully reproducible without a personal browser/service account.

Enabled APIs: free public BRREG Enhetsregisteret (entity/subunit, company roles, group structure, workplaces) and normalised Regnskapsregisteret financials. Company websites use ordinary anonymous HTTP subject to robots and the source policy. Original code is MIT; official data is NLOD; dependency and company-source rights are in THIRD_PARTY_NOTICES.md and docs/dependency-licences.json. No raw company page is redistributed.

Measured paid third-party API spend is **USD 0.00 per tested batch**. Representative development measurements (exact final records and later clean verification are in verification-report.md and submission/verification-final.json):

| Run | Inputs | HTTP starts | Runtime seconds | Paid API USD |
| --- | ---: | ---: | ---: | ---: |
| Initial smoke | 100 | 642 | 211.454 | 0.00 |
| Initial scale | 1,000 | 2,000 | 658.050 | 0.00 |
| Revised smoke | 100 | 650 | 223.515 | 0.00 |
| Revised scale | 1,000 | 2,000 | 691.515 | 0.00 |
| Live refresh first | 6 | 32 | 31.359 | 0.00 |
| Live refresh second | 6 | 32 | 29.172 | 0.00 |

The default official-run **paid API cost expectation is $0** at any supplied batch size, because there is no charging integration. This does not mean full information is free to access: restricted/missing sources are declined. Budgets constrain coverage, not price. The retrieved contract gives an equal supplied budget but no numeric cap; default $0 remains below the user's unverified $10 ceiling.

Internet service, electricity, hardware, development time, ChatGPT/Codex plan usage, GitHub account arrangements and possible future deployment costs are separate from third-party application API charges. They are neither estimated nor represented as free. No account upgrade, paid hosting or cloud provisioning occurred. Development preparation downloads and diagnostic HTTP tests are outside measured evaluator runs; they made no paid API calls. Their request counts are not claimed to be comprehensively metered. Evaluator adapters all share the durable bounded counter.
