"""Collect bounded original filings for explicit manual semantic review.

This separate diagnostic is not part of an evaluator batch. No OCR/model guesses,
numeric repairs, or automatic 'semantic audit passed' assertions are generated.
Install requirements-audit.txt only when running this optional review utility.
"""
import argparse
import asyncio
import io
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from signalpost.batch import atomic_json
from signalpost.http import Budget,Fetcher
from signalpost.store import Store


async def collect(args):
    from pypdf import PdfReader
    rows=[json.loads(l) for l in Path(args.input).read_text(encoding='utf-8').splitlines() if l.strip()]
    opportunities=[]
    for row in rows:
        by_period={}
        for c in row['claims']:
            if c['availability']=='available' and not c['stale'] and c['field'].startswith('financial.'):
                v=c['value'];by_period.setdefault(v['period']['tilDato'],[]).append(v)
        if by_period:
            period=max(by_period)
            opportunities.append((row,period,by_period[period]))
    selected=opportunities[:args.count]
    # Include observed currency/sign/scope edges without selecting on websites.
    for predicate in [lambda vs:any(v['amount'].startswith('-') for v in vs),lambda vs:any(v['currency']!='NOK' for v in vs),lambda vs:any(v['scope']=='group' for v in vs)]:
        edge=next((o for o in opportunities if predicate(o[2]) and o not in selected),None)
        if edge and len(selected)<args.max_records:selected.append(edge)
    budget=Budget(args.max_records,args.max_seconds);store=Store(Path(args.state));f=Fetcher(store,budget,timeout_seconds=120)
    records=[]
    try:
        for row,period,values in selected[:args.max_records]:
            org=row['organisation_number'];year=period[:4]
            record={'organisation_number':org,'legal_name':row['legal_identity']['legal_name'],'api_values':values,'review_status':'not_reviewed'}
            try:
                result=await f.get(f'https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/{org}/{year}','official_filed_accounts',robots=False,attempts=1,limit=8_000_000)
                record['snapshot']=result.snapshot
                if not result.data.startswith(b'%PDF'):raise ValueError('Source did not supply a PDF')
                reader=PdfReader(io.BytesIO(result.data));record['total_pages']=len(reader.pages)
                record['text_pages']=[{'page':i+1,'text':p.extract_text() or ''} for i,p in enumerate(reader.pages[:60])]
                if args.render:
                    import pymupdf
                    doc=pymupdf.open(stream=result.data,filetype='pdf')
                    folder=Path(args.state)/'review-images'/org;folder.mkdir(parents=True,exist_ok=True)
                    for i in range(min(8,len(doc))):doc[i].get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(str(folder/f'page-{i+1}.png'))
            except Exception as exc:record['error']=type(exc).__name__+': '+str(exc)
            records.append(record)
    finally:await f.close()
    atomic_json(args.output,{'purpose':'Original-file semantic review, not research coverage or automatic truth verification','operations':budget.report(),'records':records})
    store.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--state',required=True)
    p.add_argument('--count',type=int,default=6);p.add_argument('--max-records',type=int,default=10);p.add_argument('--max-seconds',type=float,default=900);p.add_argument('--render',action='store_true')
    a=p.parse_args()
    if not 1<=a.count<=a.max_records<=20:p.error('Require 1 <= count <= max-records <= 20')
    asyncio.run(collect(a))
