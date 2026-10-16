"""Conservative extractions from already verified company-owned HTML only."""
from __future__ import annotations
import html
import json
import re
from datetime import UTC,datetime
from urllib.parse import urlsplit,urljoin
from .models import canonical,digest


def structured_refs(profile,result,value):
    """Bind every published scalar to literal JSON-LD source bytes."""
    leaves=[]
    def walk(v):
        if isinstance(v,dict):
            for child in v.values():walk(child)
        elif isinstance(v,list):
            for child in v:walk(child)
        else:leaves.append(v)
    walk(value)
    if len(leaves)>30:return []
    raw=html.unescape(result.data.decode('utf-8','replace'));refs=[]
    for leaf in leaves:
        if leaf is None:continue
        variants=[str(leaf),json.dumps(leaf,ensure_ascii=True)[1:-1] if isinstance(leaf,str) else canonical(leaf)]
        span=next((v for v in variants if v and v in raw),None)
        if span is None:return []
        eid=profile.ev(result,None,span=span)
        if eid not in refs:refs.append(eid)
    return refs


def add_structured(profile,result,field,value,key,*,effective=None):
    refs=structured_refs(profile,result,value)
    if not refs:return False
    profile.add(field,value,refs[0],key=key,effective=effective,explanation='Explicit structured company-owned record; source-authored, not independent endorsement')
    profile.claims[key]['evidence_ids']=refs
    return True


def iso_date(value):
    if not isinstance(value,str):return None
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.date().isoformat()
    except ValueError:return None


def company_contact_context(node):
    """A verified publisher can quote a partner's contacts; exclude such blocks."""
    blocks=[node,*node.find_parents(['div','section','article','aside','footer'],limit=3)]
    for block in blocks:
        value=' '.join(block.stripped_strings)
        if len(value)>3000:continue
        if re.search(r'webdesign|utviklet av|developed by|powered by|website by|part of.{0,60}group|konsernsjef|group\s+(?:ceo|contact)|forhandler|dealers?|distribut[øo]r|third.party|avtales direkte|installat[øo]r',value,re.I):return False
    return True


def contact_normal(field,value):
    if field=='website_email':return value.casefold().strip()
    digits=re.sub(r'\D','',value)
    return digits[2:] if len(digits)==10 and digits.startswith('47') else digits


def contact_is_new(profile,field,value):
    return not any(c['field']==field and c['availability']=='available' and contact_normal(field,str(c['value']))==contact_normal(field,value) for c in profile.claims.values())


def business_description_page(profile,url,value=''):
    path=urlsplit(url).path.casefold()
    if re.search(r'privacy|personvern|integritet|cookies?|gdpr|vilk[åa]r|terms|kontakt|contact|kundeservice|/(?:products|produkter|services|tjenester)/',path):return False
    if re.search(r'personopplysning|privacy|integritetspolicy|cookie|informasjonskaps|fyll ut.{0,35}(?:kontakt|skjema)|du leser n[åa] innhold|her finner du innhold|here are the different options|kontaktinformasjon\s*:',value,re.I):return False
    home=getattr(profile,'website_homepage',None)
    return bool((home and url.rstrip('/')==home.rstrip('/')) or path in {'/','/index.html','/index.htm','/index.php'} or re.search(r'(?:^|/)(?:about|om(?:[-_/]|oss)|hvem[-_]er|virksomheten|bedriften)',path))


def reject_contact(profile,result,field,value,node,span=None):
    """Allow a later refresh to retract a known attribution defect explicitly."""
    span=span or node.get('href','') or ' '.join(node.stripped_strings)[:700]
    if span:
        try:eid=profile.ev(result,None,span=span)
        except ValueError:return
        profile.contact_rejections[(field,contact_normal(field,value))]=eid


