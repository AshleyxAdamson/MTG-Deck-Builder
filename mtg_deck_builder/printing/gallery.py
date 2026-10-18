"""The art gallery: one self-contained HTML page and a small server that saves taps.

The page is a template string with inline CSS and JS (no framework, no external assets).
This module does not know the print-file format: the caller hands it plain dicts and
receives `on_choose(name, source, id)` calls. See docs/spec/print-suite.md, "Step 2".
"""
from __future__ import annotations

import argparse
import html
import inspect
import ipaddress
import json
import secrets
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

TAILSCALE = "/opt/homebrew/bin/tailscale"
LIFETIME_SECONDS = 24 * 60 * 60
LOW_DPI = 600
MAX_BODY = 1_000_000


# ---------------------------------------------------------------- page

def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _url(value) -> str:
    """Escaped image URL, or "" when it is not http(s)."""
    value = str(value or "")
    return html.escape(value) if value.startswith(("http://", "https://")) else ""


def _style(cand: dict) -> str:
    return "render" if cand.get("source") == "mpcfill" else "scan"


def _dpi(cand: dict) -> str:
    return f"{cand['dpi']} dpi" if cand.get("dpi") else "? dpi"


def _caption(cand: dict) -> str:
    second = " · ".join(x for x in (cand.get("artist"), _dpi(cand)) if x)
    return f'<span class="l">{_esc(cand.get("label") or cand.get("id"))}</span><span class="a">{_esc(second)}</span>'


def _thumb(i: int, j: int, cand: dict, chosen: dict) -> str:
    q = f'{cand.get("label", "")} {cand.get("artist") or ""}'.lower()
    on = " on" if chosen and cand.get("id") == chosen.get("id") and cand.get("source") == chosen.get("source") else ""
    img = f'<img loading="lazy" decoding="async" alt="" src="{_url(cand.get("thumb"))}">' if _url(cand.get("thumb")) else '<i class="noimg"></i>'
    return (
        f'<button type="button" class="th{on}" data-j="{j}" data-style="{_style(cand)}" '
        f'data-fancy="{int(bool(cand.get("fancy")))}" data-ub="{int(bool(cand.get("universes_beyond")))}" '
        f'data-q="{_esc(q)}">{img}<span class="cap">{_caption(cand)}</span></button>'
    )


def _badge(cls: str, text: str, hidden: bool = False) -> str:
    return f'<span class="b {cls}"{" hidden" if hidden else ""}>{text}</span>'


def _badges(card: dict, ch: dict) -> str:
    out = [
        _badge("render", "RENDER", not ch or _style(ch) != "render"),
        _badge("scan", "SCAN", not ch or _style(ch) != "scan"),
        _badge("fancy", "FANCY", not ch.get("fancy")),
        _badge("low", "LOW RES", not (ch and ch.get("dpi") is not None and ch["dpi"] < LOW_DPI)),
        _badge("ub", "UNIVERSES BEYOND", not ch.get("universes_beyond")),
    ]
    if card.get("will_upscale") or card.get("upscaled_from"):
        src = f' from {_esc(card["upscaled_from"])} dpi' if card.get("upscaled_from") else ""
        out.append(_badge("up", "UPSCALE" + src))
    if card.get("printed"):
        out.append(_badge("printed", "PRINTED"))
    if card.get("status") == "missing":
        out.append(_badge("missing", "MISSING"))
    if card.get("kind") == "token":
        out.append(_badge("token", "TOKEN"))
    if (card.get("copies") or 1) > 1:
        out.append(_badge("copies", f'x{_esc(card["copies"])}'))
    return "".join(out)


