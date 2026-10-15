from __future__ import annotations

import html
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from .http import FetchError, safe_url

CSS = """
:root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#152a30;background:#eef3f1;font-size:15px}
*{box-sizing:border-box}body{margin:0}a{color:#087568;text-decoration:none}a:hover{text-decoration:underline}
header{background:#142e32;color:white;padding:24px 5vw;display:flex;justify-content:space-between;gap:20px;align-items:center}
.logo{font-size:26px;font-weight:750;letter-spacing:-1px;color:white}.logo span{color:#8ae0bd}
.strap{font-size:12px;color:#adcbca;letter-spacing:1.2px;text-transform:uppercase}main{max-width:1240px;margin:auto;padding:32px 24px}
h1{font-size:clamp(26px,4vw,40px);line-height:1.15;margin:12px 0 16px;letter-spacing:-1px}h2{font-size:20px;margin:28px 0 16px}
p{line-height:1.65}.muted{color:#61767b}.eyebrow{font-size:12px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#087568}
.bar{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:24px 0}input{font:inherit;padding:14px;border:1px solid #bfcfca;border-radius:8px;min-width:260px;flex:1;background:white}
button,.button{font:inherit;cursor:pointer;border:0;border-radius:8px;background:#087568;color:white;padding:14px 22px;display:inline-block}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0}.stat,.panel{background:white;border:1px solid #d6e2dd;border-radius:12px;padding:22px}.stat strong{font-size:28px;display:block}.stat small{color:#61767b}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px}.card{display:block;background:white;border:1px solid #d6e2dd;border-radius:12px;padding:24px;color:inherit}.card:hover{border-color:#087568;text-decoration:none;box-shadow:0 4px 20px #1233210b}.card h3{font-size:18px;line-height:1.4;margin:12px 0}.mono{font-family:Consolas,monospace;font-size:13px}
.badge{display:inline-block;font-size:11px;padding:5px 9px;border-radius:20px;background:#edf1f2;color:#476166;white-space:nowrap}.available{background:#ddf5e9;color:#146440}.blocked,.ambiguous{background:#fff0cc;color:#815710}.failed{background:#fbe8e7;color:#974747}.stale{background:#efe4f7;color:#6f4389}
table{width:100%;border-collapse:collapse}td,th{text-align:left;vertical-align:top;padding:16px 12px;border-bottom:1px solid #e3ebe7}th{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#61767b}td:first-child{width:22%}.value{max-width:600px;overflow-wrap:anywhere;line-height:1.6}pre{white-space:pre-wrap;word-break:break-word;font:12px/1.6 Consolas,monospace;background:#f2f6f4;border-radius:8px;padding:14px}.scroll{overflow:auto}details{margin-top:10px}summary{cursor:pointer;color:#087568}.evidence{scroll-margin-top:20px;margin:12px 0;padding:18px;background:white;border:1px solid #d6e2dd;border-radius:10px}.links{display:flex;gap:14px;flex-wrap:wrap}footer{max-width:1240px;margin:auto;padding:24px;color:#61767b;font-size:12px}
@media(max-width:680px){header{padding:20px}.strap{display:none}main{padding:24px 16px}.stats{grid-template-columns:1fr 1fr}.panel{padding:12px}td,th{padding:12px 8px}table{min-width:560px}input{min-width:180px}h1{overflow-wrap:anywhere}}
"""


def esc(value):
    return html.escape(str(value), quote=True)


def display(value):
    if isinstance(value, (dict, list)):
        return "<pre>" + esc(json.dumps(value, ensure_ascii=False, indent=2)) + "</pre>"
    return esc(value)


def badge(state):
    return f'<span class="badge {esc(state)}">{esc(state.replace("_", " "))}</span>'


def shell(title, body):
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(title) + '</title><style>' + CSS + '</style></head><body><header><a class="logo" href="/">Signal<span>post.</span></a><div class="strap">Norwegian companies · evidence first</div></header><main>' + body + '</main><footer>Bhavy Garg · 24BAI1088 · VIT Chennai<br>Local research viewer. Unknown and blocked fields are shown explicitly. Company statements are attributed to their sources.</footer></body></html>'


