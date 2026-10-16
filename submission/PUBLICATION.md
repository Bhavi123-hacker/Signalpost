# Exact publication and submission handoff

Public repository: https://github.com/Bhavi123-hacker/Signalpost . Remote main was verified at d400e03e73f0ee90bf7b2eedab5ca94e1319bdaa. No push/email has occurred.

Preserved local main includes an older source-derived brand projection in its private pending history. Do NOT publish that branch. The isolated handoff-publication branch is a clean descendant of public main and preserves the tested application bytes. The final source hash is inserted into the manifest after the source freeze; packaging identity is recorded separately. Original commits/ZIPs remain local recovery points.

From D:/Signalpost, after review and a later explicit publication instruction, use this normal, non-force command:

```sh
git push origin handoff-publication:main
```

It has been prepared, not executed. A remote advance must be fetched and reviewed; never add --force. The final packaging report supplies exact remote verification commands. Verify remote main equals the publication branch tip and the tested source commit resolves through GitHub before sending the email. Public visibility alone is not enough.

Draft/contact placeholder: D:/Signalpost/submission/handoff/EMAIL_DRAFT.txt, [AUTHOR: CONFIRM CONTACT DETAILS BEFORE SENDING]. Fill actual author contact, review the ZIP/manifest and send manually to submit@builderr.ai. The primary run command includes the organiser-provisioned snapshot. See docs/reproducibility.md for checksum/acquisition/cutoff requirements and separately measured no-bulk results. Private harness and numerical caps remain unverified.

## Exact remote verification after publication

Frozen tested source: `3124c87b40e381411c9661d8434728028ac3ea5c`. It is not public until the prepared push succeeds. The packaging branch tip contains this source as an ancestor.

From D:/Signalpost, inspect the local and remote state:

```sh
git log --oneline origin/main..handoff-publication
git diff --stat origin/main handoff-publication
git ls-remote origin refs/heads/main
```

The exact normal, non-force push is:

```sh
git push origin handoff-publication:main
```

Do not push old local main. If remote main advanced, fetch/review it rather than force-pushing. After the authorised push:

```sh
git rev-parse handoff-publication
git ls-remote origin refs/heads/main
gh api repos/Bhavi123-hacker/Signalpost/commits/main --jq .sha
gh api repos/Bhavi123-hacker/Signalpost/commits/3124c87b40e381411c9661d8434728028ac3ea5c --jq .sha
```

The first three hashes must equal the final packaging branch tip; the last must return the exact source above. A404/mismatch blocks submission. These commands are prepared, not a claim of completed publication. Contact placeholder: [AUTHOR: CONFIRM CONTACT DETAILS BEFORE SENDING] in the local EMAIL_DRAFT.txt. Fill actual contact, verify source accessibility and submit manually to submit@builderr.ai. No email/push has occurred.
