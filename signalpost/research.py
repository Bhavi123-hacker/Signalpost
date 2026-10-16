from __future__ import annotations

import json
import html
import re
import time
import unicodedata
from decimal import Decimal
from datetime import date
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from .http import FetchError, Fetcher, Result, safe_url
from .models import Claim, Evidence, MODULE_STATE, canonical, digest, org_number, utcnow
from .site_extract import extra_site_facts,expanded_site_facts,business_description_page,company_contact_context,contact_is_new,contact_normal,reject_contact,add_structured,iso_date,job_record

BASE = "https://data.brreg.no/enhetsregisteret/api"
MODULES = ("registry", "financials", "roles", "locations", "group", "website", "hiring", "activity", "public_brand", "company_owned_profiles")


def pointer(value, path: str):
    for token in path.strip("/").split("/") if path else []:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def identity_gate(org: str, legal_name: str, text: str) -> dict:
    # Only separated 9-digit tokens, never a substring assembled across all page digits.
    candidates = set()
    for match in re.finditer(r"(?<!\d)(\d{3}[ .\u00a0]?\d{3}[ .\u00a0]?\d{3})(?!\d)", text):
        try:
            candidates.add(org_number(match.group(1)))
        except ValueError:
            pass
    if candidates - {org}:
        return {"state": "ambiguous", "reason": "Conflicting organisation numbers on page", "observed_numbers": sorted(candidates)}
    normalize=lambda s: re.sub(r'[^\w]+',' ',unicodedata.normalize('NFKC',s).casefold()).strip()
    if org in candidates and (' '+normalize(legal_name)+' ') in (' '+normalize(text)+' '):
        return {"state": "available", "reason": "Exact legal name and organisation number in collected page", "observed_numbers": [org]}
    return {"state": "ambiguous", "reason": "Exact legal name and organisation number not both established", "observed_numbers": sorted(candidates)}


def website_candidates(entity: dict) -> list[dict]:
    values = []
    listed = entity.get("hjemmeside")
    if listed:
        values.append({"url": listed if "://" in listed else "https://" + listed, "method": "registry_listed", "status": "candidate"})
    email = entity.get("epostadresse") or ""
    if "@" in email:
        domain = email.rsplit("@", 1)[1].strip().lower()
        if domain not in {"gmail.com", "hotmail.com", "hotmail.no", "outlook.com", "yahoo.com", "yahoo.no", "online.no", "live.no", "live.com", "icloud.com", "c2i.net", "netcom.no", "start.no", "broadpark.no"}:
            values.append({"url": "https://" + domain, "method": "registry_business_email_domain", "status": "candidate"})
    # Reproducible zero-fee discovery, not a claim: at most one legal-name domain hypothesis.
    if not values:
        name = re.sub(r"\s+(?:AS|ASA|ANS|DA|SA|NUF)$", "", entity.get("navn", ""), flags=re.I)
        name = name.translate(str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "å": "a", "Å": "a"}))
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^a-z0-9]", "", name.casefold())
        if 4 <= len(slug) <= 45:
            values.append({"url": "https://" + slug + ".no", "method": "legal_name_domain_hypothesis", "status": "candidate"})
    return list({v["url"].lower().rstrip("/"): v for v in values}.values())[:2]


