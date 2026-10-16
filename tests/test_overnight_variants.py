"""Synthetic regression examples, never live evidence or coverage claims."""
import httpx
from signalpost.http import Budget,Fetcher,Result
from signalpost.models import utcnow,validate_envelopes
from signalpost.research import Profile,extract_site,page_text,website
from test_signalpost import ORG,ENTITY,response,store

def site_result(store,body):
    data=body.encode();return Result(store.snapshot({'source_url':'https://synthetic.no/','final_url':'https://synthetic.no/','source_class':'company_owned','retrieved_at':utcnow(),'http_status':200,'content_type':'text/html'},data),data)

def test_expanded_legacy_html_description_and_labelled_contacts(store):
    body='<html><body><p>Synthetic Example AS is an independent consultancy company providing engineering services to local clients in Norway.</p><p>E-post: contact@synthetic.no</p><p>Telefon: +47 22 33 44 55</p></body></html>'
    r=site_result(store,body)
    def extract(mode):
        p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY));extract_site(p,[(r,*page_text(r.data))],extraction=mode);return p
    baseline=extract('baseline');expanded=extract('expanded')
    assert not any(c['field']=='website_description' for c in baseline.claims.values())
    facts={c['field']:c for c in expanded.claims.values()}
    assert facts['website_description']['value'].startswith('Synthetic Example AS')
    assert facts['website_phone']['value']=='+47 22 33 44 55'
    assert facts['website_email']['value']=='contact@synthetic.no'
    for field in ('website_description','website_phone','website_email'):
        for eid in facts[field]['evidence_ids']:assert expanded.evidence[eid]['claim_span'] in body

def test_expanded_excludes_forms_chrome_credits_and_long_numbers(store):
    body='<html><body><nav><p>We provide navigation services in this synthetic cookie and login widget for no real company.</p></nav><form><p>We provide arbitrary text in an input form and should never publish this as a business description.</p></form><div class="cookie-consent"><p>We offer personalisation of user experience using analytics and these statements are not business activities.</p></div><p>Developed by E-post: developer@synthetic.no Telefon: 22 33 44 55</p><p>Telefon: 123456789</p><p>Telefon: 12 34 56 78 9</p></body></html>'
    r=site_result(store,body);p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY));extract_site(p,[(r,*page_text(r.data))],extraction='expanded')
    assert not any(c['field'] in {'website_description','website_phone','website_email'} for c in p.claims.values())

async def test_expanded_never_overrides_wrong_company_gate(store):
    html='<html><body><p>Synthetic Example AS is an independent consultancy company providing engineering services to local clients in Norway.</p></body></html>'
    def handle(req):
        return httpx.Response(404) if req.url.path=='/robots.txt' else httpx.Response(200,text=html,headers={'content-type':'text/html'})
    f=Fetcher(store,Budget(10,20),transport=httpx.MockTransport(handle));p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY))
    await website(p,f,extraction='expanded',page_policy='focused');assert p.modules['website']['availability']!='available'
    assert not any(c['field'].startswith('website_') for c in p.claims.values());await f.close()

async def test_focused_page_order_uses_real_navigation_only(store):
    proof=f'<html><body>Synthetic Example AS {ORG}<a href="/about">About us</a><a href="/news">News</a><a href="/jobs">Jobs</a></body></html>'
    calls=[]
    def handle(req):
        calls.append(req.url.path);return httpx.Response(404) if req.url.path=='/robots.txt' else httpx.Response(200,text=proof,headers={'content-type':'text/html'})
    f=Fetcher(store,Budget(10,20),transport=httpx.MockTransport(handle));p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY))
    await website(p,f,max_pages=2,page_policy='focused');assert '/jobs' in calls and '/about' not in calls and '/news' not in calls;await f.close()

