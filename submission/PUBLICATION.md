# Publication and submission handoff

The authorised GitHub repository is private: https://github.com/Bhavi123-hacker/Signalpost . A private source push does not give Builderr access. No email has been sent and no competition entry has been submitted.

After reviewing the local package and choosing how the organiser will receive access, publish only the frozen source and permitted reports. The commands below are a handoff, not executed public publication:

```sh
git remote -v
git status --short
git push -u origin main
```

The final report states whether the private source push has already been performed. Do not add private/, out/, .env files, raw company pages, virtual environments, tokens or personal-session data. The repository ignores those paths; the packaging script uses an explicit tracked-source allowlist and permitted export directory.

If a public artifact is required, changing visibility needs a separate explicit authorisation:

```sh
gh repo edit Bhavi123-hacker/Signalpost --visibility public --accept-visibility-change-consequences
```

Alternatively, arrange specific organiser access after receiving the correct account identity. Do not guess or invite an account automatically. `EMAIL_DRAFT.txt` is local-only and must be reviewed, contact details filled, and sent by the author to submit@builderr.ai. Use the exact frozen source commit in manifest.json. No result file implies official qualification.