class Profile:
    def __init__(self, org: str, run_id: str, started_at: str, input_id=None):
        self.org, self.run_id, self.started_at, self.input_id = org, run_id, started_at, input_id
        self.claims, self.evidence, self.snapshots, self.errors, self.candidates = {}, {}, {}, [], []
        self.modules = {m: {"availability": "failed", "explanation": "Not checked: resource allocation or module disabled", "retry_count": 0} for m in MODULES}
        self.entity = {}
        self.verified_urls = set()
        self.contact_rejections={}
        self.retractions={}
        self.website_homepage=None
        self.started = time.monotonic()
        self.request_start = 0

    def mark(self, module, state, explanation):
        self.modules[module] = {"availability": state, "state": MODULE_STATE[state], "explanation": explanation, "final_timestamp": utcnow(), "retry_count": 0}
        if state == "available":
            self.claims.pop(module, None)

    def ev(self, result: Result, path: str | None, value=None, span=None) -> str:
        s = result.snapshot
        self.snapshots[s["id"]] = s
        if span is None:
            actual = pointer(result.json(), path or "")
            if value is not None and canonical(actual) != canonical(value):
                raise ValueError("Extractor attempted to bind evidence to a different source value")
            span = canonical(actual)[:700]
        elif span not in html.unescape(result.data.decode("utf-8", "replace")) and span not in page_text(result.data)[1]:
            raise ValueError("Excerpt does not occur in collected source")
        if path is not None:
            path = result.root_path + path
        eid = "ev-" + digest(canonical([self.org, s["source_url"], s["content_sha256"], path, span]).encode())[:24]
        self.evidence[eid] = Evidence(id=eid, organisation_number=self.org, source_url=s["source_url"], final_url=s["final_url"],
            source_class="company_owned" if s["final_url"] in self.verified_urls else s["source_class"], source_identifier=s["final_url"] + ("#" + path if path else ""), retrieved_at=s["retrieved_at"],
            content_sha256=s["content_sha256"], storage_ref=s["storage_ref"], claim_span=span, json_path=path).model_dump()
        return eid

    def add(self, field, value, eid, *, key=None, effective=None, period=None, explanation=""):
        key = key or field
        checked = self.evidence[eid]["retrieved_at"]
        self.claims[key] = Claim(id=key, field=field, value=value, availability="available", evidence_ids=[eid], explanation=explanation,
                                 effective_at=effective, reporting_period=period, last_checked=checked).model_dump()
        self.evidence[eid]["claim_bindings"][key] = digest(canonical(value).encode())
        self.evidence[eid]["effective_at"] = effective

    def unknown(self, field, state, explanation, *, key=None, evidence_ids=None):
        key = key or field
        self.claims[key] = Claim(id=key, field=field, availability=state, explanation=explanation, evidence_ids=evidence_ids or [], last_checked=utcnow()).model_dump()

    def failure(self, module, exc):
        self.mark(module, exc.state, str(exc))
        error = {"module": module, "state": exc.state, "message": str(exc)}
        if exc.snapshot:
            s = exc.snapshot
            self.snapshots[s["id"]] = s
            error["source_url"] = s["source_url"]
            error["snapshot_id"] = s["id"]
        self.errors.append(error)

    def registry(self, result: Result):
        body = result.json()
        if not isinstance(body, dict) or body.get("organisasjonsnummer") != self.org:
            raise FetchError("ambiguous", "Registry response identifier does not match requested company")
        self.entity = body
        kind = "subunit" if body.get("overordnetEnhet") or body.get("respons_klasse") == "Underenhet" else "legal_entity"
        if kind=='legal_entity' and body.get('organisasjonsform',{}).get('kode')=='NUF':kind='registered_foreign_enterprise'
        fields = {"legal_name": "navn", "legal_form": "organisasjonsform", "business_address": "beliggenhetsadresse" if kind == "subunit" else "forretningsadresse",
                  "postal_address": "postadresse", "industry": "naeringskode1", "employees": "antallAnsatte", "founded": "stiftelsesdato",
                  "registered": "registreringsdatoEnhetsregisteret", "deleted_at": "slettedato", "bankrupt": "konkurs", "liquidating": "underAvvikling",
                  "business_phone": "telefon", "business_email": "epostadresse", "registered_activity": "aktivitet",
                  "registered_purpose": "vedtektsfestetFormaal", "latest_filing_year": "sisteInnsendteAarsregnskap", "parent_entity": "overordnetEnhet"}
        e = self.ev(result, "/organisasjonsnummer", self.org)
        self.add("organisation_number", self.org, e)
        self.add("entity_kind", kind, e, explanation="Derived from official endpoint, legal form and overordnetEnhet; NUF registration is not a separate Norwegian incorporated company")
        if kind=='registered_foreign_enterprise':self.claims['entity_kind']['evidence_ids'].append(self.ev(result,'/organisasjonsform'))
        for field, source in fields.items():
            value = body.get(source)
            if field == "employees" and body.get("harRegistrertAntallAnsatte") is False:
                self.unknown(field, "not_available", "Registry explicitly does not provide a registered employee count", evidence_ids=[self.ev(result, "/harRegistrertAntallAnsatte", False)])
                continue
            if value is not None and value != "" and value != []:
                eid = self.ev(result, "/" + source, value)
                effective = body.get("registreringsdatoAntallAnsatteEnhetsregisteret") if field == "employees" else None
                self.add(field, value, eid, effective=effective,
                         explanation="Self-reported registered activity; not an industry-code description" if field == "registered_activity" else "")
            elif field == "deleted_at":
                continue
            elif field == "parent_entity" and kind == "legal_entity":
                # No inference of a group parent from lack of a subunit parent.
                continue
            else:
                self.unknown(field, "not_available", "Field absent from returned official record", evidence_ids=[e])
        self.mark("registry", "available", "Exact organisation number anchored in official registry")

    def finalize(self, previous=None) -> dict:
        # Preserve last-known claims when a new check fails; never mark them current.
        if previous:
            prior_evidence = {e["id"]: e for e in previous["evidence"]}
            field_modules = {"legal_name": "registry", "employees": "registry", "organisation_number": "registry", "entity_kind": "registry", "legal_form": "registry",
                "business_address": "registry", "postal_address": "registry", "industry": "registry", "founded": "registry", "registered": "registry", "bankrupt": "registry", "liquidating": "registry",
                "business_phone": "registry", "business_email": "registry", "registered_activity": "registry", "registered_purpose": "registry", "latest_filing_year": "registry", "parent_entity": "registry",
                "leadership_role": "roles", "registered_workplace": "locations", "official_group_structure": "group", "official_website": "website", "website_description": "website", "website_email": "website", "website_phone": "website"}
            for old in previous["claims"]:
                current = self.claims.get(old["id"])
                retraction=self.retractions.get(old['id'])
                if old['field'] in {'website_phone','website_email'}:
                    eid=self.contact_rejections.get((old['field'],contact_normal(old['field'],str(old.get('value','')))))
                    if eid:retraction=(eid,'Previously published contact was quoted in a third-party/group/installer or malformed-contact context; exact-company attribution withheld')
                if old['availability']=='available' and retraction and (not current or current['availability']!='available'):
                    eid,reason=retraction
                    self.unknown(old['field'],'ambiguous','Retracted: '+reason,key=old['id'],evidence_ids=[eid])
                    self.claims[old['id']]['retracted']=True
                    continue
                if old["availability"] == "available" and (current is None or current["availability"] in {"blocked", "failed", "ambiguous"}):
                    module = "financials" if old["field"].startswith("financial.") else field_modules.get(old["field"])
                    # Only complete official collections justify removal. Website absence
                    # and bounded jobs/news crawls cannot prove a prior fact was removed.
                    if current is None and module in {"roles", "locations", "group"} and self.modules[module]["availability"] in {"available", "not_available"} and self.modules[module].get("collection_complete"):
                        self.unknown(old["field"], "not_available", "Absent from successfully rechecked complete official collection", key=old["id"], evidence_ids=self.modules[module].get("source_evidence_ids", []))
                        continue
                    item = {**old, "stale": True, "explanation": "Last known evidence retained; current refresh did not verify it. " + (current or {}).get("explanation", "Source/module not checked")}
                    self.claims[old["id"]] = item
                    for eid in old["evidence_ids"]:
                        self.evidence[eid] = prior_evidence[eid]
                    prior_refs = {prior_evidence[eid]["content_sha256"] for eid in old["evidence_ids"]}
                    for snapshot in previous.get("source_snapshots", []):
                        if snapshot["content_sha256"] in prior_refs:
                            self.snapshots[snapshot["id"]] = snapshot
        for module in MODULES:
            record = self.modules[module]
            record.setdefault("state", MODULE_STATE[record["availability"]])
            record.setdefault("final_timestamp", utcnow())
            if not any(c["field"] == module or (module == "financials" and c["field"].startswith("financial.")) for c in self.claims.values()) and record["availability"] != "available":
                self.unknown(module, record["availability"], record["explanation"], evidence_ids=record.get("source_evidence_ids", []))
        current_identity = self.modules["registry"]["availability"] == "available"
        availability = "available" if current_identity else self.modules["registry"]["availability"]
        done = utcnow()
        name = next((c["value"] for c in self.claims.values() if c["field"] == "legal_name" and c["availability"] == "available"), None)
        facts = {c["field"]: c["value"] for c in self.claims.values() if c["availability"] == "available" and not c["stale"] and not c["field"].startswith("financial.")}
        evidence_modules = {k: {"status": v["availability"], "note": v["explanation"], "retrieved_at": v["final_timestamp"]} for k, v in self.modules.items()}
        summary = {"legal_name": name, "organisation_number": self.org, "current_fact_count": sum(c["availability"] == "available" and not c["stale"] for c in self.claims.values()),
                   "business_description_claim_ids": [c["id"] for c in self.claims.values() if c["availability"] == "available" and not c['stale'] and c["field"] in {"registered_activity", "website_description"}],
                   "unknowns": [{"field": k, "state": v["availability"], "reason": v["explanation"]} for k, v in self.modules.items() if v["availability"] != "available"],
                   "note": "Company self-descriptions are attributed, not independently endorsed. Financial scope and period are explicit in each observation."}
        return {"schema_version": "signalpost-1.0", "organisation_number": self.org, "input_id": self.input_id,
                "run_id": self.run_id, "state": "complete" if current_identity else MODULE_STATE[availability], "availability": availability,
                "started_at": self.started_at, "completed_at": done,
                "run": {"run_id": self.run_id, "started_at": self.started_at, "completed_at": done, "terminal_status": "completed"},
                "legal_identity": {"organisation_number": self.org, "legal_name": name, "status": self.modules["registry"]["availability"]},
                "modules": self.modules, "claims": list(self.claims.values()), "evidence": list(self.evidence.values()), "source_snapshots": list(self.snapshots.values()),
                "profile": {"organisation_number": self.org, "name": name, **facts, "evidence": evidence_modules}, "summary": summary,
                "website_candidates": self.candidates, "changes": [], "errors": self.errors,
                "refresh": {"checked_at": done, "previous_run_id": (previous or {}).get("run_id"), "freshness_policy": {"registry_hours": 24, "accounts_days": 30, "website_hours": 24, "hiring_hours": 6},
                            "mode": "recheck_sources", "stale_claims": sum(c["stale"] for c in self.claims.values())},
                "operations": {"runtime_ms": round((time.monotonic() - self.started) * 1000), "third_party_cost_usd": 0}}


