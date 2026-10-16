# Exact publication and submission handoff

Public repository: https://github.com/Bhavi123-hacker/Signalpost . Remote main was verified at d400e03e73f0ee90bf7b2eedab5ca94e1319bdaa. No push/email has occurred.

Preserved local main includes an older source-derived brand projection in its private pending history. Do NOT publish that branch. The isolated handoff-publication branch is a clean descendant of public main and preserves the tested application bytes. The final source hash is inserted into the manifest after the source freeze; packaging identity is recorded separately. Original commits/ZIPs remain local recovery points.

From D:/Signalpost, after review and a later explicit publication instruction, use this normal, non-force command:

```sh
git push origin handoff-publication:main
```

It has been prepared, not executed. A remote advance must be fetched and reviewed; never add --force. The final packaging report supplies exact remote verification commands. Verify remote main equals the publication branch tip and the tested source commit resolves through GitHub before sending the email. Public visibility alone is not enough.

Draft/contact placeholder: D:/Signalpost/submission/handoff/EMAIL_DRAFT.txt, [AUTHOR: CONFIRM CONTACT DETAILS BEFORE SENDING]. Fill actual author contact, review the ZIP/manifest and send manually to submit@builderr.ai. The primary run command includes the organiser-provisioned snapshot. See docs/reproducibility.md for checksum/acquisition/cutoff requirements and separately measured no-bulk results. Private harness and numerical caps remain unverified.
