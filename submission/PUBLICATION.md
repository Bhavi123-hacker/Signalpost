# Publication and submission handoff

The authorised GitHub repository is now **public**: https://github.com/Bhavi123-hacker/Signalpost . The author explicitly requested public visibility on 15 October 2026; the visibility change succeeded and GitHub confirmed `isPrivate=false`. Source and permitted official-data exports have been pushed. No email has been sent and no competition entry has been submitted.

Future source publication must include only permitted source and reports. These are the publication commands; the initial push and later authorised visibility change have already been performed:

```sh
git remote -v
git status --short
git push -u origin main
```

Do not add private/, out/, .env files, raw company pages, virtual environments, tokens or personal-session data. The repository ignores those paths; the packaging script uses an explicit tracked-source allowlist and permitted export directory.

The following visibility command was executed after the author's explicit request:

```sh
gh repo edit Bhavi123-hacker/Signalpost --visibility public --accept-visibility-change-consequences
```

`EMAIL_DRAFT.txt` is local-only and must be reviewed, contact details filled, and sent by the author to submit@builderr.ai. Use the exact frozen source commit in manifest.json. No result file implies official qualification. The ZIP overlays explicitly listed later reports/packaging metadata on the frozen research source; its manifest identifies every overlay and payload hash.