def test_contacts_quoted_from_installer_or_group_are_quarantined(store):
    body='<html><body><div><p>Priser og betingelser avtales direkte med våre installatører.</p><p>Telefon: 91 77 11 10 E-post: partner@synthetic.no <a href="mailto:partner@synthetic.no">Email</a><a href="tel:91771110">Phone</a></p></div><div><p>We are part of the Parent group!</p><p>Phone: +47 90 99 69 93 <a href="mailto:ceo@parent.no">CEO</a></p></div><p><a href="mailto://malformed@synthetic.no">bad syntax</a></p></body></html>'
    r=site_result(store,body);p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY));extract_site(p,[(r,*page_text(r.data))],extraction='expanded')
    assert not any(c['field'] in {'website_phone','website_email'} for c in p.claims.values())

def test_contact_formatting_does_not_duplicate_facts(store):
    body='<html><body><p>Telefon: +47 22 33 44 55 <a href="tel:22334455">Call</a></p><p>E-post: contact@synthetic.no <a href="mailto:contact@synthetic.no">Email</a></p></body></html>'
    r=site_result(store,body);p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY));extract_site(p,[(r,*page_text(r.data))],extraction='expanded');extract_site(p,[(r,*page_text(r.data))],extraction='expanded')
    assert sum(c['field']=='website_phone' for c in p.claims.values())==1
    assert sum(c['field']=='website_email' for c in p.claims.values())==1

def test_stale_description_not_referenced_as_current_summary(store):
    p=Profile(ORG,'first',utcnow());p.registry(response(store,ENTITY));prior=p.finalize()
    p2=Profile(ORG,'failed-refresh',utcnow());p2.mark('registry','failed','Synthetic outage');current=p2.finalize(prior)
    assert not current['summary']['business_description_claim_ids']
    assert any(c['field']=='registered_activity' and c['stale'] for c in current['claims'])

def test_advice_article_is_not_named_service_but_buyable_product_is(store):
    for path,extra,expected in [('/services/better-lighting','',False),('/products/synthetic-widget','<form action="/cart/add"><button name="add">Buy item</button></form>',True)]:
        body='<html><main><h1>Synthetic useful heading</h1><p>This explicitly synthetic company-authored paragraph describes a source page; its URL alone does not establish the meaning of a service offering.</p>'+extra+'</main></html>'
        r=site_result(store,body);r.snapshot['final_url']='https://synthetic.no'+path
        p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY));extract_site(p,[(r,*page_text(r.data))],extraction='expanded')
        assert any(c['field']=='website_service' for c in p.claims.values())==expected

async def test_adaptive_page_budget_keeps_missing_description_and_skips_repetition(store):
    calls=[]
    proof=f'<html><body>Synthetic Example AS {ORG}<p>Phone: 22 33 44 55</p><p>Email: contact@synthetic-example.no</p><a href="/about">About us</a><a href="/contact">Contact</a></body></html>'
    about='<html><body><p>We provide synthetic engineering services for explicitly fictional clients in this offline fixture and do not represent any real company.</p></body></html>'
    def handle(req):
        calls.append(req.url.path);return httpx.Response(404) if req.url.path=='/robots.txt' else httpx.Response(200,text=about if req.url.path=='/about' else proof,headers={'content-type':'text/html'})
    f=Fetcher(store,Budget(10,20),transport=httpx.MockTransport(handle));p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY))
    await website(p,f,extraction='expanded',page_policy='adaptive')
    assert '/about' in calls and '/contact' not in calls
    assert any(c['field']=='website_description' for c in p.claims.values());await f.close()

def test_known_contact_error_retracted_but_failed_refresh_preserves_history(store):
    body='<html><div><p>Priser avtales direkte med installatør.</p><p><a href="mailto:partner@synthetic.no">Partner contact</a></p></div></html>'
    r=site_result(store,body);p=Profile(ORG,'first',utcnow());p.registry(response(store,ENTITY))
    eid=p.ev(r,None,span='mailto:partner@synthetic.no');key='website_email:partner@synthetic.no';p.add('website_email','partner@synthetic.no',eid,key=key)
    prior=store.save(p.finalize(),'synthetic-input')
    outage=Profile(ORG,'outage',utcnow());outage.mark('website','failed','Synthetic timeout');carried=outage.finalize(prior)
    assert next(c for c in carried['claims'] if c['id']==key)['stale']
    fixed=Profile(ORG,'correction',utcnow());fixed.registry(response(store,ENTITY));extract_site(fixed,[(r,*page_text(r.data))],extraction='expanded')
    row=store.save(fixed.finalize(prior),'synthetic-input');c=next(c for c in row['claims'] if c['id']==key)
    assert c['availability']=='ambiguous' and c['value'] is None and c['retracted'] and not c['stale']
    assert any(c['type']=='retracted' for c in row['changes'])
    assert store.db.execute('SELECT count(*) FROM history').fetchone()[0]==2
    assert validate_envelopes([row])['passed']

