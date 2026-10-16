"""All HTTP bodies and names in this file are explicitly SYNTHETIC fixtures.

Organisation numbers are valid identifiers used to exercise checks, not evidence.
No fixture output is represented as a real collected profile.
"""
import asyncio
import copy
import json
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError

from signalpost.batch import load_bulk, normalize_csv, read_inputs, run_batch
from signalpost.cli import main, parser
from signalpost.http import Budget, FetchError, Fetcher, PinnedBackend, REQUEST_SCOPE, resolve_public, safe_url
from signalpost.models import Claim, canonical, digest, org_number, utcnow, validate_envelopes
from signalpost.research import Profile, financials, identity_gate, official, registry, website, website_candidates
from signalpost.store import Store
from signalpost.viewer import esc, profile_html

ORG = "923609016"
OTHER = "914778271"
ENTITY = {"organisasjonsnummer": ORG, "navn": "SYNTHETIC EXAMPLE AS", "organisasjonsform": {"kode": "AS"}, "antallAnsatte": 7, "aktivitet": ["Synthetic test services only"], "hjemmeside": "https://synthetic-example.no"}


def synth_org(i):
    base = f"{90000000+i:08d}"
    check = 11 - sum(int(a)*b for a,b in zip(base,(3,2,7,6,5,4,3,2))) % 11
    if check == 11: check = 0
    return base+str(check) if check < 10 else synth_org(i+200000)


def response(store, body, url="https://data.brreg.no/synthetic", source="official_registry"):
    data = canonical(body).encode()
    from signalpost.http import Result
    s = store.snapshot({"source_url": url, "final_url": url, "source_class": source, "retrieved_at": utcnow(), "http_status": 200, "content_type": "application/json"}, data)
    return Result(s, data)


@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path / "state")
    yield s
    s.close()


@pytest.mark.parametrize("value", [ORG, "923 609 016", "NO923609016MVA", "923.609.016"])
def test_org_accept(value):
    assert org_number(value) == ORG


@pytest.mark.parametrize("value", ["000000000", "923609017", "9236090160", "abc923609016", "９２３６０９０１６", "923-609-016", None])
def test_org_reject(value):
    with pytest.raises(ValueError): org_number(value)


def test_identity_wrong_company_same_name():
    assert identity_gate(ORG,"SYNTHETIC EXAMPLE AS",f"SYNTHETIC EXAMPLE AS Org {OTHER}")["state"] == "ambiguous"


def test_identity_name_only_insufficient():
    assert identity_gate(ORG,"SYNTHETIC EXAMPLE AS","SYNTHETIC EXAMPLE AS contact us")["state"] == "ambiguous"


def test_identity_parent_brand_conflict():
    assert identity_gate(ORG,"SYNTHETIC EXAMPLE AS",f"SYNTHETIC EXAMPLE AS {ORG} parent {OTHER}")["state"] == "ambiguous"


def test_identity_number_must_be_distinct_token():
    assert identity_gate(ORG,"SYNTHETIC EXAMPLE AS",f"SYNTHETIC EXAMPLE AS 1{ORG}0")["state"] == "ambiguous"
    assert identity_gate(ORG,"SYNTHETIC EXAMPLE AS",f"SYNTHETIC EXAMPLE AS NO 923 609 016 MVA")["state"] == "available"


def test_evidence_value_binding(store):
    p=Profile(ORG,"test",utcnow()); p.registry(response(store,ENTITY))
    row=p.finalize()
    assert validate_envelopes([row])["passed"]
    changed=copy.deepcopy(row)
    changed["claims"][0]["value"]="fabricated"
    assert not validate_envelopes([changed])["passed"]
    with pytest.raises(ValueError): p.ev(response(store,ENTITY),"/navn","wrong name")


def test_foreign_evidence_rejected(store):
    p=Profile(ORG,"test",utcnow()); p.registry(response(store,ENTITY)); row=p.finalize()
    row["evidence"][0]["organisation_number"]=OTHER
    assert not validate_envelopes([row])["passed"]


def test_registry_wrong_number_blocked(store):
    p=Profile(ORG,"test",utcnow())
    with pytest.raises(FetchError,match="identifier"): p.registry(response(store,{**ENTITY,"organisasjonsnummer":OTHER}))


