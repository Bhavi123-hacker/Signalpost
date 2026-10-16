"""Publish only NLOD official-data observations and run statistics.

Raw HTML and raw roles responses stay private. This is an explicitly labelled
filtered export, never a substitute for the original measured run output.
"""
import argparse
import copy
import gzip
import json
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from signalpost.batch import atomic_json,write_jsonl
from signalpost.models import MODULE_STATE,digest,validate_envelopes


def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--report',required=True); p.add_argument('--state',required=True); p.add_argument('--output',required=True)
    p.add_argument('--compress-output',action='store_true',help='Gzip large public exports for GitHub file-size limits')
    args=p.parse_args(); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    rows=[json.loads(l) for l in Path(args.input).read_text(encoding='utf-8').splitlines() if l.strip()]
    original_hash=digest(Path(args.input).read_bytes())
    filtered=[]; copied=set()
    for original in rows:
        row=copy.deepcopy(original)
        official_ids={e['id'] for e in row['evidence'] if e['source_class'].startswith('official_')}
        row['claims']=[c for c in row['claims'] if c['availability']!='available' or all(eid in official_ids for eid in c['evidence_ids'])]
        row['claims']=[c for c in row['claims'] if not c['field'].startswith('website') and c['field'] not in {'official_website','job_posting','dated_activity','public_brand','company_owned_profiles'}]
        used={eid for c in row['claims'] for eid in c['evidence_ids']}
        used.update(eid for m in row['modules'].values() for eid in m.get('source_evidence_ids',[]) if eid in official_ids)
        used.update(eid for change in row['changes'] for eid in (change.get('previous') or {}).get('evidence_ids',[]) if eid in official_ids)
        row['evidence']=[e for e in row['evidence'] if e['id'] in used and e['id'] in official_ids]
        hashes={e['content_sha256'] for e in row['evidence']}
        row['source_snapshots']=[s for s in row['source_snapshots'] if s['source_class'].startswith('official_') and s['content_sha256'] in hashes]
        current_ids={c['id'] for c in row['claims']}
        row['changes']=[c for c in row['changes'] if c['claim_id'] in current_ids]
        row['website_candidates']=[]
        for module in ['website','hiring','activity','public_brand','company_owned_profiles']:
            row['modules'][module]={'availability':'failed','state':MODULE_STATE['failed'],'explanation':'Omitted from public export because company-source redistribution rights are not established; original measured state is in report.json','final_timestamp':row['completed_at'],'retry_count':0}
        row['profile']={k:v for k,v in row['profile'].items() if not k.startswith('website') and k not in {'official_website','job_posting','dated_activity','public_brand','company_owned_profiles'}}
        row['profile']['evidence']={m:{'status':v['availability'],'note':v['explanation']} for m,v in row['modules'].items()}
        row['summary']['current_fact_count']=sum(c['availability']=='available' and not c['stale'] for c in row['claims'])
        row['summary']['business_description_claim_ids']=[k for k in row['summary']['business_description_claim_ids'] if k in current_ids]
        row['summary']['unknowns']=[{'field':m,'state':v['availability'],'reason':v['explanation']} for m,v in row['modules'].items() if v['availability']!='available']
        row['export_policy']={'kind':'filtered_official_data_export','original_output_sha256':original_hash,'raw_company_pages':'local only','raw_roles_responses':'local only; may contain birth dates','measured_coverage':'See unmodified report.json for original local-run counts'}
        filtered.append(row)
        for s in row['source_snapshots']:
            if s['source_class']=='official_roles': continue
            ref=s['storage_ref']
            if ref in copied: continue
            source=(Path(args.state)/ref).resolve()
            if not source.is_relative_to((Path(args.state)/'evidence').resolve()): raise ValueError('Invalid source evidence path')
            dest=out/'state'/ref; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,dest); copied.add(ref)
    validation=validate_envelopes(filtered)
    assert validation['passed'],validation
    if args.compress_output:
        from signalpost.models import canonical
        with (out/'envelopes.jsonl.gz').open('wb') as raw:
            with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as zipped:
                for row in filtered:
                    zipped.write((canonical(row)+'\n').encode('utf-8'))
    else:
        write_jsonl(out/'envelopes.jsonl',filtered)
    shutil.copyfile(args.report,out/'report.json')
    atomic_json(out/'export-validation.json',{'validation':validation,'copied_official_blobs':len(copied),'policy':'Official NLOD observations only; raw roles and company-owned pages excluded. Original live outputs remain local.'})
    print(json.dumps({'profiles':len(filtered),'official_blobs':len(copied),'output':str(out)}))


if __name__=='__main__': main()
