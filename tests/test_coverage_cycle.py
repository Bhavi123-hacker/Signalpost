"""Synthetic identity/ownership regressions. These are not collected evidence."""
import copy
import json
import pytest
import httpx
from signalpost.research import identity_gate, website, website_candidates, Profile
from signalpost.http import Fetcher, Budget
from signalpost.models import utcnow
from test_signalpost import ORG, OTHER, ENTITY, response, store
from test_signalpost import batch_args
from signalpost.batch import run_batch


def entity(name='SYNTHETIC FLOWERS AS'):
    return {**copy.deepcopy(ENTITY), 'navn': name, 'organisasjonsform': {'kode': 'AS'},
            'forretningsadresse': {'adresse': ['Testveien 50'], 'postnummer': '0373'}}


@pytest.mark.parametrize('number', [ORG, ORG[:3]+' - '+ORG[3:6]+'\n'+ORG[6:], ORG[:3]+'\u202f'+ORG[3:6]+'\u00a0'+ORG[6:]])
def test_literal_number_formats(number):
    assert identity_gate(ORG, 'SYNTHETIC AS', 'Synthetic AS org: '+number)['state'] == 'available'


def test_corroborated_legal_suffix_needs_every_signal():
    e = entity(); text='Synthetic Flowers | Org.nr. '+ORG+' | Testveien 50, 0373 Oslo'
    assert identity_gate(ORG, e['navn'], text)['state']=='ambiguous'
    gate=identity_gate(ORG, e['navn'], text, entity=e, policy='corroborated')
    assert gate['state']=='available' and len(gate['proof_spans'])==4
    for broken in [text.replace(ORG, OTHER), text.replace('0373','0374'), text.replace('Testveien 50','Testveien 51'), text.replace('Synthetic Flowers','Flowers'), text+' parent '+OTHER]:
        assert identity_gate(ORG, e['navn'], broken, entity=e, policy='corroborated')['state']=='ambiguous'
    assert identity_gate(ORG,e['navn'],text,entity={**e,'overordnetEnhet':OTHER},policy='corroborated')['state']=='ambiguous'


def test_conjunction_and_foundation_variants_are_bound_to_address():
    e=entity('SYNTHETIC GÅRD & GJESTEHUS AS')
    text='Synthetic Gård og Gjestehus AS '+ORG+' Testveien 50 0373'
    assert identity_gate(ORG,e['navn'],text,entity=e,policy='corroborated')['state']=='available'
    e=entity('STIFTELSEN SYNTHETIC SCHOOL');e['organisasjonsform']['kode']='STI'
    text='Synthetic School '+ORG+' Testveien 50 0373'
    assert identity_gate(ORG,e['navn'],text,entity=e,policy='corroborated')['state']=='available'
    assert identity_gate(ORG,e['navn'],text,entity={**e,'organisasjonsform':{'kode':'NUF'}},policy='corroborated')['state']=='ambiguous'


async def test_corroborated_proof_binds_four_actual_spans(store):
    e=entity(); text='<p>Synthetic Flowers | '+ORG+' | Testveien 50, 0373</p>'
    def handle(r):
        return httpx.Response(404) if r.url.path=='/robots.txt' else httpx.Response(200,text=text,headers={'content-type':'text/html'})
    p=Profile(ORG,'synthetic-cycle',utcnow());p.registry(response(store,e))
    f=Fetcher(store,Budget(10,20),transport=httpx.MockTransport(handle))
    await website(p,f,max_pages=1,identity_policy='corroborated')
    claim=p.claims['official_website']; assert len(claim['evidence_ids'])==4
    assert all(p.evidence[i]['claim_span'] in text for i in claim['evidence_ids'])
    await f.close()


async def test_conflicting_first_proof_cannot_be_overridden_by_later_page(store):
    def handle(r):
        if r.url.path=='/robots.txt':return httpx.Response(404)
        text='<a href="/contact">Contact</a><a href="/legal">Legal</a>' if r.url.path=='/' else ENTITY['navn']+' '+ORG+(' '+OTHER if r.url.path=='/contact' else '')
        return httpx.Response(200,text=text,headers={'content-type':'text/html'})
    p=Profile(ORG,'synthetic-cycle',utcnow());p.registry(response(store,ENTITY))
    f=Fetcher(store,Budget(10,20),transport=httpx.MockTransport(handle)); await website(p,f)
    assert 'official_website' not in p.claims
    assert p.candidates[0]['reason']=='Conflicting organisation numbers on page'
    await f.close()