async def test_subunit_never_inherits_parent_accounts(store):
    p=Profile(ORG,"test",utcnow()); p.registry(response(store,{**ENTITY,"overordnetEnhet":OTHER}))
    assert p.claims["entity_kind"]["value"]=="subunit"
    assert p.claims["parent_entity"]["value"]==OTHER
    f=SimpleNamespace(get=AsyncMock())
    await official(p,f,"financials")
    f.get.assert_not_called()
    assert p.modules["financials"]["availability"]=="not_applicable"


def account_body(scope="SELSKAP", currency="NOK", scale=1):
    return [{"id":42,"journalnr":"synthetic","virksomhet":{"organisasjonsnummer":ORG},"regnskapstype":scope,"valuta":currency,"scale":scale,
             "regnskapsperiode":{"fraDato":"2025-01-01","tilDato":"2025-12-31"},"resultatregnskapResultat":{"driftsresultat":{"driftsinntekter":{"sumDriftsinntekter":1234567.89}}}}]


def test_finance_exact_amount_period_currency_scope(store):
    p=Profile(ORG,"test",utcnow()); financials(p,response(store,account_body()))
    c=next(c for c in p.claims.values() if c["field"]=="financial.revenue")
    assert c["value"]["amount"]=="1234567.89"
    assert c["value"]["scale"]==1 and c["value"]["currency"]=="NOK"
    assert c["value"]["scope"]=="company" and c["reporting_period"]["tilDato"]=="2025-12-31"


def test_finance_company_group_separate(store):
    p=Profile(ORG,"test",utcnow()); financials(p,response(store,account_body()+account_body("KONSERN")))
    available=[c for c in p.claims.values() if c['availability']=='available']
    assert {c["value"]["scope"] for c in available}=={"company","group"}
    assert len(available)==2


@pytest.mark.parametrize("scope,currency,scale",[("unknown","NOK",1),("SELSKAP",None,1),("SELSKAP","NOK",1000)])
def test_finance_unknown_dimensions_quarantine(store,scope,currency,scale):
    p=Profile(ORG,"test",utcnow()); financials(p,response(store,account_body(scope,currency,scale)))
    assert not any(c["availability"]=="available" for c in p.claims.values())


def test_finance_foreign_company_and_missing_not_zero(store):
    p=Profile(ORG,"test",utcnow()); body=account_body(); body[0]["virksomhet"]["organisasjonsnummer"]=OTHER
    with pytest.raises(FetchError): financials(p,response(store,body))
    financials(p,response(store,[]))
    assert not p.claims


@pytest.mark.parametrize("url",["http://127.0.0.1","http://[::1]/","http://10.0.0.1","http://169.254.169.254/latest/meta-data","file:///etc/passwd","ftp://example.no","http://user:pass@example.no","https://example.no:8080","https://metadata.google.internal","https://foo.local","https://linkedin.com/test","https://x.com","https://example.no\\@127.0.0.1","https://example.no\nInjected: hi"])
def test_unsafe_url(url):
    with pytest.raises(FetchError): safe_url(url)


def test_safe_public_url():
    assert safe_url("https://example.no/a?q=1#fragment")=="https://example.no/a?q=1"


async def test_dns_mixed_private_rejected(monkeypatch):
    loop=asyncio.get_running_loop()
    monkeypatch.setattr(loop,"getaddrinfo",AsyncMock(return_value=[(None,None,None,None,("8.8.8.8",443)),(None,None,None,None,("127.0.0.1",443))]))
    with pytest.raises(FetchError): await resolve_public("example.no",443)


async def test_connection_is_pinned(monkeypatch):
    import signalpost.http as mod
    monkeypatch.setattr(mod,"resolve_public",AsyncMock(return_value=["8.8.8.8"]))
    backend=PinnedBackend(); backend.inner=SimpleNamespace(connect_tcp=AsyncMock(return_value="stream"))
    assert await backend.connect_tcp("example.no",443)=="stream"
    assert backend.inner.connect_tcp.call_args.args[0]=="8.8.8.8"


async def test_redirect_private_blocked_and_counted(store):
    f=Fetcher(store,Budget(10,10),transport=httpx.MockTransport(lambda r:httpx.Response(302,headers={"location":"http://127.0.0.1/"})))
    with pytest.raises(FetchError): await f.get("https://example.no/", "synthetic",robots=False)
    assert f.budget.requests==1
    await f.close()


