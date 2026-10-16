"""Offline collection funnel; absence of evidence is not proven absence online."""
import argparse
import json
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlsplit
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from signalpost.models import digest,utcnow

EXTERNAL={'website_description','website_email','website_phone','website_service','website_location','website_leadership','dated_activity','job_posting','public_brand'}

def diagnose(rows,events):
    funnel=Counter();outcomes=Counter();methods=defaultdict(Counter);categories=Counter();allocation=Counter();starts=defaultdict(list)
    for event in events:
        starts[event.get('organisation_number')].append(event)
        url=urlsplit(event['url'])
        kind='robots' if url.path.endswith('/robots.txt') else 'registry_identity' if url.hostname=='data.brreg.no' and '/enhetsregisteret/api/enheter' in url.path and not url.path.endswith('/roller') else 'accounts' if '/regnskapsregisteret/' in url.path else 'roles' if url.path.endswith('/roller') else 'workplaces' if '/underenheter' in url.path else 'official_group' if url.hostname=='data.brreg.no' else 'discovery_api' if url.hostname=='query.wikidata.org' else 'company_page'
        allocation[kind]+=1
    for row in rows:
        cs=[c for c in row['claims'] if c['availability']=='available' and not c['stale']]
        candidates=row['website_candidates'];attempts=[c for c in candidates if c.get('checks')]
        verified=[c for c in candidates if c.get('status')=='verified']
        substantive=any(c['field'] in EXTERNAL for c in cs)
        funnel.update({'inputs':1,'identity_available':row['legal_identity']['status']=='available','candidate_discovered':bool(candidates),'candidate_html_fetched':bool(attempts),'ownership_verified':bool(verified),'substantive_external':substantive})
        verified_pages={s['final_url'] for s in row['source_snapshots'] if s['source_class']=='company_owned'}
        funnel['companies_with_additional_company_pages']+=bool(verified_pages)
        for c in candidates:methods[c['method']][c['status']]+=1
        categories.update({c['field'] for c in cs})
        reasons='; '.join(str(c.get('reason','')) for c in candidates)+'; '+row['modules']['website']['explanation']
        # Exclusive dominant bounded-run outcome; no inference of universal absence.
        if substantive:reason='substantive_accepted'
        elif verified:reason='verified_site_no_substantive_extraction'
        elif 'Time budget' in reasons or 'time' in reasons.lower() and 'cutoff' in reasons.lower():reason='time_budget_exhausted'
        elif 'budget exhausted' in reasons.lower() or 'allocation exhausted' in reasons.lower():reason='request_starvation'
        elif any(c.get('status')=='blocked' for c in candidates):reason='blocked_access'
        elif any(c.get('status')=='ambiguous' for c in candidates):reason='identity_ambiguous'
        elif any('Timeout' in c.get('reason','') for c in candidates):reason='source_timeout'
        elif not candidates:reason='missing_discovery_path'
        elif any(c.get('status')=='rejected' for c in candidates):reason='candidate_source_absent'
        else:reason='other_fetch_or_parser_failure'
        outcomes[reason]+=1
    return {'created_at':utcnow(),'funnel':dict(funnel),'dominant_website_outcomes':dict(outcomes),'candidates_by_method':dict(methods),'companies_by_populated_field':dict(categories),'request_allocation':dict(allocation),'recorded_request_starts':len(events),'interpretation':'Bounded collection outcomes only. Missing discovery path/unattempted/ambiguous is not confirmed absence. Extraction counts require substantive supported facts, never URL-only.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--requests',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    load=lambda n:[json.loads(l) for l in Path(n).read_text(encoding='utf-8').splitlines() if l.strip()]
    result=diagnose(load(a.input),load(a.requests));result['input_output_sha256']=digest(Path(a.input).read_bytes())
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