def _controls(card: dict) -> str:
    parts = []
    if card.get("will_upscale") or card.get("upscaled_from"):
        mode = card.get("upscale") or "auto"
        btns = "".join(
            f'<button type="button" data-mode="{m}"{" class=on" if m == mode else ""}>{m}</button>'
            for m in ("auto", "never", "always")
        )
        parts.append(f'<div class="ctl"><span>Upscale</span><div class="seg" data-ctl="upscale">{btns}</div></div>')
    cmp_ = card.get("compare") or {}
    if _url(cmp_.get("before")) and _url(cmp_.get("after")):
        parts.append('<div class="ctl"><span>Compare</span><div class="seg" data-ctl="compare">'
                     '<button type="button" data-which="before">before</button>'
                     '<button type="button" data-which="after" class="on">after</button></div></div>')
    slots = card.get("slots")
    if slots:
        n = max(1, min(4, len(slots)))
        parts.append('<div class="ctl"><span>Spread over <b class="n">%d</b> arts</span>'
                     '<div class="seg" data-ctl="slots"><button type="button" data-d="-1" aria-label="fewer">−</button>'
                     '<button type="button" data-d="1" aria-label="more">+</button></div>'
                     '<small class="split"></small></div>' % n)
    return f'<div class="ctls">{"".join(parts)}</div>' if parts else ""


def _row(i: int, card: dict) -> str:
    ch = card.get("chosen") or {}
    cands = card.get("candidates") or []
    missing = card.get("status") == "missing"
    cls = "row" + (" printed" if card.get("printed") else "") + (" missing" if missing else "")
    large, thumb = _url(ch.get("large") or ch.get("thumb")), _url(ch.get("thumb"))
    if large or thumb:
        ph = f'<img class="ph" alt="" src="{thumb}">' if thumb else ""
        big = f'<div class="big" role="img" aria-label="{_esc(card.get("name"))}">{ph}<img class="large" alt="" src="{large or thumb}" loading="lazy" decoding="async"></div>'
    else:
        big = '<div class="big empty"><span>No printable image</span></div>'
    lock = '<span class="lock" title="Already printed">🔒</span>' if card.get("printed") else ""
    sub = " · ".join(x for x in (ch.get("artist"), _dpi(ch) if ch else None) if x)
    strip = "".join(_thumb(i, j, c, ch) for j, c in enumerate(cands))
    return (
        f'<section class="{cls}" data-i="{i}" data-name="{_esc(str(card.get("name")).lower())}">'
        f'<div class="main">{big}<div class="meta"><h3>{lock}{_esc(card.get("name"))}</h3>'
        f'<div class="label">{_esc(ch.get("label"))}</div><div class="sub">{_esc(sub)}</div>'
        f'<div class="badges">{_badges(card, ch)}</div></div></div>'
        f'<div class="side"><div class="strip">{strip}</div>{_controls(card)}</div></section>'
    )


def _groups(cards: list[dict]) -> list[tuple[str, list[int]]]:
    any_role = any(c.get("role") for c in cards)
    groups: dict[str, list[int]] = {}
    for i, c in enumerate(cards):
        if c.get("kind") == "token" and not c.get("role"):
            key = "Tokens"
        else:
            key = c.get("role") or ("Other" if any_role else "Cards")
        groups.setdefault(key, []).append(i)
    return sorted(groups.items(), key=lambda kv: kv[0] == "Tokens")


def render(deck: dict, cards: list[dict]) -> str:
    """The whole page as one string."""
    body = "".join(
        f'<h2 class="grp">{_esc(title)} <small>{len(idx)}</small></h2>' + "".join(_row(i, cards[i]) for i in idx)
        for title, idx in _groups(cards)
    )
    stats = [("to print", deck.get("to_print")), ("already printed", deck.get("already_printed")),
             ("missing", deck.get("missing")), ("bracket", deck.get("bracket")), ("free slots", deck.get("free_slots"))]
    stats_html = "".join(f'<li><b>{_esc(v)}</b> {k}</li>' for k, v in stats if v is not None)
    data = {"deck": {"name": deck.get("name")}, "cards": cards}
    data_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return (PAGE.replace("@@TITLE@@", _esc(deck.get("name") or "Gallery"))
            .replace("@@STATS@@", stats_html).replace("@@BODY@@", body)
            .replace("@@CSS@@", CSS).replace("@@JS@@", JS).replace("@@DATA@@", data_json))