def expanded_site_facts(profile,result,soup,text):
    """Source-authored content in older non-semantic HTML; never synthesize prose.

    Called only after the unchanged exact-company gate. Page chrome, forms,
    privacy text and developer credits are ineligible as business descriptions.
    """
    key='description:'+digest(result.snapshot['final_url'].encode())[:12]
    if key not in profile.claims and business_description_page(profile,result.snapshot['final_url']):
        legal_tokens=re.findall(r'\w+',profile.entity.get('navn','').casefold())
        name_pattern=r'[\W_]+'.join(re.escape(t) for t in legal_tokens)
        action=re.compile(r'\b(?:we\s+(?:are|supply|provide|offer|develop|deliver|help|build|speciali[sz]e)|vi\s+(?:er|tilbyr|leverer|utvikler|hjelper|driver|produserer)|selskapet\s+(?:driver|tilbyr|leverer)|company\b.{0,30}\b(?:services|consultancy|manufactur))',re.I)
        for node in soup.find_all('p',limit=100):
            if node.find_parent(['nav','footer','header','aside','form','dialog']):continue
            value=' '.join(node.stripped_strings)
            context=' '.join(' '.join(n.get('class',[]))+' '+n.get('id','') for n in [node,*list(node.parents)[:3]] if getattr(n,'attrs',None))
            if re.search(r'cookie|consent|privacy|personvern|modal|newsletter|nyhetsbrev|login|logginn',context,re.I):continue
            if not 65<=len(value)<=700 or value not in text:continue
            if not business_description_page(profile,result.snapshot['final_url'],value):continue
            if re.search(r'cookie|informasjonskaps|personvern|privacy|javascript|copyright|webdesign|utviklet av|developed by|powered by|terms of|vilkår',value,re.I):continue
            named=bool(name_pattern and re.search(name_pattern,value,re.I))
            if not action.search(value) and not (named and re.search(r'\b(?:consultancy|services|engineering|produksjon|tjenester|virksomhet|handel|utvikling)\b',value,re.I)):continue
            eid=profile.ev(result,None,span=value)
            profile.add('website_description',value,eid,key=key,explanation='Verbatim operational paragraph on exact-company verified site; company-authored, not independent endorsement')
            break
    # Text-only contacts must be explicitly labelled, outside forms/credits, and
    # bounded. An incidental number or developer email is never a contact fact.
    for node in soup.find_all(['p','address'],limit=100):
        if node.find_parent(['form','nav','header','aside','dialog']):continue
        context_allowed=company_contact_context(node)
        value=' '.join(node.stripped_strings)
        if len(value)>700 or re.search(r'webdesign|utviklet av|developed by|powered by|website by|personvern|privacy|cookie',value,re.I):continue
        for field,pattern in [
            ('website_email',r'(?i)(?:e-?post|e-?mail)\s*[:：]?\s*([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,20})'),
            ('website_phone',r'(?i)(?:telefon|phone|tlf\.?|tel\.?)\s*[:：]?\s*((?:\+47\s*)?(?:\d[ .\u00a0]?){7}\d)(?![ .\u00a0]*\d)')]:
            matches=list(re.finditer(pattern,value))
            if len(matches)>3:continue
            for match in matches:
                contact=match.group(1).strip();claim_key=field+':'+contact
                if not context_allowed:
                    reject_contact(profile,result,field,contact,node,match.group(0));continue
                if not contact_is_new(profile,field,contact) or match.group(0) not in text:continue
                if field=='website_email':
                    # A differently named email in a partner/group box must not
                    # become a company contact merely because it is quoted here.
                    domain=contact.rsplit('@',1)[-1].casefold()
                    host=(urlsplit(result.snapshot['final_url']).hostname or '').casefold()
                    registered=profile.entity.get('epostadresse','').rsplit('@',1)[-1].casefold()
                    if host!=domain and not host.endswith('.'+domain) and domain!=registered:continue
                eid=profile.ev(result,None,span=match.group(0))
                profile.add(field,contact,eid,key=claim_key,explanation='Explicitly labelled business contact in verified company text; original formatting retained')


