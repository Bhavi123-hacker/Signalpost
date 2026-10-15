"""Package an immutable Git source commit plus local verification handoff.

The embedded manifest hashes payload files, never itself. The external manifest
adds the final ZIP hash. Neither source commit nor ZIP hash depends on itself.
No network, credential lookup, GitHub write or email operation is performed.
"""
import argparse
import hashlib
import io
import json
import re
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]


def sha(data): return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def allowed(name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name: return False
    if any(part in {'.git','.venv','.venv-linux','private','reference','out','__pycache__','.pytest_cache'} or part.startswith('.env') or part.startswith('.venv') for part in path.parts): return False
    if name.startswith('artifacts/development-'): return False
    if name.startswith('docs/rules/') and not name.endswith('.json'): return False
    return True


def main():
    p=argparse.ArgumentParser(); p.add_argument('--source-commit',required=True); p.add_argument('--verification',required=True); p.add_argument('--output',default='submission/Signalpost-submission.zip')
    args=p.parse_args()
    commit=git('rev-parse',args.source_commit+'^{commit}').decode().strip()
    archive=git('archive','--format=zip',commit)
    payload={}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for info in z.infolist():
            if info.is_dir(): continue
            if not allowed(info.filename): raise ValueError('Tracked file violates packaging policy: '+info.filename)
            payload[info.filename]=z.read(info)
    # Tokens/keys are never printed. Fail with filenames only if accidental tracked material exists.
    secret_pattern=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    for name,data in payload.items():
        if secret_pattern.search(data): raise ValueError('Potential secret pattern in '+name)
    verification=json.loads(Path(args.verification).read_text(encoding='utf-8'))
    # Later packaging metadata is explicit; executable research source stays frozen.
    metadata_paths=['PROGRESS.md','docs/verification-report.md','docs/limitations.md',
        'docs/model-api-costs.md','submission/PUBLICATION.md','scripts/package_submission.py']
    for name in metadata_paths:
        payload[name]=(ROOT/name).read_bytes()
    payload['submission/verification-final.json']=(json.dumps(verification,indent=2,ensure_ascii=False)+'\n').encode()
    try:
        remote=git('remote','get-url','origin').decode().strip()
        if '@' in remote.split('://')[-1].split('/')[0]: raise ValueError('Credential-bearing remote URL rejected')
        repository=remote.removesuffix('.git')
    except subprocess.CalledProcessError:
        repository=None
    summary=verification.get('summary',{})
    visibility=verification.get('repository_visibility','unknown')
    command='python scripts/run_competition_batch.py --organisations INPUT.jsonl --output OUTPUT.jsonl --report REPORT.json --state STATE --run-id official-001 --max-requests 2000 --max-seconds 2700'
    email=f'''To: submit@builderr.ai
Subject: Signalpost entry — Bhavy Garg, 24BAI1088, VIT Chennai

Author: Bhavy Garg
Student ID: 24BAI1088
Institution: VIT Chennai
Contact email/phone for results: [AUTHOR: CONFIRM CONTACT DETAILS BEFORE SENDING]
Agent: Signalpost (deterministic no-model mode)
Repository: {repository or '[repository URL not configured]'}
Repository visibility: {visibility}; author explicitly authorised public visibility on 15 October 2026.
Frozen source commit: {commit}

Install Python 3.12+ and: python -m pip install -r requirements.lock.txt
Run from the activated isolated environment:
{command}
Append --bulk BRREG.csv.gz when using the evaluator-supplied frozen registry. Use its actual resource settings; retrieved public rules do not specify numerical caps.

Local package: {str((ROOT/args.output).resolve())}
Source and instructions: {ROOT/'README.md'}
100-company input: {ROOT/'data/inputs/smoke-100.jsonl'}
100-company report/export: {ROOT/'artifacts/smoke-100'}
1,000-company report/export: {ROOT/'artifacts/scale-1000'}
Verification and limits: {ROOT/'docs/verification-report.md'}
Exact frozen-commit checks: submission/verification-final.json in the ZIP.

Measured summary: {json.dumps(summary,ensure_ascii=False)}
Paid model/search/data API spend: USD 0.00. Expected paid API cost per official run: USD 0.00 (no paid integration).
Other internet/electricity/hardware/assistant-plan costs are separate and not estimated.
Original code: MIT. BRREG data: NLOD. Runtime licences: THIRD_PARTY_NOTICES.md and docs/dependency-licences.json.
Raw company HTML, raw roles with birth dates, personal credentials and virtual environments are excluded. Official-data exports are explicitly filtered subsets; original-run counts are in reports.
No official qualification or private-pool score is claimed. Financial values are exact normalised API fields; independent PDF scale corroboration remains a declared limitation.

This is a LOCAL DRAFT ONLY. Nothing has been sent.
'''
    payload['submission/EMAIL_DRAFT.txt']=email.encode('utf-8')
    rules=json.loads((ROOT/'docs/rules/retrieval.json').read_text())
    manifest={'manifest_version':1,'created_at':datetime.now(UTC).isoformat(),'author':{'name':'Bhavy Garg','student_id':'24BAI1088','institution':'VIT Chennai'},
        'source_commit':commit,'source_tree':git('rev-parse',commit+'^{tree}').decode().strip(),'repository_url':repository,'repository_visibility':visibility,
        'completion_status':{'local_implementation':'finished subject to declared limitations','official_qualification':'not evaluated','submission_sent':False,'public_publication':visibility=='public'},
        'contract_retrievals':rules,'actual_verification_summary':summary,'run_command':command,'third_party_api_cost_usd':0,
        'remaining_handoff':['Confirm author contact detail','Review and send email manually; no email was sent','Use organiser-supplied official run limits and frozen registry/cutoff'],
        'source_archive_sha256':sha(archive),'payload_sha256':{n:sha(b) for n,b in sorted(payload.items())},
        'post_freeze_metadata_paths':metadata_paths,
        'source_scope':'Research runtime, tests, schemas and requirements are the frozen source commit. Listed packaging/report files overlay later authorisation and exact-commit verification; their payload hashes are explicit.',
        'manifest_scope':'Embedded manifest hashes payload excluding itself; external manifest additionally records final ZIP hash.'}
    payload['submission/manifest.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
    output=(ROOT/args.output).resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,15,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16
            z.writestr(info,data)
    manifest['submission_zip_sha256']=sha(output.read_bytes())
    manifest['submission_zip_bytes']=output.stat().st_size
    (ROOT/'submission/manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (ROOT/'submission/EMAIL_DRAFT.txt').write_text(email,encoding='utf-8')
    (ROOT/'submission'/('Signalpost-source-'+commit[:12]+'.zip')).write_bytes(archive)
    print(json.dumps({'source_commit':commit,'zip':str(output),'bytes':output.stat().st_size,'sha256':manifest['submission_zip_sha256'],'payload_files':len(payload)},indent=2))


if __name__=='__main__': main()
