# Publication and submission handoff

Real repository:https://github.com/Bhavi123-hacker/Signalpost (PUBLIC). Remote main rechecked16 October2026 at d400e03e73f0ee90bf7b2eedab5ca94e1319bdaa. No push/email from this cycle. Tested source0100dabf7580532f72a8e1e46e33dd04c591ee3b is local until publication succeeds. Current package/manifest/checks are D:/Signalpost/submission/coverage-cycle/.

Use the clean coverage-cycle publication branch, which descends from public main. The preserved older local main contains unrelated-to-this-release restricted projection history and must NOT be pushed. Original commits and four ZIPs remain recovery points. Source/runtime freeze and later packaging/report commit are separate; the external PACKAGING_COMMIT.txt records the latter without a self-referential hash cycle.

From Windows CMD:

```bat
cd /d D:\Signalpost
git fetch origin main
git log --oneline origin/main..coverage-cycle
git diff --stat origin/main coverage-cycle
git merge-base --is-ancestor origin/main coverage-cycle
git merge-base --is-ancestor 0100dabf7580532f72a8e1e46e33dd04c591ee3b coverage-cycle
git ls-remote origin refs/heads/main
```

Review remote advancement and the pending audit before publishing. Do not force or push old local main. After a later explicit publication instruction, the exact normal push is:

```sh
git push origin coverage-cycle:main
```

Then verify:

```sh
git rev-parse coverage-cycle
git ls-remote origin refs/heads/main
gh api repos/Bhavi123-hacker/Signalpost/commits/main --jq .sha
gh api repos/Bhavi123-hacker/Signalpost/commits/0100dabf7580532f72a8e1e46e33dd04c591ee3b --jq .sha
```

The first three hashes must equal the final packaging branch tip. The last must return the exact frozen source. A404/mismatch blocks submission. Public repository visibility alone does not establish that the tested source is available. These commands are prepared, not executed.

Fill [AUTHOR: CONFIRM CONTACT DETAILS BEFORE SENDING] in D:/Signalpost/submission/coverage-cycle/EMAIL_DRAFT.txt. Review package/hash/report, confirm organiser snapshot staging/acquisition/cutoff and actual numerical limits, publish/remotely verify source, then manually send to submit@builderr.ai. Primary command includes --bulk and selected ownership flags; no current no-bulk1000 equivalence is claimed. Financial semantic audit remains10 filings/31observations and private-harness acceptance remains unverified. No email or publication occurs automatically.