async def registry(profile: Profile, fetcher: Fetcher, bulk_result=None):
    if bulk_result:
        profile.registry(bulk_result)
        return
    # These documented open machine APIs explicitly permit automated reuse under NLOD.
    # Robots is a company-page crawler gate, not a prerequisite for this API contract.
    result = await fetcher.get(f"{BASE}/enheter/{profile.org}", "official_registry", robots=False)
    if result.snapshot["http_status"] == 410:
        fetcher.store.legal_removal(profile.org)
        profile.entity["_legal_removal"] = True
        profile.mark("registry", "not_available", "BRREG 410 legal removal: prior company cache/history purged; no parent fallback")
        return
    if result.snapshot["http_status"] == 404:
        result = await fetcher.get(f"{BASE}/underenheter/{profile.org}", "official_subunit", robots=False)
    if result.snapshot["http_status"] == 410:
        fetcher.store.legal_removal(profile.org)
        profile.entity["_legal_removal"] = True
        profile.mark("registry", "not_available", "BRREG 410 legal removal: prior company cache/history purged")
        return
    if result.snapshot["http_status"] in {404, 410}:
        profile.mark("registry", "not_available", "No entity or subunit returned by official endpoints")
        source = profile.ev(result, None, span="")
        profile.modules["registry"]["source_evidence_ids"] = [source]
        profile.unknown("organisation_number", "not_available", "No official identity returned", evidence_ids=[source])
        return
    profile.registry(result)