@pytest.mark.parametrize("status,state",[(403,"blocked"),(429,"blocked"),(451,"blocked"),(500,"failed")])
async def test_source_error_states(store,status,state):
    f=Fetcher(store,Budget(10,10),transport=httpx.MockTransport(lambda r:httpx.Response(status)))
    with pytest.raises(FetchError) as exc: await f.get("https://example.no/", "synthetic",robots=False)
    assert exc.value.state==state
    await f.close()


async def test_robots_disallow_counts_robot_only(store):
    f=Fetcher(store,Budget(10,10),transport=httpx.MockTransport(lambda r:httpx.Response(200,text="User-agent: *\nDisallow: /")))
    with pytest.raises(FetchError,match="Robots"): await f.get("https://example.no/", "synthetic")
    assert f.budget.requests==1
    await f.close()


async def test_retry_shared_counter(store):
    calls=[]
    def handle(r):
        calls.append(r.url)
        return httpx.Response(503 if len(calls)==1 else 200,json={"synthetic":True})
    f=Fetcher(store,Budget(3,10),transport=httpx.MockTransport(handle))
    await f.get("https://data.brreg.no/synthetic", "synthetic",robots=False)
    assert f.budget.requests==2
    await f.close()


async def test_timeout_bounded_and_counted(store):
    async def handle(r): raise httpx.ReadTimeout("synthetic timeout")
    f=Fetcher(store,Budget(2,10),transport=httpx.MockTransport(handle))
    with pytest.raises(FetchError): await f.get("https://data.brreg.no/synthetic", "synthetic",robots=False)
    assert f.budget.requests==2
    await f.close()


async def test_response_size_bound(store):
    f=Fetcher(store,Budget(1,10),transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'x'*100)))
    with pytest.raises(FetchError): await f.get("https://example.no/", "synthetic",robots=False,limit=20)
    assert f.budget.requests==1
    await f.close()


async def test_conditional_refresh_304_is_live_request(store):
    calls=[]
    def handle(r):
        calls.append(r)
        return httpx.Response(304) if r.headers.get("if-none-match")=="synthetic-v1" else httpx.Response(200,content=b'synthetic',headers={"etag":"synthetic-v1"})
    f=Fetcher(store,Budget(5,10),transport=httpx.MockTransport(handle))
    a=await f.get("https://data.brreg.no/synthetic", "synthetic",robots=False)
    budget=f.budget
    await f.close()
    # A refresh is a new run/fetcher; same-run URL sharing is separately tested.
    f=Fetcher(store,budget,transport=httpx.MockTransport(handle))
    b=await f.get("https://data.brreg.no/synthetic", "synthetic",robots=False)
    assert a.data==b.data and b.snapshot["revalidated"] and f.budget.requests==2 and f.budget.cache_hits==1
    await f.close()


def test_budget_request_and_time_caps():
    b=Budget(1,10); b.take("synthetic")
    with pytest.raises(FetchError): b.take("synthetic")
    assert b.requests==1
    b.deadline=time.monotonic()-1
    with pytest.raises(FetchError): b.check()


async def test_company_allocation_cap(store):
    b=Budget(10,10); f=Fetcher(store,b,transport=httpx.MockTransport(lambda r:httpx.Response(200)))
    token=REQUEST_SCOPE.set({"org":ORG,"allowance":1,"used":0})
    try:
        await f.get("https://data.brreg.no/synthetic", "synthetic",robots=False)
        with pytest.raises(FetchError): await f.get("https://data.brreg.no/synthetic2", "synthetic",robots=False)
        assert b.requests==1
    finally: REQUEST_SCOPE.reset(token); await f.close()


def test_unchanged_refresh_and_changed_history(store):
    for run,employees in [("first",7),("same",7),("changed",8)]:
        p=Profile(ORG,run,utcnow()); p.registry(response(store,{**ENTITY,"antallAnsatte":employees})); prior=store.load(ORG)
        row=store.save(p.finalize(prior),"test")
        if run=="same": assert row["changes"]==[]
        if run=="changed": assert [c["field"] for c in row["changes"]]==["employees"]
        if run=='changed':
            assert set(row['changes'][0]['previous']['evidence_ids']) <= {e['id'] for e in row['evidence']}
    assert store.db.execute("SELECT count(*) FROM history").fetchone()[0]==3
    assert store.db.execute("SELECT count(*) FROM observations WHERE claim_id='employees'").fetchone()[0]==2