def extra_site_facts(profile,result,soup,text,structured_items):
    url=result.snapshot['final_url']
    # Use an actual main/article paragraph when SEO metadata is absent. Never
    # synthesize an industry description or publish cookie/navigation text.
    key='description:'+digest(url.encode())[:12]
    if key not in profile.claims and business_description_page(profile,url):
        main=soup.find('main') or soup.find('article')
        if main:
            for p in main.find_all('p',limit=12):
                value=' '.join(p.stripped_strings)
                if not business_description_page(profile,url,value):continue
                if 80<=len(value)<=700 and not re.search(r'cookie|informasjonskaps|personvern|privacy|javascript|copyright',value,re.I):
                    if value not in text:continue
                    eid=profile.ev(result,None,span=value)
                    profile.add('website_description',value,eid,key=key,explanation='Verbatim company-authored main-content excerpt; not independent verification')
                    break
    # URL taxonomy alone does not turn an advisory article into a named service.
    # HTML product inference additionally needs an actual purchase control.
    # Structured exact-provider Service/Product records remain eligible below.
    purchase=soup.select_one('form[action*="/cart"],button[name="add"],input[name="add"]')
    purchase_page=bool(purchase and re.search(r'/(?:produkter|products)/[^/?]+',urlsplit(url).path,re.I))
    if not purchase_page and re.search(r'/(?:tjenester|services|produkter|products)/[^/?]+',urlsplit(url).path,re.I):
        heading=soup.find('h1');span=' '.join(heading.stripped_strings) if heading else ''
        if span and span in text:
            profile.retractions['service:'+digest(url.encode())[:16]]=(profile.ev(result,None,span=span),'Previous URL/headline-based offering inference is unsupported; an advisory article is not a named offering')
    if purchase_page:
        heading=soup.find('h1');name=' '.join(heading.stripped_strings) if heading else ''
        if 3<=len(name)<=160 and name in text:
            meta=soup.find('meta',attrs={'name':re.compile('^description$',re.I)}) or soup.find('meta',attrs={'property':'og:description'})
            paragraph=soup.find('main') or soup.find('article')
            para=paragraph.find('p') if paragraph else None
            description=meta.get('content','').strip() if meta else ' '.join(para.stripped_strings) if para else ''
            eid=profile.ev(result,None,span=name)
            value={'name':name,'page_url':url,'attribution':'buyable product on verified company site'}
            if 35<=len(description)<=700:value['description_excerpt']=description
            claim_key='service:'+digest(url.encode())[:16]
            profile.add('website_service',value,eid,key=claim_key)
            if 'description_excerpt' in value:profile.claims[claim_key]['evidence_ids'].append(profile.ev(result,None,span=description))
            control=purchase.get('action') or ' '.join(purchase.stripped_strings)
            if control and (control in text or control in html.unescape(result.data.decode('utf-8','replace'))):
                profile.claims[claim_key]['evidence_ids'].append(profile.ev(result,None,span=control[:700]))
    # Actual dated article elements; neither relative "yesterday" nor retrieval
    # time is substituted for a publication date. Keep the source-authored title.
    for article in soup.find_all('article',limit=12):
        stamp=article.find('time',attrs={'datetime':True})
        heading=article.find(['h1','h2','h3'])
        if not stamp or not heading:continue
        published=iso_date(stamp['datetime']);headline=' '.join(heading.stripped_strings)
        if not published or published>datetime.now(UTC).date().isoformat() or not 8<=len(headline)<=250:continue
        if headline not in text:continue
        date_ref=structured_refs(profile,result,stamp['datetime'])
        if not date_ref:continue
        eid=profile.ev(result,None,span=headline)
        value={'headline':headline,'datePublished':stamp['datetime'],'attribution':'dated article published on verified company site'}
        key='dated-html:'+digest(canonical([headline,stamp['datetime']]).encode())[:16]
        profile.add('dated_activity',value,eid,key=key,effective=stamp['datetime'],explanation='Explicit HTML article/time; no inference of independent sentiment or current event validity')
        profile.claims[key]['evidence_ids']+=date_ref
    for item in list(structured_items)[:60]:
        typ=item.get('@type');types=typ if isinstance(typ,list) else [typ]
        if any(t in {'Organization','Corporation','LocalBusiness','ProfessionalService','Store'} for t in types):
            name=item.get('legalName') or item.get('name','')
            normal=lambda s:re.sub(r'[^\w]+',' ',str(s).casefold()).strip()
            if normal(name)!=normal(profile.entity.get('navn','')):continue
            aliases=item.get('alternateName',[])
            if isinstance(aliases,str):aliases=[aliases]
            for alias in aliases[:5] if isinstance(aliases,list) else []:
                if isinstance(alias,str) and 2<=len(alias)<=160 and normal(alias)!=normal(name):
                    value={'legal_name':name,'alternate_name':alias}
                    if add_structured(profile,result,'public_brand',value,'brand:'+digest(canonical(value).encode())[:16]):
                        profile.mark('public_brand','available','Explicit alternate name in exact-legal-entity company structured data')
            address=item.get('address')
            if isinstance(address,dict) and address.get('streetAddress') and address.get('addressLocality'):
                value={k:address[k] for k in ('streetAddress','postalCode','addressLocality','addressRegion','addressCountry') if isinstance(address.get(k),str)}
                add_structured(profile,result,'website_location',value,'site-location:'+digest(canonical(value).encode())[:16])
        if 'Person' in types and isinstance(item.get('name'),str) and isinstance(item.get('jobTitle'),str):
            employer=item.get('worksFor',{})
            if isinstance(employer,dict) and str(employer.get('name','')).casefold()==profile.entity.get('navn','').casefold():
                value={'name':item['name'],'role':item['jobTitle'],'employer':employer['name']}
                add_structured(profile,result,'website_leadership',value,'site-person:'+digest(canonical(value).encode())[:16])
        if any(t in {'Service','Product'} for t in types) and isinstance(item.get('name'),str):
            provider=item.get('provider',item.get('seller',{}))
            # Explicit legal provider, never a partner's product inferred from name.
            if not isinstance(provider,dict) or str(provider.get('name','')).casefold()!=profile.entity.get('navn','').casefold():continue
            value={k:item[k] for k in ('name','description','serviceType','category') if isinstance(item.get(k),str) and len(item[k])<=700}
            value['provider']=provider['name']
            add_structured(profile,result,'website_service',value,'offering:'+digest(canonical(value).encode())[:16])


def job_record(item,legal_name,now=None):
    employer=item.get('hiringOrganization',{})
    if not isinstance(employer,dict) or str(employer.get('name','')).casefold()!=legal_name.casefold():return None
    posted=iso_date(item.get('datePosted'));until=iso_date(item.get('validThrough'))
    if not posted or not isinstance(item.get('title'),str):return None
    today=(now or datetime.now(UTC)).date().isoformat()
    if posted>today:return None
    if item.get('validThrough') and not until:return None
    status='expired' if until and until<today else 'within_published_application_window' if until else 'opening_status_unverified'
    value={k:item[k] for k in ('title','datePosted','validThrough','employmentType') if isinstance(item.get(k),str)}
    value['hiringOrganization']={'name':employer['name']}
    value['opening_status']=status
    return value