FINANCIAL_PATHS = {"revenue": "/resultatregnskapResultat/driftsresultat/driftsinntekter/sumDriftsinntekter",
                   "operating_result": "/resultatregnskapResultat/driftsresultat/driftsresultat",
                   "annual_result": "/resultatregnskapResultat/aarsresultat", "assets": "/eiendeler/sumEiendeler",
                   "equity": "/egenkapitalGjeld/egenkapital/sumEgenkapital", "debt": "/egenkapitalGjeld/gjeldOversikt/sumGjeld"}


def financials(profile: Profile, result: Result):
    body = json.loads(result.data, parse_float=Decimal)
    if not isinstance(body, list):
        raise FetchError("failed", "Unexpected accounts response schema")
    count = 0
    for index, record in enumerate(body):
        if record.get("virksomhet", {}).get("organisasjonsnummer") != profile.org:
            raise FetchError("ambiguous", "Accounts response contains another legal entity")
        period = record.get("regnskapsperiode") or {}
        scope = {"SELSKAP": "company", "KONSERN": "group"}.get(record.get("regnskapstype"))
        currency = record.get("valuta")
        if not scope or not currency or not re.fullmatch(r"[A-Z]{3}", currency) or not all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(period.get(k, ""))) for k in ("fraDato", "tilDato")):
            profile.errors.append({"module": "financials", "state": "ambiguous", "message": "Record lacks explicit currency, scope or reporting period"})
            continue
        try:
            if date.fromisoformat(period['fraDato']) > date.fromisoformat(period['tilDato']):
                raise ValueError('Reversed reporting period')
        except ValueError:
            profile.errors.append({'module':'financials','state':'ambiguous','message':'Invalid/reversed reporting dates; record quarantined'})
            continue
        for metric, path in FINANCIAL_PATHS.items():
            key = f"financial.{metric}:{scope}:{period['fraDato']}:{period['tilDato']}:{record.get('id')}"
            try:
                amount = pointer(record, path)
            except (KeyError, TypeError):
                eid = profile.ev(result, f"/{index}/regnskapsperiode")
                profile.unknown("financial." + metric, "not_available", "Metric absent from this exact official account record; missing is not zero", key=key, evidence_ids=[eid])
                profile.claims[key]["reporting_period"] = period
                continue
            if not isinstance(amount, (Decimal, int)) or isinstance(amount, bool) or (isinstance(amount,Decimal) and not amount.is_finite()):
                continue
            # The official normalised endpoint returns absolute currency amounts.
            # Preserve decimals as strings, never multiply or infer missing numbers.
            if record.get("scale", 1) != 1 or record.get("enhet") not in {None,'kroner','hele','1','units'}:
                profile.errors.append({"module": "financials", "state": "ambiguous", "message": "Unexpected financial scale; amount quarantined"})
                continue
            raw_value = pointer(result.json(), f"/{index}{path}")
            eid = profile.ev(result, f"/{index}{path}", raw_value)
            value = {"organisation_number": profile.org, "metric": metric, "amount": str(amount), "currency": currency, "scale": 1,
                     "units": "currency units (normalised official API)", "scope": scope, "period": period,
                     "record_id": record.get("id"), "journal_number": record.get("journalnr"), "source_field": path}
            value['metric_definition']={'revenue':'Total operating income (sumDriftsinntekter), including other operating income; not sales-only revenue','operating_result':'Operating profit/loss','annual_result':'Annual profit/loss','assets':'Total assets','equity':'Total equity','debt':'Total liabilities'}[metric]
            value['reporting_entity_context']='Foreign enterprise filed under Norwegian NUF registration; not evidence of Norwegian branch-only performance' if profile.entity.get('organisasjonsform',{}).get('kode')=='NUF' else 'Exact registered entity; standalone company and consolidated group kept separate'
            profile.add("financial." + metric, value, eid, key=key, effective=period["tilDato"], period=period)
            for source_field in ("virksomhet", "regnskapstype", "regnskapsperiode", "valuta", "id", "journalnr"):
                if source_field in record:
                    profile.claims[key]["evidence_ids"].append(profile.ev(result, f"/{index}/{source_field}"))
            count += 1
    profile.mark("financials", "available" if count else "not_available" if not body else "ambiguous", "Exact-company official accounts; all returned periods/scopes retained" if count else "Endpoint supplied no usable, fully dimensioned financial metrics")
    if not count:
        profile.modules["financials"]["source_evidence_ids"] = [profile.ev(result, None, span="")]