def test_blocked_refresh_keeps_stale_without_false_freshness(store):
    p=Profile(ORG,"before",utcnow()); p.registry(response(store,ENTITY)); prior=store.save(p.finalize(),"test")
    p=Profile(ORG,"blocked",utcnow()); p.mark("registry","blocked","synthetic refusal")
    row=store.save(p.finalize(prior),"test")
    name=next(c for c in row["claims"] if c["field"]=="legal_name")
    assert name["stale"] and row["availability"]=="blocked"
    assert name["last_checked"]==next(c for c in prior["claims"] if c["field"]=="legal_name")["last_checked"]
    assert not row["changes"]


def test_duplicate_inputs_rejected(tmp_path):
    p=tmp_path/'input.jsonl'; p.write_text(json.dumps({"organisation_number":ORG})+'\n'+json.dumps({"organisation_number":"923 609 016"}))
    with pytest.raises(ValueError,match="Duplicate"): read_inputs(p)


def test_invalid_identifier_is_individual_outcome(tmp_path):
    p=tmp_path/'input.json'; p.write_text(json.dumps([ORG,"invalid",OTHER]))
    records=read_inputs(p)
    assert len(records)==3 and records[1]["input_error"] and not records[0]["input_error"]


def batch_args(tmp_path,orgs,**overrides):
    input_path=tmp_path/'input.jsonl'; input_path.write_text('\n'.join(json.dumps({"organisation_number":o,"id":i}) for i,o in enumerate(orgs)))
    args=parser().parse_args(["batch","--organisations",str(input_path),"--output",str(tmp_path/'output.jsonl'),"--report",str(tmp_path/'report.json'),"--state",str(tmp_path/'state'),"--run-id","synthetic-test","--modules","registry","--max-requests","2000","--max-seconds","30"])
    for k,v in overrides.items(): setattr(args,k,v)
    return args


async def test_full_output_order_variable_batch_and_failure_isolation(tmp_path):
    orgs=[synth_org(i) for i in range(105)]
    orgs[50]="invalid"
    def handle(r):
        org=r.url.path.rsplit('/',1)[-1]
        return httpx.Response(200,json={**ENTITY,"organisasjonsnummer":org})
    args=batch_args(tmp_path,orgs,max_seconds=60)
    # Per-host delay is tested elsewhere; avoid 26 seconds of synthetic waiting.
    import signalpost.http as h
    original=h.Fetcher._request
    async def quick(self,*a,**kw):
        self.next_time['data.brreg.no']=0
        return await original(self,*a,**kw)
    from unittest.mock import patch
    with patch.object(h.Fetcher,'_request',quick):
        assert await run_batch(args,transport=httpx.MockTransport(handle))==0
    rows=[json.loads(l) for l in Path(args.output).read_text(encoding='utf-8').splitlines()]
    assert [r['organisation_number'] for r in rows]==orgs
    assert len(rows)==105 and rows[50]['availability']=='failed' and rows[104]['availability']=='available'
    assert validate_envelopes(rows,read_inputs(args.organisations))['passed']


async def test_deadline_emits_every_remaining_input(tmp_path):
    args=batch_args(tmp_path,[ORG,OTHER],max_seconds=.02)
    async def slow(r): await asyncio.sleep(1); return httpx.Response(200,json=ENTITY)
    assert await run_batch(args,transport=httpx.MockTransport(slow))==0
    rows=[json.loads(l) for l in Path(args.output).read_text().splitlines()]
    assert len(rows)==2 and all(r['run']['terminal_status']=='completed' for r in rows)