def test_no_guessed_domains_and_generic_mailboxes():
    assert website_candidates({'navn':'SYNTHETIC AS'})==[]
    assert website_candidates({'navn':'SYNTHETIC AS','epostadresse':'synthetic@gmail.com'})==[]


async def test_missing_discovery_is_incomplete_not_confirmed_absence(store):
    p=Profile(ORG,'synthetic',utcnow()); p.entity={'navn':'SYNTHETIC AS'}
    f=Fetcher(store,Budget(0,10),transport=httpx.MockTransport(lambda r: pytest.fail('No candidate must not fetch')))
    await website(p,f)
    assert p.modules['website']['availability']=='failed'
    assert 'not confirmed absence' in p.modules['website']['explanation']
    assert f.budget.requests==0
    await f.close()


@pytest.mark.parametrize('strategy',['external-first','coverage-fair'])
async def test_external_first_preserves_proof_budget_before_optional_roles(tmp_path,strategy):
    entities=[]
    for org,domain in [(ORG,'fixture-mail-one.no'),(OTHER,'fixture-mail-two.no')]:
        e={**ENTITY,'organisasjonsnummer':org,'epostadresse':'post@'+domain}
        e.pop('hjemmeside');entities.append(e)
    bulk=tmp_path/'snapshot.jsonl';bulk.write_text('\n'.join(json.dumps(e) for e in entities))
    def handle(r):
        if 'regnskapsregisteret' in r.url.path:return httpx.Response(200,json=[])
        if r.url.path=='/robots.txt':return httpx.Response(404)
        if r.url.path.endswith('/roller'):return httpx.Response(200,json={'rollegrupper':[]})
        org=ORG if r.url.host=='fixture-mail-one.no' else OTHER
        return httpx.Response(200,text=ENTITY['navn']+' '+org,headers={'content-type':'text/html'})
    args=batch_args(tmp_path,[ORG,OTHER],bulk=str(bulk),strategy=strategy,modules='registry,financials,roles,website',max_requests=6,site_pages=1)
    assert await run_batch(args,transport=httpx.MockTransport(handle))==0
    report=json.loads((tmp_path/'report.json').read_text())
    assert report['coverage']['verified_website_companies']==2
    assert report['operations']['requests']==6
    assert report['coverage']['registry_anchored_companies']==2
    assert report['configuration']['strategy']==strategy


async def test_fair_round_reuses_actual_fetch_and_donates_unused_allocation(tmp_path):
    entities=[]
    for org,domain in [(ORG,'fixture-mail-one.no'),(OTHER,'fixture-mail-two.no')]:
        e={**ENTITY,'organisasjonsnummer':org,'epostadresse':'post@'+domain}; e.pop('hjemmeside');entities.append(e)
    bulk=tmp_path/'snapshot.jsonl';bulk.write_text('\n'.join(json.dumps(e) for e in entities))
    calls=[]
    def handle(r):
        calls.append(str(r.url))
        if 'regnskapsregisteret' in r.url.path:return httpx.Response(200,json=[])
        if r.url.host=='fixture-mail-two.no':return httpx.Response(403)
        if r.url.path=='/robots.txt':return httpx.Response(404)
        text='<a href="/contact">Contact</a>' if r.url.path=='/' else ENTITY['navn']+' '+ORG
        return httpx.Response(200,text=text,headers={'content-type':'text/html'})
    args=batch_args(tmp_path,[ORG,OTHER],bulk=str(bulk),strategy='coverage-fair',modules='registry,financials,roles,website',max_requests=6,site_pages=1)
    assert await run_batch(args,transport=httpx.MockTransport(handle))==0
    report=json.loads((tmp_path/'report.json').read_text())
    assert report['coverage']['verified_website_companies']==1
    assert report['operations']['requests']==len(calls)==6
    assert report['operations']['shared_response_hits']>=1
    assert sum('fixture-mail-one.no/'==url.split('://')[1] for url in calls)==1
    assert sum('fixture-mail-two.no/robots.txt' in url for url in calls)==1  # no retry of blocked source