async def official(profile: Profile, fetcher: Fetcher, module: str):
    endpoints = {"financials": f"https://data.brreg.no/regnskapsregisteret/regnskap/{profile.org}",
                 "roles": f"{BASE}/enheter/{profile.org}/roller", "group": f"{BASE}/konsernstruktur/{profile.org}",
                 "locations": f"{BASE}/underenheter?overordnetEnhet={profile.org}&size=100"}
    if profile.entity.get("overordnetEnhet"):
        profile.mark(module, "not_applicable", "Subunit is not a separate legal entity; parent facts are not attached")
        return
    result = await fetcher.get(endpoints[module], "official_annual_accounts" if module == "financials" else "official_" + module, robots=False)
    if result.snapshot["http_status"] in {404, 410}:
        profile.mark(module, "not_available", "Official endpoint returned no record")
        profile.modules[module]["source_evidence_ids"] = [profile.ev(result, None, span="")]
        return
    if module == "financials":
        financials(profile, result)
        return
    body = result.json()
    if not isinstance(body, dict):
        raise FetchError("failed", "Unexpected official module response schema")
    if module == "roles":
        found = 0
        for gi, group in enumerate(body.get("rollegrupper", [])):
            for ri, role in enumerate(group.get("roller", [])):
                if role.get("avregistrert"):
                    continue
                person = role.get("person", {}).get("navn", {})
                name = " ".join(str(person[k]) for k in ("fornavn", "mellomnavn", "etternavn") if person.get(k))
                entity = role.get("enhet", {})
                name = name or entity.get("navn")
                if not name:
                    continue
                # Evidence only exposes role/name fields, never date of birth/address.
                path = f"/rollegrupper/{gi}/roller/{ri}"
                eid = profile.ev(result, path + ("/person/navn" if person else "/enhet/navn"), person if person else name)
                value = {"name": name, "role": role.get("type"), "role_group": group.get("type"), "last_changed": group.get("sistEndret"),
                         "role_holder_organisation_number": entity.get("organisasjonsnummer")}
                key = "role:" + digest(canonical([name, role.get("type")]).encode())[:16]
                profile.add("leadership_role", value, eid, key=key, effective=group.get("sistEndret"))
                for extra_path in (path + "/type", f"/rollegrupper/{gi}/type", f"/rollegrupper/{gi}/sistEndret"):
                    try:
                        extra_eid = profile.ev(result, extra_path)
                        profile.claims[key]["evidence_ids"].append(extra_eid)
                    except KeyError:
                        pass
                found += 1
    elif module == "locations":
        rows = body.get("_embedded", {}).get("underenheter", [])
        found = 0
        for i, sub in enumerate(rows):
            if sub.get("overordnetEnhet") != profile.org:
                raise FetchError("ambiguous", "Subunit parent mismatch")
            value = {k: sub.get(k) for k in ("organisasjonsnummer", "overordnetEnhet", "navn", "beliggenhetsadresse", "antallAnsatte")}
            eid = profile.ev(result, f"/_embedded/underenheter/{i}/organisasjonsnummer", sub["organisasjonsnummer"])
            profile.add("registered_workplace", value, eid, key="workplace:" + sub["organisasjonsnummer"])
            for source_field in ("overordnetEnhet", "navn", "beliggenhetsadresse", "antallAnsatte"):
                if sub.get(source_field) is not None:
                    profile.claims["workplace:" + sub["organisasjonsnummer"]]["evidence_ids"].append(profile.ev(result, f"/_embedded/underenheter/{i}/{source_field}", sub[source_field]))
            found += 1
        if body.get("page", {}).get("totalPages", 1) > 1:
            profile.errors.append({"module": module, "state": "failed", "message": "First 100 workplaces only; pagination not completed under bounded allocation"})
    else:
        found = bool(body)
        if found:
            eid = profile.ev(result, "", body)
            profile.add("official_group_structure", body, eid, explanation="Official structure as returned; legal entities are not merged")
    profile.mark(module, "available" if found else "not_available", "Collected official records" if found else "Checked endpoint returned no records")
    profile.modules[module]["collection_complete"] = module != "locations" or body.get("page", {}).get("totalPages", 1) <= 1
    profile.modules[module]["source_evidence_ids"] = [profile.ev(result, None, span="")]


def page_text(data: bytes):
    soup = BeautifulSoup(data, "html.parser")
    structured = []
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            structured.append(json.loads(node.get_text()))
        except (ValueError, TypeError):
            pass
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    text = " ".join(soup.stripped_strings)
    return soup, text, structured


def flat_jsonld(value):
    if isinstance(value, list):
        for item in value:
            yield from flat_jsonld(item)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from flat_jsonld(value["@graph"])


def identity_text(result, text, structured):
    # Structured legal identifiers are commonly hidden in script tags. Include
    # exact scalar values only when they occur in the collected source bytes.
    raw=html.unescape(result.data.decode('utf-8','replace'))
    pieces=[text]
    for item in flat_jsonld(structured):
        for key in ('legalName','name','taxID','vatID','identifier'):
            value=item.get(key)
            if isinstance(value,str) and value in raw:
                pieces.append(value)
    return ' '.join(pieces)


def candidate_priority(entity):
    candidates=website_candidates(entity)
    if any(c['method']=='registry_listed' for c in candidates): return 0
    email=next((c for c in candidates if c['method']=='registry_business_email_domain'),None)
    if email:
        parts=(urlsplit(email['url']).hostname or '').split('.')
        domain=parts[-2] if len(parts)>=2 else ''
        name=re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',entity.get('navn','').lower()).encode('ascii','ignore').decode())
        return 1 if len(domain)>=4 and domain in name else 2
    return 3


def scoped_publisher_path(path):
    return bool(re.search(r'/(?:medarbeid(?:ere|arar|er)?|ansatte|staff|team|people|profiles?|members?|companies|bedrifter|customers?|clients?|kunder|portfolio|forhandlere?|dealers?|franchises?)/[^/]+',path,re.I))