async def test_checkpoint_resume_no_duplicate_output_or_requests(tmp_path):
    args=batch_args(tmp_path,[ORG])
    transport=httpx.MockTransport(lambda r:httpx.Response(200,json=ENTITY))
    assert await run_batch(args,transport=transport)==0
    args.resume=True
    def forbidden(r): raise AssertionError('Completed checkpoints must not fetch')
    assert await run_batch(args,transport=httpx.MockTransport(forbidden))==0
    report=json.loads(Path(args.report).read_text())
    assert report['resumed_profiles']==1 and report['operations']['requests_this_invocation']==0 and report['operations']['requests']==1
    assert len(Path(args.output).read_text().splitlines())==1


async def test_new_run_id_rechecks_live_sources(tmp_path):
    args=batch_args(tmp_path,[ORG]); calls=[]
    def handle(r): calls.append(r); return httpx.Response(200,json=ENTITY)
    await run_batch(args,transport=httpx.MockTransport(handle)); args.run_id='refresh-new'
    await run_batch(args,transport=httpx.MockTransport(handle))
    assert len(calls)==2


def test_cli_bad_input_exit_code_2(tmp_path,capsys):
    p=tmp_path/'bad.json'; p.write_text('invalid json')
    assert main(['batch','--input',str(p),'--output',str(tmp_path/'out'),'--report',str(tmp_path/'report'),'--state',str(tmp_path/'state'),'--run-id','test'])==2
    assert capsys.readouterr().out==''


def test_viewer_escapes_external_content(store):
    p=Profile(ORG,'test',utcnow()); p.registry(response(store,{**ENTITY,'navn':'<script>alert(1)</script>'})); row=p.finalize()
    rendered=profile_html(row,[])
    assert '<script>alert(1)</script>' not in rendered and '&lt;script&gt;' in rendered


def test_discovery_beyond_registry_url():
    c=website_candidates({'navn':'SYNTHETIC EXAMPLE AS','epostadresse':'office@synthetic-domain.no'})
    assert c[0]['method']=='registry_business_email_domain'
    c=website_candidates({'navn':'SYNTHETIC EXAMPLE AS'})
    assert c == []  # No domain guessing: only actual public source identifiers.


def test_bulk_preserves_original_and_hash(store,tmp_path):
    path=tmp_path/'bulk.csv'; path.write_text('organisasjonsnummer,navn,antallAnsatte\n'+ORG+',SYNTHETIC EXAMPLE AS,7\n')
    result=load_bulk(path,{ORG},store,Budget(1,10))[ORG]
    assert result.json()['antallAnsatte']==7
    assert result.json()['_source_csv_row']['antallAnsatte']=='7'
    assert result.snapshot['parent_bulk_sha256']==digest(path.read_bytes())


async def test_resume_cannot_reset_request_budget(tmp_path):
    args=batch_args(tmp_path,[ORG],max_requests=1)
    await run_batch(args,transport=httpx.MockTransport(lambda r:httpx.Response(200,json=ENTITY)))
    # Simulate interruption before final checkpoint: network reservation remains durable.
    db=sqlite3.connect(Path(args.state)/'signalpost.sqlite'); db.execute('DELETE FROM checkpoints'); db.commit(); db.close()
    args.resume=True
    def forbidden(r): raise AssertionError('Resume cannot reset budget')
    await run_batch(args,transport=httpx.MockTransport(forbidden))
    report=json.loads(Path(args.report).read_text())
    assert report['operations']['requests']==1 and report['operations']['requests_this_invocation']==0


async def test_resume_mismatched_configuration_rejected(tmp_path):
    args=batch_args(tmp_path,[ORG])
    await run_batch(args,transport=httpx.MockTransport(lambda r:httpx.Response(200,json=ENTITY)))
    args.resume=True; args.max_requests=100
    with pytest.raises(ValueError,match='configuration'): await run_batch(args,transport=httpx.MockTransport(lambda r:httpx.Response(200)))


async def test_brreg_410_legal_removal_not_failed_refresh(store):
    p=Profile(ORG,'before',utcnow()); p.registry(response(store,ENTITY)); store.save(p.finalize(),'test')
    p=Profile(ORG,'removed',utcnow())
    f=Fetcher(store,Budget(5,10),transport=httpx.MockTransport(lambda r:httpx.Response(410)))
    await registry(p,f)
    assert p.entity['_legal_removal'] and store.load(ORG) is None
    assert store.db.execute('SELECT count(*) FROM history WHERE org=?',(ORG,)).fetchone()[0]==0
    await f.close()