def write(deck: dict, cards: list[dict], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(deck, cards), encoding="utf-8")
    return out_path


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>@@TITLE@@ gallery</title>
<style>@@CSS@@</style></head><body>
<header><h1>@@TITLE@@</h1><ul class="stats">@@STATS@@</ul></header>
<div class="bar"><span id="count">0 changed</span><button type="button" id="copy">Copy choices</button></div>
<div class="filters">
<div class="chips" role="group" aria-label="Style">
<button type="button" data-style="all" class="on">all</button><button type="button" data-style="render">renders</button>
<button type="button" data-style="scan">scans</button><button type="button" data-style="fancy">fancy only</button></div>
<label class="chk"><input type="checkbox" id="noub"> hide Universes Beyond</label>
<label class="chk"><input type="checkbox" id="showprinted"> show printed</label>
<input type="search" id="q" placeholder="Filter by artist or name" autocomplete="off"></div>
<main>@@BODY@@<p id="none" hidden>Nothing matches these filters.</p></main>
<div id="toast" role="status" hidden></div>
<script type="application/json" id="data">@@DATA@@</script>
<script>@@JS@@</script></body></html>
"""

CSS = """
:root{--bg:#0f1115;--panel:#181b22;--panel2:#20242d;--line:#2d323d;--fg:#e8eaf0;--dim:#9aa1b0;--acc:#6ea8fe;--ok:#4cc38a;--bad:#ef5b5b;--warn:#e5a93c}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.35 system-ui,-apple-system,Segoe UI,sans-serif;overflow-x:hidden}
button,input{font:inherit;color:inherit}button{cursor:pointer;min-height:44px}
header{padding:14px 14px 4px}h1{margin:0 0 6px;font-size:20px;overflow-wrap:anywhere}
.stats{display:flex;flex-wrap:wrap;gap:6px 14px;list-style:none;margin:0;padding:0;color:var(--dim)}.stats b{color:var(--fg)}
.bar{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:6px 14px;background:#12151bf2;border-bottom:1px solid var(--line);backdrop-filter:blur(6px)}
#count{font-weight:600}#count.some{color:var(--acc)}
#copy,.chips button,.seg button{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:0 14px}
.filters{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:10px 14px}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chips button.on,.seg button.on{background:var(--acc);border-color:var(--acc);color:#0b1020;font-weight:600}
.chk{display:flex;align-items:center;gap:6px;min-height:44px}.chk input{width:22px;height:22px}
#q{flex:1 1 180px;min-width:0;min-height:44px;padding:0 12px;background:var(--panel);border:1px solid var(--line);border-radius:8px}
main{padding:0 14px 60px}.grp{margin:22px 0 8px;font-size:16px;color:var(--acc);border-bottom:1px solid var(--line);padding-bottom:4px}.grp small{color:var(--dim)}
.row{display:grid;grid-template-columns:minmax(240px,330px) minmax(0,1fr);gap:14px;padding:12px;margin:0 0 12px;background:var(--panel);border:1px solid var(--line);border-radius:12px}
.row.printed .main,.row.printed .strip{opacity:.7}.row.missing{border-color:var(--bad)}
.main,.side{min-width:0}.big{position:relative;aspect-ratio:5/7;border-radius:4.5%;overflow:hidden;background:var(--panel2)}
.big img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.big img.ph{filter:blur(2px)}
.big.empty{display:flex;align-items:center;justify-content:center;color:var(--dim);border:1px dashed var(--bad)}
.meta h3{margin:10px 0 2px;font-size:17px;overflow-wrap:anywhere}.label{overflow-wrap:anywhere}.sub{color:var(--dim)}.lock{margin-right:6px}
.badges{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.b{font-size:11px;font-weight:700;letter-spacing:.03em;padding:2px 7px;border-radius:99px;background:var(--panel2);border:1px solid var(--line)}.b[hidden]{display:none}
.b.render{color:var(--ok)}.b.scan{color:var(--warn)}.b.fancy{color:#c79bff}.b.low,.b.missing{color:var(--bad);border-color:var(--bad)}
.b.up{color:var(--acc)}.b.printed{color:var(--dim)}.b.copies{color:var(--fg)}
.strip{display:flex;gap:10px;overflow-x:auto;padding-bottom:8px;scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch}
.th{flex:0 0 118px;display:flex;flex-direction:column;gap:4px;padding:4px;text-align:left;background:var(--panel2);border:2px solid transparent;border-radius:8px;scroll-snap-align:start}
.th.on{border-color:var(--acc)}.th[hidden]{display:none}.th img,.noimg{display:block;width:100%;aspect-ratio:5/7;object-fit:cover;border-radius:4px;background:#000}
.cap{display:flex;flex-direction:column;font-size:11px;line-height:1.25}.cap span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}
.cap .a{color:var(--dim)}.th.busy{opacity:.5}
.ctls{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:6px}.ctl{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--dim)}
.seg{display:inline-flex;gap:4px}.seg button{min-width:44px}.ctl small{color:var(--dim)}
#toast{position:fixed;left:12px;right:12px;bottom:14px;z-index:9;padding:12px 14px;background:#2b1d1d;border:1px solid var(--bad);border-radius:10px}
#toast.good{background:#16261e;border-color:var(--ok)}
@media (max-width:700px){.row{grid-template-columns:minmax(0,1fr)}.big{width:100%}}
"""

JS = r"""
(function(){
'use strict';
var D=JSON.parse(document.getElementById('data').textContent), cards=D.cards;
var T=new URLSearchParams(location.search).get('t')||'';
var KEY='gallery:'+(D.deck.name||''), changed={}, f={style:'all',noub:false,printed:false,q:''};
function $(s,r){return (r||document).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
function store(k,v){try{if(v===undefined)return localStorage.getItem(KEY+k);localStorage.setItem(KEY+k,v)}catch(e){}return null}
var tt;function toast(msg,good){var t=$('#toast');t.textContent=msg;t.className=good?'good':'';t.hidden=false;clearTimeout(tt);tt=setTimeout(function(){t.hidden=true},good?2500:7000)}
function post(path,body){
  body.t=T;
  return fetch(path+'?t='+encodeURIComponent(T),{method:'POST',headers:{'Content-Type':'application/json','X-Token':T},body:JSON.stringify(body)})
   .then(function(r){return r.json().catch(function(){return {ok:false,error:'HTTP '+r.status}})},function(){return {ok:false,gone:true}});
}
function gone(){toast('The server is not reachable. Your choice is kept on this page: use Copy choices and paste it to the agent.')}
function fail(res){if(res.gone)gone();else toast('Not saved: '+(res.error||'unknown error'))}
function tomlStr(s){return JSON.stringify(String(s))}
function updateBar(){var n=Object.keys(changed).length,c=$('#count');c.textContent=n+' changed';c.className=n?'some':''}
function row(i){return $('.row[data-i="'+i+'"]')}
function chosenOf(c){return c.chosen||{}}
function same(a,b){return a&&b&&a.id===b.id&&a.source===b.source}

function paint(i){
  var c=cards[i],ch=chosenOf(c),r=row(i);
  var big=$('.big',r);
  if(big.classList.contains('empty')){big.classList.remove('empty');big.innerHTML='<img class="ph" alt=""><img class="large" alt="">';big.setAttribute('role','img');big.setAttribute('aria-label',c.name)}
  var ph=$('.ph',big),lg=$('.large',big);
  if(ph&&ch.thumb)ph.src=ch.thumb;
  lg.src=ch.large||ch.thumb||'';
  $('.label',r).textContent=ch.label||'';
  $('.sub',r).textContent=[ch.artist,ch.dpi?ch.dpi+' dpi':'? dpi'].filter(Boolean).join(' · ');
  var show={render:ch.source==='mpcfill',scan:ch.source!=='mpcfill',fancy:!!ch.fancy,low:ch.dpi!=null&&ch.dpi<600,ub:!!ch.universes_beyond};
  Object.keys(show).forEach(function(k){var b=$('.b.'+k,r);if(b)b.hidden=!show[k]});
  $$('.th',r).forEach(function(t){t.classList.toggle('on',same(c.candidates[+t.dataset.j],ch))});
  var cmp=$('[data-ctl=compare]',r);
  if(cmp){cmp.parentNode.hidden=!same(ch,c.original||ch);$$('button',cmp).forEach(function(x){x.classList.toggle('on',x.dataset.which==='after')})}
}

function choose(i,j,btn){
  var c=cards[i],cand=c.candidates[j];
  if(same(cand,chosenOf(c)))return;
  if(c.printed&&!confirm('This card is already printed. Reprint it with this art?'))return;
  btn.classList.add('busy');
  post('/choose',{name:c.name,source:cand.source,id:cand.id}).then(function(res){
    btn.classList.remove('busy');
    if(!res.ok&&!res.gone){fail(res);return}
    if(c.original===undefined)c.original=chosenOf(c);
    c.chosen=cand;paint(i);
    if(same(c.original,cand))delete changed[c.name];else changed[c.name]={source:cand.source,id:cand.id};
    updateBar();
    if(res.gone)gone();
  });
}

function splitSlots(i,n){
  var c=cards[i],ids=c.candidates.slice(0,n),tot=0,k;
  for(k in c.slots)tot+=c.slots[k];
  if(!tot)tot=c.copies||n;
  var base=Math.floor(tot/n),extra=tot%n,out={};
  ids.forEach(function(x,idx){out[x.id]=base+(idx<extra?1:0)});
  return out;
}
function showSlots(i){
  var r=row(i),s=cards[i].slots,keys=Object.keys(s);
  $('.n',r).textContent=keys.length;
  $('.split',r).textContent=keys.map(function(k){return s[k]}).join(' / ');
}

function bind(){
  $$('.row').forEach(function(r){
    var i=+r.dataset.i,c=cards[i];
    $$('.th',r).forEach(function(t){t.addEventListener('click',function(){choose(i,+t.dataset.j,t)})});
    var up=$('[data-ctl=upscale]',r);
    if(up)$$('button',up).forEach(function(b){b.addEventListener('click',function(){
      post('/upscale',{name:c.name,mode:b.dataset.mode}).then(function(res){
        if(!res.ok){fail(res);return}
        c.upscale=b.dataset.mode;$$('button',up).forEach(function(x){x.classList.toggle('on',x===b)});
      })})});
    var cp=$('[data-ctl=compare]',r);
    if(cp)$$('button',cp).forEach(function(b){b.addEventListener('click',function(){
      var u=c.compare[b.dataset.which];if(!u)return;
      $('.large',r).src=u;$$('button',cp).forEach(function(x){x.classList.toggle('on',x===b)});
    })});
    var sl=$('[data-ctl=slots]',r);
    if(sl){showSlots(i);$$('button',sl).forEach(function(b){b.addEventListener('click',function(){
      var n=Math.max(1,Math.min(4,c.candidates.length,Object.keys(c.slots).length+(+b.dataset.d)));
      var slots=splitSlots(i,n);
      post('/slots',{name:c.name,slots:slots}).then(function(res){
        if(!res.ok){fail(res);return}
        c.slots=slots;showSlots(i);
      })})})}
  });
}

function apply(){
  var any=false;
  $$('.row').forEach(function(r){
    var c=cards[+r.dataset.i],q=f.q,hit=!q||c.name.toLowerCase().indexOf(q)>=0;
    $$('.th',r).forEach(function(t){
      var ok=true,on=t.classList.contains('on');
      if(f.style==='fancy')ok=t.dataset.fancy==='1';else if(f.style!=='all')ok=t.dataset.style===f.style;
      if(f.noub&&t.dataset.ub==='1')ok=false;
      var m=!q||t.dataset.q.indexOf(q)>=0;if(m&&q)hit=true;
      t.hidden=!(on||ok);
    });
    var vis=hit&&(f.printed||!c.printed);
    r.hidden=!vis;if(vis)any=true;
  });
  $$('.grp').forEach(function(h){var n=h.nextElementSibling,v=false;while(n&&n.classList.contains('row')){if(!n.hidden)v=true;n=n.nextElementSibling}h.hidden=!v});
  $('#none').hidden=any;
  store('filters',JSON.stringify(f));
}

function filters(){
  try{var s=JSON.parse(store('filters')||'null');if(s)f=Object.assign(f,s)}catch(e){}
  $$('.chips button').forEach(function(b){
    b.classList.toggle('on',b.dataset.style===f.style);
    b.addEventListener('click',function(){f.style=b.dataset.style;$$('.chips button').forEach(function(x){x.classList.toggle('on',x===b)});apply()});
  });
  $('#noub').checked=f.noub;$('#showprinted').checked=f.printed;$('#q').value=f.q;
  $('#noub').addEventListener('change',function(){f.noub=this.checked;apply()});
  $('#showprinted').addEventListener('change',function(){f.printed=this.checked;apply()});
  $('#q').addEventListener('input',function(){f.q=this.value.trim().toLowerCase();apply()});
}

function fragment(){
  return Object.keys(changed).map(function(n){var x=changed[n];
    return '[[choices]]\nname = '+tomlStr(n)+'\nsource = '+tomlStr(x.source)+'\nid = '+tomlStr(x.id)+'\n'}).join('\n');
}
function copy(){
  var txt=fragment();
  if(!txt){toast('Nothing changed yet.',true);return}
  var done=function(){toast('Copied '+Object.keys(changed).length+' choices.',true)};
  var legacy=function(){var a=document.createElement('textarea');a.value=txt;document.body.appendChild(a);a.select();
    try{document.execCommand('copy')?done():toast('Could not copy.')}catch(e){toast('Could not copy.')}a.remove()};
  if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(txt).then(done,legacy);else legacy();
}

$('#copy').addEventListener('click',copy);
filters();bind();apply();updateBar();
try{var y=+store('scroll');if(y)window.scrollTo(0,y)}catch(e){}
var st;window.addEventListener('scroll',function(){clearTimeout(st);st=setTimeout(function(){store('scroll',String(window.scrollY))},200)},{passive:true});
})();
"""


# ---------------------------------------------------------------- server

def pick_bind_address() -> tuple[str, str]:
    """(address, how): the Tailscale address, else the LAN address, else localhost."""
    try:
        out = subprocess.run([TAILSCALE, "ip", "-4"], capture_output=True, text=True, timeout=5).stdout
        for line in out.split():
            if ipaddress.ip_address(line).version == 4:
                return line, "tailscale"
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 80))  # UDP connect sends nothing; it only picks a route
            addr = s.getsockname()[0]
        if addr and not addr.startswith("127."):
            return addr, "lan"
    except OSError:
        pass
    return "127.0.0.1", "localhost"


class GalleryServer:
    """A running gallery server. `.url` carries the token."""

    def __init__(self, httpd: ThreadingHTTPServer, token: str, state: dict):
        self.httpd, self.token, self._state = httpd, token, state
        self.address, self.port = getattr(httpd, "advertise", httpd.server_address[0]), httpd.server_address[1]
        self.url = f"http://{self.address}:{self.port}/?t={token}"
        self.thread = threading.Thread(target=httpd.serve_forever, name="gallery", daemon=True)
        self.timer = threading.Timer(LIFETIME_SECONDS, self.stop)
        self.timer.daemon = True

    @property
    def changed(self) -> int:
        return self._state["changed"]

    def start(self) -> "GalleryServer":
        self.thread.start()
        self.timer.start()
        return self

    def stop(self) -> None:
        self.timer.cancel()
        if self.thread.is_alive():
            self.httpd.shutdown()
        self.httpd.server_close()


def _accepts_slots(fn) -> bool:
    try:
        params = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(p.name == "slots" or p.kind is p.VAR_KEYWORD for p in params)


def serve(out_path: Path, on_choose, on_upscale=None, *, bind: str | None = None, port: int = 0) -> GalleryServer:
    """Serve the page at out_path and write taps back through the callbacks."""
    out_path = Path(out_path)
    token = secrets.token_urlsafe(16)
    state = {"changed": 0}
    lock = threading.Lock()
    slots_ok = _accepts_slots(on_choose)

    class Handler(BaseHTTPRequestHandler):
        server_version = "mtg-gallery"

        def log_message(self, fmt, *args):
            line = (fmt % args).replace(token, "<token>")
            sys.stderr.write(f"[gallery] {self.address_string()} {line}\n")

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj).encode(), "application/json")

        def _authorized(self, supplied) -> bool:
            return isinstance(supplied, str) and secrets.compare_digest(supplied.encode(), token.encode())

        def do_GET(self):
            parts = urlsplit(self.path)
            if not self._authorized((parse_qs(parts.query).get("t") or [None])[0]):
                return self._json(403, {"ok": False, "error": "forbidden"})
            if parts.path in ("/", "/index.html"):
                try:
                    return self._send(200, out_path.read_bytes(), "text/html; charset=utf-8")
                except OSError as exc:
                    return self._json(404, {"ok": False, "error": str(exc)})
            if parts.path == "/done":
                return self._json(200, {"changed": state["changed"]})
            self._json(404, {"ok": False, "error": "not found"})

        def do_POST(self):
            parts = urlsplit(self.path)
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if not 0 < length <= MAX_BODY:
                    raise ValueError("bad body size")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("body must be an object")
            except (ValueError, json.JSONDecodeError) as exc:
                supplied = (parse_qs(parts.query).get("t") or [self.headers.get("X-Token")])[0]
                if not self._authorized(supplied):
                    return self._json(403, {"ok": False, "error": "forbidden"})
                return self._json(400, {"ok": False, "error": f"bad request: {exc}"})
            supplied = self.headers.get("X-Token") or body.get("t") or (parse_qs(parts.query).get("t") or [None])[0]
            if not self._authorized(supplied):
                return self._json(403, {"ok": False, "error": "forbidden"})
            name = body.get("name")
            if not isinstance(name, str) or not name:
                return self._json(400, {"ok": False, "error": "name is required"})
            try:
                if parts.path == "/choose":
                    source, ident = body.get("source"), body.get("id")
                    if not isinstance(source, str) or not isinstance(ident, str):
                        return self._json(400, {"ok": False, "error": "source and id are required"})
                    on_choose(name, source, ident)
                    with lock:
                        state["changed"] += 1
                elif parts.path == "/upscale":
                    mode = body.get("mode")
                    if on_upscale is None:
                        return self._json(400, {"ok": False, "error": "upscale is not supported"})
                    if mode not in ("auto", "never", "always"):
                        return self._json(400, {"ok": False, "error": "mode must be auto, never or always"})
                    on_upscale(name, mode)
                elif parts.path == "/slots":
                    slots = body.get("slots")
                    if not slots_ok:
                        return self._json(400, {"ok": False, "error": "slots are not supported"})
                    if not isinstance(slots, dict) or not all(isinstance(k, str) and isinstance(v, int) and v >= 0 for k, v in slots.items()):
                        return self._json(400, {"ok": False, "error": "slots must map id to a count"})
                    on_choose(name, None, None, slots=slots)
                else:
                    return self._json(404, {"ok": False, "error": "not found"})
            except Exception as exc:  # the callback decides what is an error; the page shows it
                return self._json(200, {"ok": False, "error": str(exc) or type(exc).__name__})
            self._json(200, {"ok": True})

    # Listen on every interface (the token is the lock), advertise the address the phone can reach.
    advertise = bind or pick_bind_address()[0]
    httpd = ThreadingHTTPServer((bind or "0.0.0.0", port), Handler)
    httpd.advertise = advertise
    httpd.daemon_threads = True
    return GalleryServer(httpd, token, state).start()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Serve a gallery from a JSON file holding {deck, cards}.")
    ap.add_argument("json_file", type=Path)
    ap.add_argument("--bind", help="address to bind (default: Tailscale, LAN, then localhost)")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args(argv)
    data = json.loads(args.json_file.read_text(encoding="utf-8"))
    out = write(data["deck"], data["cards"], args.json_file.with_suffix(".gallery.html"))

    def on_choose(name, source, ident, slots=None):
        print(f"choose {name!r}: slots={slots}" if slots is not None else f"choose {name!r}: {source} {ident}", file=sys.stderr, flush=True)

    def on_upscale(name, mode):
        print(f"upscale {name!r}: {mode}", file=sys.stderr, flush=True)

    how = "localhost" if args.bind else pick_bind_address()[1]
    server = serve(out, on_choose, on_upscale, bind=args.bind, port=args.port)
    print(f"Gallery ({how}): {server.url}", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        print(f"{server.changed} changed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