def profile_html(row, history):
    org = row["organisation_number"]
    title = row["legal_identity"].get("legal_name") or org
    body = f'<a href="/">← All companies</a><p class="eyebrow">Company profile / {esc(org)}</p><h1>{esc(title)}</h1>'
    body += f'<div class="links">{badge(row["availability"])}<span class="muted mono">Checked {esc(row["refresh"]["checked_at"])}</span><a href="/export/{quote(org)}">Export JSON ↗</a></div>'
    current = sum(c["availability"] == "available" and not c["stale"] for c in row["claims"])
    body += '<div class="stats">' + ''.join(f'<div class="stat"><strong>{esc(v)}</strong><small>{esc(k)}</small></div>' for k, v in [("Current facts", current), ("Evidence references", len(row["evidence"])), ("Changes this run", len(row["changes"])), ("API cost USD", "0.00")]) + '</div>'
    descriptions = [c for c in row['claims'] if c['availability']=='available' and not c['stale'] and c['field'] in {'website_description','registered_activity'}]
    descriptions.sort(key=lambda c:c['field']!='website_description')
    if descriptions:
        c=descriptions[0]
        label='Company-authored website description' if c['field']=='website_description' else 'Self-reported registered activity'
        body+='<h2>What the company does</h2><div class="panel"><div class="eyebrow">'+esc(label)+'</div><p>'+display(c['value'])+'</p><a href="#'+esc(c['evidence_ids'][0])+'">Check the source →</a></div>'
    financial=[c for c in row['claims'] if c['availability']=='available' and not c['stale'] and c['field'].startswith('financial.')]
    if financial:
        last=max(c['value']['period']['tilDato'] for c in financial)
        body+='<h2>Latest returned accounts · '+esc(last)+'</h2><div class="panel scroll"><table><thead><tr><th>Metric & scope</th><th>Reported amount</th><th>Evidence</th></tr></thead><tbody>'
        for c in financial:
            v=c['value']
            if v['period']['tilDato']!=last: continue
            body+='<tr><td>'+esc(v['metric'].replace('_',' '))+' · '+esc(v['scope'])+'</td><td>'+esc(v['amount'])+' '+esc(v['currency'])+'<br><small class="muted">'+esc(v['period']['fraDato'])+' to '+esc(v['period']['tilDato'])+' · API currency units, scale '+str(v['scale'])+'</small></td><td><a href="#'+esc(c['evidence_ids'][0])+'">Source ↗</a></td></tr>'
        body+='</tbody></table></div>'
    body += '<h2>Research status</h2><div class="panel">' + ''.join(f'<p>{badge(v["availability"])} <strong>{esc(k.replace("_", " "))}</strong> <span class="muted">{esc(v["explanation"])}</span></p>' for k, v in row["modules"].items()) + '</div>'
    body += '<h2>Facts & provenance</h2><div class="panel scroll"><table><thead><tr><th>Field</th><th>Observation</th><th>Evidence</th></tr></thead><tbody>'
    for c in row["claims"]:
        links = ' '.join(f'<a href="#{esc(eid)}">[{i+1}]</a>' for i, eid in enumerate(c["evidence_ids"]))
        value = display(c["value"]) if c["availability"] == "available" else esc(c["explanation"])
        details = '<details><summary>Dates & status</summary>' + display({k: c.get(k) for k in ("availability", "first_seen", "last_checked", "effective_at", "reporting_period", "stale", "explanation")}) + '</details>'
        body += f'<tr><td>{esc(c["field"].replace("_", " "))}<br>{badge("stale" if c["stale"] else c["availability"])}</td><td class="value">{value}{details}</td><td>{links}</td></tr>'
    body += '</tbody></table></div><h2>Collected evidence</h2>'
    for e in row["evidence"]:
        try:
            url = safe_url(e["final_url"])
            link = f'<a rel="noopener noreferrer" target="_blank" href="{esc(url)}">{esc(url)} ↗</a>'
        except FetchError:
            link = esc(e["final_url"])
        body += f'<article id="{esc(e["id"])}" class="evidence"><div class="eyebrow">{esc(e["source_class"])}</div><p>{link}</p><p>{esc(e["claim_span"])}</p><details><summary>Source path, hash & timestamps</summary>{display(e)}</details></article>'
    body += '<h2>Website candidates</h2><div class="panel">' + display(row["website_candidates"]) + '</div>'
    body += '<h2>Change history</h2>'
    for prior in history:
        body += '<details class="panel"><summary>' + esc(prior["run_id"]) + ' · ' + str(len(prior["changes"])) + ' changes</summary>' + display(prior["changes"]) + '</details>'
    return shell(title + " · Signalpost", body)


