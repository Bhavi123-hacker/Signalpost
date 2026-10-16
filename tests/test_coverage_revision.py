"""Synthetic regression bodies only; never live company evidence."""
import asyncio
import json
import time
from datetime import UTC,datetime
import httpx
import pytest
from signalpost.batch import coverage_report,run_batch
from signalpost.http import Budget,Fetcher,Result
from signalpost.models import utcnow,validate_envelopes
from signalpost.research import Profile,identity_gate,website,page_text,extract_site
from signalpost.site_extract import job_record
from test_signalpost import ENTITY,ORG,OTHER,batch_args,response,store
from test_signalpost import account_body
from signalpost.research import financials


async def test_filtered_identity_preserves_original_row_evidence(tmp_path):
    calls=[]
    def handle(r):
        calls.append(str(r.url))
        assert r.url.params['organisasjonsnummer']==ORG+','+OTHER
        return httpx.Response(200,json={'_embedded':{'enheter':[ENTITY,{**ENTITY,'organisasjonsnummer':OTHER,'navn':'OTHER SYNTHETIC AS'}]},'page':{'totalPages':1}})
    inp=tmp_path/'in.jsonl';inp.write_text('\n'.join(json.dumps({'organisation_number':o}) for o in [ORG,OTHER]))
    args=batch_args(tmp_path,[ORG,OTHER]);args.modules='registry';args.max_requests=1
    assert await run_batch(args,transport=httpx.MockTransport(handle))==0
    rows=[json.loads(l) for l in open(args.output,encoding='utf-8')]
    assert len(calls)==1 and validate_envelopes(rows)['passed']
    assert rows[1]['legal_identity']['legal_name']=='OTHER SYNTHETIC AS'
    assert any(e['json_path']=='/_embedded/enheter/1/navn' for e in rows[1]['evidence'])


async def test_filtered_unrequested_entity_does_not_attach(tmp_path):
    def handle(r):
        if 'organisasjonsnummer' in r.url.params:return httpx.Response(200,json={'_embedded':{'enheter':[{**ENTITY,'organisasjonsnummer':'999999999'}]}})
        org=r.url.path.rsplit('/',1)[1]
        return httpx.Response(200,json={**ENTITY,'organisasjonsnummer':org})
    inp=tmp_path/'in.jsonl';inp.write_text('\n'.join(json.dumps({'organisation_number':o}) for o in [ORG,OTHER]))
    args=batch_args(tmp_path,[ORG,OTHER]);args.modules='registry';args.max_requests=5
    assert await run_batch(args,transport=httpx.MockTransport(handle))==0
    rows=[json.loads(l) for l in open(args.output,encoding='utf-8')]
    assert [r['legal_identity']['organisation_number'] for r in rows]==[ORG,OTHER]


async def test_same_run_shared_response_and_next_run_rechecks(store):
    calls=[]
    def handle(r):calls.append(r);return httpx.Response(200,content=b'synthetic')
    f=Fetcher(store,Budget(10,10),transport=httpx.MockTransport(handle))
    a,b=await asyncio.gather(f.get('https://synthetic.no/a','company_owned',robots=False),f.get('https://synthetic.no/a','company_owned',robots=False))
    assert len(calls)==1 and f.shared_hits==1 and a.snapshot['retrieved_at']==b.snapshot['retrieved_at']
    await f.close()
    g=Fetcher(store,Budget(10,10),transport=httpx.MockTransport(handle));await g.get('https://synthetic.no/a','company_owned',robots=False)
    assert len(calls)==2
    await g.close()


async def test_structured_legal_identity_and_mailto_nav(store):
    home='<html><a href="mailto:contact@synthetic.no">Contact</a><a href="/contact">Contact us</a><main><p>This is a synthetic long main paragraph for testing actual source extraction rather than an industry label or a guessed company description.</p></main></html>'
    proof=json.dumps({'@type':'Organization','legalName':ENTITY['navn'],'taxID':ORG})
    def handle(r):
        if r.url.path=='/robots.txt':return httpx.Response(404)
        return httpx.Response(200,text=home if r.url.path=='/' else '<script type="application/ld+json">'+proof+'</script>',headers={'content-type':'text/html'})
    f=Fetcher(store,Budget(10,20),transport=httpx.MockTransport(handle));p=Profile(ORG,'test',utcnow());p.registry(response(store,ENTITY))
    await website(p,f)
    assert p.modules['website']['availability']=='available'
    assert len(p.claims['official_website']['evidence_ids'])==2
    assert any(c['field']=='website_description' for c in p.claims.values())
    await f.close()


