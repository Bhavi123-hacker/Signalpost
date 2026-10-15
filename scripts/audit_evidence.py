"""Offline audit of actual output against locally stored immutable evidence.

No outbound request, benchmark answer or scoring estimate. A passing audit only
checks source binding and financial dimensions; it is not independent truth.
"""
import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from signalpost.batch import atomic_json
from signalpost.models import canonical,digest,utcnow,validate_envelopes
from signalpost.research import pointer,page_text


def audit(rows,state):
    failures=[]
    evidence_count=financial_count=0
    state=Path(state).resolve()
    for row in rows:
        org=row['organisation_number']
        index={e['id']:e for e in row['evidence']}
        for e in row['evidence']:
            path=(state/e['storage_ref']).resolve()
            try:
                if not path.is_relative_to(state/'evidence'): raise ValueError('storage reference outside evidence directory')
                data=path.read_bytes()
                if digest(data)!=e['content_sha256']: raise ValueError('content hash mismatch')
                if e['json_path'] is not None:
                    actual=pointer(json.loads(data),e['json_path'])
                    if canonical(actual)[:700]!=e['claim_span']: raise ValueError('JSON pointer/span mismatch')
                elif e['claim_span']:
                    import html
                    if e['claim_span'] not in html.unescape(data.decode('utf-8','replace')) and e['claim_span'] not in page_text(data)[1]: raise ValueError('text span not in source')
                evidence_count+=1
            except (ValueError,KeyError,OSError,TypeError,IndexError) as exc:
                failures.append({'organisation_number':org,'evidence_id':e['id'],'error':str(exc)})
        for c in row['claims']:
            if c['availability']!='available' or not c['field'].startswith('financial.'): continue
            try:
                e=index[c['evidence_ids'][0]]
                data=(state/e['storage_ref']).read_bytes()
                body=json.loads(data,parse_float=Decimal)
                record=body[int(e['json_path'].split('/')[1])]
                v=c['value']
                if Decimal(v['amount']) != pointer(body,e['json_path']): raise ValueError('financial amount mismatch')
                if v['currency'] != record['valuta'] or v['period']!=record['regnskapsperiode']: raise ValueError('financial dimensions mismatch')
                if v['scope']!={'SELSKAP':'company','KONSERN':'group'}[record['regnskapstype']]: raise ValueError('company/group mismatch')
                if v['organisation_number']!=record['virksomhet']['organisasjonsnummer'] or v['organisation_number']!=org: raise ValueError('financial entity mismatch')
                financial_count+=1
            except (ValueError,KeyError,OSError,TypeError,IndexError) as exc:
                failures.append({'organisation_number':org,'claim_id':c['id'],'error':str(exc)})
    validation=validate_envelopes(rows)
    return {'audited_at':utcnow(),'companies':len(rows),'evidence_references_checked':evidence_count,'financial_observations_checked':financial_count,
        'binding_validation':validation,'failures':failures,'passed':not failures and validation['passed'],
        'limitation':'Source binding self-audit, not independent factual or official scoring validation. Raw API units retained; PDF scale corroboration not performed.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--state',required=True); p.add_argument('--output',required=True)
    args=p.parse_args(); rows=[json.loads(l) for l in Path(args.input).read_text(encoding='utf-8').splitlines() if l.strip()]
    result=audit(rows,args.state); atomic_json(args.output,result)
    print(json.dumps({k:v for k,v in result.items() if k!='failures'},indent=2)); print('failure_count',len(result['failures']))
    raise SystemExit(0 if result['passed'] else 1)