def page_family(url):
    path=urlsplit(url).path.casefold()
    if re.search(r'ledig|jobs|career|karriere|stillin',path):return 'jobs'
    if re.search(r'nyhet|news|aktuelt|blog',path):return 'activity'
    if re.search(r'tjenest|service|produkt|product|kurs',path):return 'offering'
    if re.search(r'kontakt|contact',path):return 'contact'
    if re.search(r'om[-_/]|about|ledelse|leadership|avdeling|location',path):return 'about'
    return 'other'


def adaptive_links(profile,links):
    fields={c['field'] for c in profile.claims.values() if c['availability']=='available' and not c['stale']}
    wanted={'about':'website_description' not in fields,'contact':not {'website_email','website_phone'}<=fields,
            'jobs':'job_posting' not in fields,'activity':'dated_activity' not in fields,'offering':'website_service' not in fields,'other':False}
    priorities={'about':0,'offering':1,'contact':2,'jobs':3,'activity':4} if 'website_description' not in fields else {'jobs':0,'activity':1,'offering':2,'contact':3,'about':4}
    return sorted((url for url in links if wanted[page_family(url)]),key=lambda url:priorities.get(page_family(url),5))


async def website(profile: Profile, fetcher: Fetcher, max_pages=3, *, extraction='baseline', page_policy='baseline'):
    profile.candidates = website_candidates(profile.entity)
    if not profile.candidates:
        profile.mark("website", "not_available", "No registry URL, usable business-email domain or domain hypothesis")
        return
    last_state = "ambiguous"
    for candidate in profile.candidates:
        try:
            result = await fetcher.get(candidate["url"], "company_owned_candidate",attempts=1)
            if result.snapshot["http_status"] in {404, 410}:
                candidate.update(status="rejected", reason="HTTP source absent")
                continue
            if "html" not in result.snapshot["content_type"]:
                raise FetchError("ambiguous", "Candidate did not return static HTML")
            soup, text, structured = page_text(result.data)
            profile.snapshots[result.snapshot["id"]] = result.snapshot
            candidate["checks"] = [{k: result.snapshot[k] for k in ("id", "source_url", "final_url", "retrieved_at", "content_sha256", "storage_ref")}]
            # An exact entity mentioned on a staff/directory profile does not
            # establish ownership of the shared publisher's whole website.
            path=urlsplit(result.snapshot['final_url']).path
            if scoped_publisher_path(path):
                candidate.update(status='ambiguous',reason='Scoped staff/directory profile; exact entity mention does not establish site ownership',final_url=result.snapshot['final_url'])
                last_state='ambiguous'
                continue
            gate = identity_gate(profile.org, profile.entity.get("navn", ""), identity_text(result,text,structured))
            candidate.update(status=gate["state"], reason=gate["reason"], final_url=result.snapshot["final_url"], observed_numbers=gate["observed_numbers"])
            pages = [(result, soup, text, structured)]
            # Contact/legal page can prove exact identity when homepage does not.
            if gate["state"] != "available" and not (set(gate["observed_numbers"]) - {profile.org}):
                contact_links = [a for a in soup.select("a[href]") if re.search(r"kontakt|contact|juridisk|legal|impressum|personvern|privacy|om-oss|about", a.get("href", "") + " " + a.get_text(" "), re.I)]
                targets=[]
                for a in contact_links:
                    try: target = safe_url(urljoin(result.snapshot["final_url"], a["href"]))
                    except FetchError: continue
                    if urlsplit(target).hostname != urlsplit(result.snapshot["final_url"]).hostname:
                        continue
                    if target!=result.snapshot['final_url'] and target not in targets: targets.append(target)
                targets.sort(key=lambda u:0 if re.search('kontakt|contact',u,re.I) else 1 if re.search('legal|juridisk|personvern|privacy|impressum',u,re.I) else 2)
                # Only a sitemap explicitly advertised by the fetched robots
                # policy; never spray guessed paths. One bounded XML download.
                if not targets and hasattr(fetcher,'robots'):
                    origin=urlsplit(result.snapshot['final_url'])
                    policy=fetcher.robots.get(f'{origin.scheme}://{origin.netloc}')
                    maps=policy.site_maps() if hasattr(policy,'site_maps') else []
                    for map_url in (maps or [])[:1]:
                        try:
                            map_url=safe_url(map_url)
                            if urlsplit(map_url).hostname!=origin.hostname:continue
                            sitemap=await fetcher.get(map_url,'company_owned_candidate',limit=256_000,attempts=1)
                            if b'<!DOCTYPE' in sitemap.data.upper() or b'<!ENTITY' in sitemap.data.upper():continue
                            xml=ElementTree.fromstring(sitemap.data)
                            for node in list(xml.iter())[:1500]:
                                if node.tag.rsplit('}',1)[-1]=='loc' and node.text and re.search(r'contact|kontakt|legal|privacy|personvern|om-oss|about',node.text,re.I):
                                    target=safe_url(node.text.strip())
                                    if urlsplit(target).hostname==origin.hostname and target not in targets:targets.append(target)
                        except (FetchError,ElementTree.ParseError):pass
                for target in targets[:2]:
                    contact = await fetcher.get(target, "company_owned_candidate",attempts=1)
                    if contact.snapshot["http_status"] not in {200, 304}:
                        continue
                    if urlsplit(contact.snapshot['final_url']).hostname!=urlsplit(result.snapshot['final_url']).hostname:
                        profile.errors.append({'module':'website','state':'ambiguous','message':'Contact/proof redirected off candidate host; not an ownership proof','url':target})
                        continue
                    cs, ct, cj = page_text(contact.data)
                    if scoped_publisher_path(urlsplit(contact.snapshot['final_url']).path):
                        profile.errors.append({'module':'website','state':'ambiguous','message':'Scoped directory/staff/customer page cannot prove ownership of the publisher site','url':target})
                        continue
                    profile.snapshots[contact.snapshot["id"]] = contact.snapshot
                    candidate["checks"].append({k: contact.snapshot[k] for k in ("id", "source_url", "final_url", "retrieved_at", "content_sha256", "storage_ref")})
                    cg = identity_gate(profile.org, profile.entity.get("navn", ""), identity_text(contact,ct,cj))
                    pages.append((contact, cs, ct, cj))
                    gate = cg
                    candidate.update(status=gate["state"], reason=gate["reason"], observed_numbers=gate["observed_numbers"])
                    if gate["state"] == "available":
                        break
            if gate["state"] != "available":
                last_state = "ambiguous"
                continue
            proof = pages[-1]
            profile.verified_urls.update(p[0].snapshot["final_url"] for p in pages)
            # Bind both identity tokens to the saved proof page.
            name_pattern=r'[\W_]+'.join(re.escape(t) for t in re.findall(r'\w+',profile.entity.get('navn','')))
            match=re.search(name_pattern,proof[2],re.I)
            if match:
                name_span=proof[2][max(0,match.start()-25):match.end()+25]
            else:
                values=[str(item.get(key,'')) for item in flat_jsonld(proof[3]) for key in ('legalName','name')]
                normalize=lambda s: re.sub(r'[^\w]+',' ',unicodedata.normalize('NFKC',s).casefold()).strip()
                name_span=next(v for v in values if normalize(v)==normalize(profile.entity.get('navn','')) and v in html.unescape(proof[0].data.decode('utf-8','replace')))
            eid = profile.ev(proof[0], None, span=name_span)
            profile.add("official_website", result.snapshot["final_url"], eid, explanation="Exact legal name and organisation number collected; source URL redirects recorded")
            for number_match in re.finditer(r"(?<!\d)(\d{3}[ .\u00a0]?\d{3}[ .\u00a0]?\d{3})(?!\d)", html.unescape(proof[0].data.decode('utf-8','replace'))):
                if re.sub(r"[ .\u00a0]", "", number_match.group(1)) == profile.org:
                    raw=html.unescape(proof[0].data.decode('utf-8','replace'))
                    profile.claims["official_website"]["evidence_ids"].append(profile.ev(proof[0], None, span=raw[max(0, number_match.start()-35):number_match.end()+35]))
                    break
            if len(profile.claims['official_website']['evidence_ids'])<2:
                for number_match in re.finditer(r'(?<!\d)(\d{3}[ .\u00a0]?\d{3}[ .\u00a0]?\d{3})(?!\d)',proof[2]):
                    if re.sub(r'[ .\u00a0]','',number_match.group(1))==profile.org:
                        profile.claims['official_website']['evidence_ids'].append(profile.ev(proof[0],None,span=proof[2][max(0,number_match.start()-25):number_match.end()+25]))
                        break
            candidate["status"] = "verified"
            profile.mark("website", "available", "Exact legal entity verified on company-owned page")
            home = result.snapshot["final_url"]
            profile.website_homepage=home
            links = []
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if re.search(r"om-oss|about|kontakt|contact|tjenester|services|produkter|products|karriere|career|ledig|jobs|nyhet|news|ledelse|leadership|locations|avdelinger", href + " " + a.get_text(" "), re.I):
                    try:
                        target = safe_url(urljoin(home, href))
                    except FetchError:
                        continue
                    if urlsplit(target).hostname == urlsplit(home).hostname and target not in links and target not in [p[0].snapshot["final_url"] for p in pages]:
                        links.append(target)
            if page_policy in {'focused','adaptive'}:
                # Score actual same-host navigation only. A contact proof page is
                # already collected; do not spend another slot on duplicate
                # contact/privacy prose before products or dated activity.
                def page_priority(url):
                    path=urlsplit(url).path.casefold()
                    if re.search(r'ledig|jobs|career|karriere|stillin',path):return 0
                    if re.search(r'nyhet|news|aktuelt|blog',path):return 1
                    if re.search(r'tjenest|service|produkt|product|kurs',path):return 2
                    if re.search(r'om[-_/]|about|ledelse|leadership|avdeling|location',path):return 3
                    return 4
                links.sort(key=page_priority)
            if page_policy=='adaptive':
                # Learn only from this company's already verified pages; no
                # precomputed company answers or assumed competition weights.
                extract_site(profile,pages,extraction=extraction)
                links=adaptive_links(profile,links)
            attempted_families=set()
            for target in links:
                if len(pages)>=max_pages:break
                if page_policy=='adaptive':
                    family=page_family(target)
                    if family in attempted_families or target not in adaptive_links(profile,[target]):continue
                    attempted_families.add(family)
                try:
                    child = await fetcher.get(target, "company_owned",attempts=1)
                    if child.snapshot["http_status"] in {200, 304} and "html" in child.snapshot["content_type"]:
                        cs, ct, cj = page_text(child.data)
                        cg = identity_gate(profile.org, profile.entity.get("navn", ""), identity_text(child,ct,cj))
                        if set(cg["observed_numbers"]) - {profile.org}:
                            profile.errors.append({"module": "website", "state": "ambiguous", "message": "Child page has conflicting identity; quarantined", "url": target})
                            continue
                        if urlsplit(child.snapshot["final_url"]).hostname != urlsplit(home).hostname:
                            continue
                        pages.append((child, cs, ct, cj))
                        if page_policy=='adaptive':extract_site(profile,[pages[-1]],extraction=extraction)
                except FetchError as exc:
                    profile.errors.append({"module": "website", "state": exc.state, "message": str(exc), "url": target})
            extract_site(profile, pages,extraction=extraction)
            return
        except FetchError as exc:
            candidate.update(status=exc.state, reason=str(exc))
            if exc.snapshot:
                profile.snapshots[exc.snapshot["id"]] = exc.snapshot
            last_state = exc.state
    profile.mark("website", last_state, "No verified site; " + "; ".join(str(c.get("reason", "candidate unverified")) for c in profile.candidates))


