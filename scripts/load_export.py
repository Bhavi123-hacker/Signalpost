"""Load labelled real official-data exports into a local viewer. No network."""
import argparse
import json
import gzip
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from signalpost.models import canonical,validate_envelopes
from signalpost.store import Store

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--state',required=True)
    args=p.parse_args()
    with (gzip.open(args.input,'rt',encoding='utf-8') if str(args.input).endswith('.gz') else open(args.input,encoding='utf-8')) as handle:
        rows=[json.loads(l) for l in handle if l.strip()]
    assert validate_envelopes(rows)['passed']
    store=Store(args.state)
    for row in rows:
        store.db.execute('INSERT OR REPLACE INTO current_profiles VALUES(?,?)',(row['organisation_number'],canonical(row)))
        store.db.execute('INSERT OR REPLACE INTO history VALUES(?,?,?)',(row['organisation_number'],row['run_id'],canonical(row)))
    store.db.commit(); store.close(); print('Loaded',len(rows),'real exported profiles; no network requests')
