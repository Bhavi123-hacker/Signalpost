"""Generate local schema and declared dependency metadata without network access."""
import importlib.metadata
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from signalpost.batch import atomic_json
from signalpost.models import Claim, Envelope, Evidence, InputRow

for name,model in [('input-row',InputRow),('output-envelope',Envelope),('claim',Claim),('evidence',Evidence)]:
    atomic_json(ROOT/'schemas'/(name+'.schema.json'),model.model_json_schema())

packages=[]
for d in importlib.metadata.distributions():
    m=d.metadata
    packages.append({'name':m['Name'],'version':m['Version'],'licence_expression':m.get('License-Expression'),'licence':m.get('License'),'classifiers':[c for c in m.get_all('Classifier',[]) if 'License' in c]})
atomic_json(ROOT/'docs/dependency-licences.json',sorted(packages,key=lambda p:p['name'].lower()))