def extract_site(profile: Profile, pages: list, *, extraction='baseline'):
    jobs = activity = 0
    for result, soup, text, structured in pages:
        profile.verified_urls.add(result.snapshot["final_url"])
        desc = soup.find("meta", attrs={"name": re.compile("^description$", re.I)}) or soup.find("meta", attrs={"property": "og:description"})
        if desc and 35 <= len(desc.get("content", "")) <= 1200:
            value = desc["content"].strip()
            eid = profile.ev(result, None, span=value)
            key = "description:" + digest(result.snapshot["final_url"].encode())[:12]
            if business_description_page(profile,result.snapshot['final_url'],value):
                profile.add("website_description", value, eid, key=key, explanation="Company-authored business/about-page description; not independent verification")
            else:
                profile.retractions[key]=(eid,'Privacy/contact/navigation/product-page blurb is not a company business description; field classification withdrawn')
        extra_site_facts(profile,result,soup,text,flat_jsonld(structured))
        if extraction=='expanded':expanded_site_facts(profile,result,soup,text)
        for a in soup.select('a[href^="mailto:"],a[href^="tel:"]')[:12]:
            raw = a["href"]
            value=raw.split(':',1)[1].split('?',1)[0].strip()
            field='website_email' if raw.startswith('mailto:') else 'website_phone'
            if not company_contact_context(a):
                reject_contact(profile,result,field,value,a);continue
            parent=a.find_parent(['footer','div','p'])
            if parent and re.search(r'webdesign|utviklet av|developed by|powered by|website by',parent.get_text(' '),re.I):
                continue
            value = raw.split(":", 1)[1].split("?", 1)[0].strip()
            if not value or len(value) > 160:
                continue
            field = "website_email" if raw.startswith("mailto:") else "website_phone"
            if field=='website_email' and not re.fullmatch(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,20}',value):
                reject_contact(profile,result,field,value,a);continue
            if field=='website_phone' and (not re.fullmatch(r'[+\d .()\-]+',value) or not 6<=len(re.sub(r'\D','',value))<=15):
                reject_contact(profile,result,field,value,a);continue
            if not contact_is_new(profile,field,value):continue
            eid = profile.ev(result, None, span=raw)
            profile.add(field, value, eid, key=field + ":" + value, explanation="Published business contact on verified company site")
        for item in flat_jsonld(structured):
            typ = item.get("@type")
            types = typ if isinstance(typ, list) else [typ]
            if "JobPosting" in types and item.get("title") and item.get("datePosted"):
                # Company site is the source; preserve job employer/scope, never infer a parent job.
                employer = item.get("hiringOrganization", {})
                employer_name = employer.get("name", "") if isinstance(employer, dict) else ""
                if not employer_name or employer_name.casefold() != profile.entity.get("navn", "").casefold():
                    continue
                value=job_record(item,profile.entity.get('navn',''))
                if value:
                    # Derived status is labelled; all original scalar fields and
                    # the actual dates carry literal supporting evidence.
                    original={k:v for k,v in value.items() if k!='opening_status'}
                    key='job:'+digest(canonical(original).encode())[:16]
                    if add_structured(profile,result,'job_posting',original,key,effective=item['datePosted']):
                        profile.claims[key]['explanation']='Historical posting; opening status: '+value['opening_status']+'. Application window alone does not confirm the vacancy is still open.'
                        jobs+=1
            if any(t in {"NewsArticle", "Article", "BlogPosting"} for t in types) and item.get("headline") and item.get("datePublished"):
                headline = item["headline"]
                if not isinstance(headline, str) or headline not in result.data.decode("utf-8", "replace"):
                    continue
                published=iso_date(item['datePublished'])
                if not published or published>utcnow()[:10]:continue
                value={'headline':headline,'datePublished':item['datePublished']}
                if add_structured(profile,result,'dated_activity',value,'news:'+digest(canonical(value).encode())[:16],effective=item['datePublished']):activity+=1
    profile.mark("hiring", "available" if jobs else "failed", "Structured company-owned job postings" if jobs else "Bounded pages contained no publishable structured job postings; search incomplete, not confirmed absence")
    activity=sum(c['field']=='dated_activity' and c['availability']=='available' for c in profile.claims.values())
    profile.mark("activity", "available" if activity else "failed", "Dated company-owned articles" if activity else "No dated structured articles in bounded pages; search incomplete")