def handler_for(state: str, port: int):
    db_path = (Path(state) / "signalpost.sqlite").resolve()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                self.send_error(403)
                return
            try:
                with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as db:
                    p = urlsplit(self.path)
                    org = p.path.rsplit("/", 1)[-1]
                    if p.path.startswith(("/company/", "/export/")):
                        record = db.execute("SELECT envelope FROM current_profiles WHERE org=?", (org,)).fetchone()
                        if not record:
                            self.send_error(404)
                            return
                        row = json.loads(record[0])
                        if p.path.startswith("/export/"):
                            self.respond(json.dumps(row, ensure_ascii=False, indent=2), "application/json; charset=utf-8", attachment=org + ".json")
                            return
                        history = [json.loads(h[0]) for h in db.execute("SELECT envelope FROM history WHERE org=? ORDER BY rowid DESC LIMIT 20", (org,))]
                        body = profile_html(row, history)
                    elif p.path == "/":
                        q = parse_qs(p.query).get("q", [""])[0][:100]
                        all_rows = [json.loads(r[0]) for r in db.execute("SELECT envelope FROM current_profiles")]
                        rows = [r for r in all_rows if q.casefold() in (r["organisation_number"] + " " + str(r["legal_identity"].get("legal_name") or "")).casefold()]
                        body = '<div class="eyebrow">Research workspace</div><h1>Know the company.<br>Check the evidence.</h1><p class="muted">Search collected Norwegian companies. Every published fact links to a saved source.</p>'
                        body += f'<form class="bar" action="/" method="get"><input name="q" aria-label="Search name or organisation number" placeholder="Search company or organisation number" value="{esc(q)}"><button>Search companies</button></form>'
                        body += '<div class="stats">' + ''.join(f'<div class="stat"><strong>{v}</strong><small>{k}</small></div>' for k, v in [("Collected profiles", len(all_rows)), ("Search matches", len(rows)), ("Verified websites", sum(any(c["field"] == "official_website" and c["availability"] == "available" and not c["stale"] for c in r["claims"]) for r in all_rows)), ("Paid API spend", "$0")]) + '</div><div class="grid">'
                        for r in rows[:200]:
                            org = r["organisation_number"]
                            count = sum(c["availability"] == "available" and not c["stale"] for c in r["claims"])
                            body += f'<a class="card" href="/company/{quote(org)}"><span class="mono muted">{esc(org)}</span><h3>{esc(r["legal_identity"].get("legal_name") or "Identity unavailable")}</h3>{badge(r["availability"])}<p class="muted">{count} current facts · {len(r["evidence"])} evidence references</p><span>Inspect profile →</span></a>'
                        body += '</div><p class="muted">Showing up to 200 matches; refine search to find a company.</p>'
                        body = shell("Signalpost · Research workspace", body)
                    else:
                        self.send_error(404)
                        return
                self.respond(body, "text/html; charset=utf-8")
            except (sqlite3.Error, OSError):
                self.send_error(503, "Collect a batch into this state directory first")

        def respond(self, body, content_type, attachment=None):
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            if attachment:
                safe_name = ''.join(c for c in attachment if c.isascii() and (c.isalnum() or c in '.-_'))
                self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            pass

    return Handler


def serve(state, port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_for(state, port))
    print(f"Signalpost viewer: http://127.0.0.1:{port} (local only)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