async def test_same_host_staff_contact_cannot_prove_publisher_ownership(store):
    def handle(req):
        if req.url.path=='/robots.txt':return httpx.Response(404)
        body=f'<h1>{ENTITY["navn"]}</h1><p>Org {ORG}</p>' if req.url.path.startswith('/staff/') else '<a href="/staff/synthetic-person">Contact person</a>'
        return httpx.Response(200,text=body,headers={'content-type':'text/html'})
    f=Fetcher(store,Budget(10,20),transport=httpx.MockTransport(handle));p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY))
    await website(p,f,extraction='expanded',page_policy='adaptive');assert 'official_website' not in p.claims;await f.close()

def test_official_export_removes_company_brand_from_every_profile_projection(store,tmp_path):
    import json,subprocess,sys
    from pathlib import Path
    p=Profile(ORG,'synthetic-export',utcnow());p.registry(response(store,ENTITY));r=site_result(store,'<p>Synthetic private-source alias</p>')
    p.verified_urls.add(r.snapshot['final_url']);eid=p.ev(r,None,span='Synthetic private-source alias');p.add('public_brand','Synthetic private-source alias',eid,key='brand:synthetic')
    row=p.finalize();assert 'public_brand' in row['profile']
    inp=tmp_path/'in.jsonl';inp.write_text(json.dumps(row)+'\n');report=tmp_path/'report.json';report.write_text('{}');out=tmp_path/'export'
    root=Path(__file__).resolve().parents[1]
    proc=subprocess.run([sys.executable,str(root/'scripts/export_public.py'),'--input',str(inp),'--report',str(report),'--state',str(store.root),'--output',str(out)],capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    exported=json.loads((out/'envelopes.jsonl').read_text(encoding='utf-8'))
    assert 'public_brand' not in exported['profile'] and not any(c['field']=='public_brand' for c in exported['claims'])
    assert all(e['source_class'].startswith('official_') for e in exported['evidence'])

def test_privacy_contact_and_navigation_are_not_business_descriptions(store):
    for path,meta,paragraph in [('/privacy','Read how we protect your personal data and your privacy on this company website.','Our privacy policy describes how we process personal data and protect the rights of individuals.'),('/contact','Here are the different options for how to contact us with any question about our company.','Fill in your contact details and use the contact form to send the synthetic company a message.'),('/','', 'Du leser nå innhold for privatkunder. Her finner du innhold for bedrift og borettslag.')]:
        body='<html><meta name="description" content="'+meta+'"><main><p>'+paragraph+'</p></main></html>'
        r=site_result(store,body);r.snapshot['final_url']='https://synthetic.no'+path;p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY))
        extract_site(p,[(r,*page_text(r.data))],extraction='expanded')
        assert not any(c['field']=='website_description' for c in p.claims.values())

def test_product_excerpt_is_scoped_to_product_not_company_business(store):
    body='<html><meta name="description" content="This synthetic widget is offered for sale with explicit controls on a verified source page."><h1>Synthetic widget</h1><form action="/cart/add"><button name="add">Buy</button></form></html>'
    r=site_result(store,body);r.snapshot['final_url']='https://synthetic.no/products/widget';p=Profile(ORG,'synth',utcnow());p.registry(response(store,ENTITY));extract_site(p,[(r,*page_text(r.data))],extraction='expanded')
    assert any(c['field']=='website_service' for c in p.claims.values())
    assert not any(c['field']=='website_description' for c in p.claims.values())