def test_normalized_legal_name_preserves_all_tokens():
    assert identity_gate(ORG,'SYNTHETIC-EXAMPLE AS','Synthetic Example AS '+ORG)['state']=='available'
    assert identity_gate(ORG,'SYNTHETIC EXAMPLE AS','Example AS '+ORG)['state']=='ambiguous'
    assert identity_gate(ORG,'SYNTHETIC EXAMPLE AS','Synthetic Example AS '+ORG+' parent '+OTHER)['state']=='ambiguous'


def test_url_alone_is_not_substantive_external_coverage(store):
    p=Profile(ORG,'test',utcnow());p.registry(response(store,ENTITY));eid=p.ev(response(store,ENTITY),'/hjemmeside');p.add('official_website',ENTITY['hjemmeside'],eid)
    report=coverage_report([p.finalize()]);assert report['verified_website_companies']==1 and report['externally_enriched_companies']==0


@pytest.mark.parametrize('until,expected',[('2020-12-31','expired'),('2028-12-31','within_published_application_window'),(None,'opening_status_unverified')])
def test_job_is_not_silently_called_open(until,expected):
    item={'title':'SYNTHETIC vacancy','datePosted':'2026-01-01','hiringOrganization':{'name':ENTITY['navn']}}
    if until:item['validThrough']=until
    assert job_record(item,ENTITY['navn'],datetime(2026,10,15,tzinfo=UTC))['opening_status']==expected
    item['datePosted']='2027-01-01';assert job_record(item,ENTITY['navn'],datetime(2026,10,15,tzinfo=UTC)) is None


def test_news_date_has_its_own_literal_evidence(store):
    item={'@type':'NewsArticle','headline':'SYNTHETIC title','datePublished':'2026-02-01'}
    body=('<script type="application/ld+json">'+json.dumps(item)+'</script>').encode()
    result=Result(store.snapshot({'source_url':'https://synthetic.no/news/a','final_url':'https://synthetic.no/news/a','source_class':'company_owned','retrieved_at':utcnow(),'http_status':200,'content_type':'text/html'},body),body)
    p=Profile(ORG,'test',utcnow());p.registry(response(store,ENTITY));extract_site(p,[(result,*page_text(body))])
    c=next(c for c in p.claims.values() if c['field']=='dated_activity')
    assert {'SYNTHETIC title','2026-02-01'}<={p.evidence[e]['claim_span'] for e in c['evidence_ids']}


def test_nuf_is_foreign_registration_and_finances_are_labelled(store):
    p=Profile(ORG,'test',utcnow());p.registry(response(store,{**ENTITY,'organisasjonsform':{'kode':'NUF'}}))
    assert p.claims['entity_kind']['value']=='registered_foreign_enterprise'
    financials(p,response(store,account_body(currency='SEK')))
    value=next(c['value'] for c in p.claims.values() if c['field']=='financial.revenue')
    assert 'not evidence of Norwegian branch-only' in value['reporting_entity_context']
    assert 'not sales-only' in value['metric_definition']


def test_non_finite_financial_amount_is_quarantined(store):
    p=Profile(ORG,'test',utcnow());body=account_body();body[0]['resultatregnskapResultat']['driftsresultat']['driftsinntekter']['sumDriftsinntekter']=float('nan')
    financials(p,response(store,body));assert not any(c['availability']=='available' and c['field']=='financial.revenue' for c in p.claims.values())


async def test_shared_official_cooldown_waits_instead_of_starving_later_identity(store):
    calls=[]
    def handle(r):calls.append(r);return httpx.Response(200,json=ENTITY)
    f=Fetcher(store,Budget(3,5),transport=httpx.MockTransport(handle));f.cooldowns['data.brreg.no']=time.monotonic()+.03
    await f.get('https://data.brreg.no/synthetic','official_registry',robots=False)
    assert len(calls)==1 and f.budget.requests==1 and f.cooldowns['data.brreg.no']==0
    await f.close()


def test_unknown_explicit_financial_unit_is_withheld(store):
    p=Profile(ORG,'test',utcnow());body=account_body();body[0]['enhet']='unknown denomination'
    financials(p,response(store,body));assert not any(c['availability']=='available' and c['field'].startswith('financial.') for c in p.claims.values())


async def test_cross_host_legal_page_cannot_prove_original_host(store):
    def handle(r):
        if r.url.path=='/robots.txt':return httpx.Response(404)
        if r.url.path=='/contact':return httpx.Response(302,headers={'location':'https://other-synthetic.no/proof'})
        body=f'<p>{ENTITY["navn"]} {ORG}</p>' if r.url.host=='other-synthetic.no' else '<a href="/contact">Contact</a>'
        return httpx.Response(200,text=body,headers={'content-type':'text/html'})
    f=Fetcher(store,Budget(15,15),transport=httpx.MockTransport(handle));p=Profile(ORG,'test',utcnow());p.registry(response(store,ENTITY))
    await website(p,f);assert 'official_website' not in p.claims
    assert any('redirected off' in e['message'] for e in p.errors)
    await f.close()


async def test_roles_precede_speculative_email_and_survive_zero_final_allocation(tmp_path):
    events=[]
    def handle(r):
        events.append(str(r.url))
        if r.url.path.endswith('/roller'):
            return httpx.Response(200,json={'rollegrupper':[{'type':{'kode':'STYR'},'roller':[{'type':{'kode':'LEDE'},'person':{'navn':{'fornavn':'Synthetic','etternavn':'Person'}}}]}]})
        if '/regnskapsregisteret/' in r.url.path:return httpx.Response(200,json=[])
        if r.url.path=='/robots.txt':return httpx.Response(404)
        return httpx.Response(200,text=f'<p>{ENTITY["navn"]} {ORG}</p>',headers={'content-type':'text/html'})
    args=batch_args(tmp_path,[ORG,OTHER],max_requests=10,modules='registry,financials,website,roles')
    bulk=tmp_path/'bulk.jsonl';bulk.write_text(json.dumps(ENTITY)+'\n'+json.dumps({**ENTITY,'organisasjonsnummer':OTHER,'navn':'OTHER SYNTHETIC AS','hjemmeside':'','epostadresse':'mail@external-bookkeeper.no'}))
    args.bulk=str(bulk)
    assert await run_batch(args,transport=httpx.MockTransport(handle))==0
    first_role=next(i for i,u in enumerate(events) if '/roller' in u)
    weak=next(i for i,u in enumerate(events) if 'external-bookkeeper' in u)
    assert first_role<weak
    rows=[json.loads(l) for l in open(args.output,encoding='utf-8')]
    assert all(r['modules']['roles']['availability']=='available' for r in rows)


async def test_exact_entity_on_shared_staff_profile_is_not_site_ownership(store):
    def handle(r):
        if r.url.path=='/robots.txt':return httpx.Response(404)
        if r.url.host=='synthetic-example.no':return httpx.Response(302,headers={'location':'https://shared-synthetic.no/medarbeidarar/synthetic-person/'})
        return httpx.Response(200,text=f'<h1>{ENTITY["navn"]}</h1><p>Org {ORG}</p><a href="mailto:network@shared-synthetic.no">Group contact</a>',headers={'content-type':'text/html'})
    f=Fetcher(store,Budget(10,15),transport=httpx.MockTransport(handle));p=Profile(ORG,'test',utcnow());p.registry(response(store,ENTITY));await website(p,f)
    assert p.modules['website']['availability']=='ambiguous'
    assert not any(c['field'].startswith('website') or c['field']=='official_website' for c in p.claims.values())
    assert 'site ownership' in p.candidates[0]['reason']
    await f.close()
