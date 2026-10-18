"""The art gallery: one self-contained HTML page and a small server that saves taps.

The page is a template string with inline CSS and JS (no framework, no external assets,
no build step). Each card is a swipeable carousel of full-size candidate images with a
"Use this art" button under each slide. This module does not know the print-file format:
the caller hands it plain dicts and receives `on_choose(name, source, id)` calls.
See docs/spec/print-suite.md, "Step 2: the gallery".
"""
from __future__ import annotations

import argparse
import html
import inspect
import ipaddress
import json
import re
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
MAX_STYLE_CHIPS = 12


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


def _same(a: dict, b: dict) -> bool:
    return bool(a) and bool(b) and a.get("id") == b.get("id") and a.get("source") == b.get("source")


def _styles(cand: dict) -> list[str]:
    """The candidate's style keys: clean strings, no duplicates, no empties ([] when unknown)."""
    raw = cand.get("styles") or []
    if isinstance(raw, str):
        raw = [raw]
    out: list[str] = []
    for k in raw if isinstance(raw, (list, tuple)) else []:
        k = str(k).strip().replace("|", "")
        if k and k not in out:
            out.append(k)
    return out


def _style_counts(cards: list[dict]) -> list[tuple[str, int]]:
    """Style keys on the page, most common first (ties alphabetical), at most MAX_STYLE_CHIPS."""
    counts: dict[str, int] = {}
    for card in cards:
        for cand in card.get("candidates") or []:
            for k in _styles(cand):
                counts[k] = counts.get(k, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_STYLE_CHIPS]


def _style_buttons(cards: list[dict]) -> str:
    return "".join(
        f'<button type="button" data-key="{_esc(k)}" aria-pressed="false" title="{n} candidates">{_esc(k)}</button>'
        for k, n in _style_counts(cards)
    )


def _chip(cls: str, text: str) -> str:
    return f'<span class="chip {cls}">{text}</span>'


def _slide(j: int, cand: dict, chosen: dict) -> str:
    on = _same(cand, chosen)
    thumb, large = _url(cand.get("thumb")), _url(cand.get("large") or cand.get("thumb"))
    ph = f'<img class="ph" alt="" loading="lazy" decoding="async" src="{thumb}">' if thumb else ""
    big = f'<img class="large" alt="" loading="lazy" decoding="async" src="{large}">' if large else ""
    label = cand.get("label") or cand.get("id")
    second = " · ".join(x for x in (cand.get("artist"), _dpi(cand)) if x)
    keys = _styles(cand)
    std = cand.get("standard") is not False
    chips = _chip(_style(cand), _style(cand).upper())
    chips += "".join(_chip("sty", _esc(k)) for k in keys)
    if not std:
        chips += _chip("nostd", "NO RULES BOX")
    lang = str(cand.get("language") or "").strip()
    if lang and lang.upper() != "EN":
        chips += _chip("lang", _esc(lang.upper()))
    rs = str(cand.get("render_source") or "").strip()
    strip = ('<button type="button" data-act="one">Hide this art</button>'
             + (f'<button type="button" data-act="all">Hide all from {_esc(rs)}</button>' if rs else "")
             + '<button type="button" data-act="cancel">Cancel</button>')
    ub = bool(cand.get("universes_beyond")) or "universes-beyond" in keys
    q = f'{cand.get("label", "")} {cand.get("artist") or ""}'.lower()
    return (
        f'<figure class="slide{" on" if on else ""}" data-j="{j}" data-style="{_style(cand)}" '
        f'data-styles="|{_esc("|".join(keys))}|" data-std="{int(std)}" data-ub="{int(ub)}" data-rs="{_esc(rs)}" data-q="{_esc(q)}">'
        f'<div class="img" role="img" aria-label="{_esc(label)}">{ph}{big}</div>'
        f'<figcaption><span class="l">{_esc(label)}</span><span class="a">{_esc(second)}</span>'
        f'<span class="chips">{chips}</span></figcaption>'
        f'<div class="acts"><button type="button" class="use"{" disabled" if on else ""}>{"Chosen" if on else "Use this art"}</button>'
        f'<button type="button" class="hidebtn" aria-label="Hide this art">Hide</button></div>'
        f'<div class="hidestrip" hidden>{strip}</div></figure>'
    )


def _badge(cls: str, text: str, hidden: bool = False) -> str:
    return f'<span class="b {cls}"{" hidden" if hidden else ""}>{text}</span>'


def _badges(card: dict, ch: dict) -> str:
    out = []
    if (card.get("copies") or 1) > 1:
        out.append(_badge("copies", f'x{_esc(card["copies"])}'))
    if card.get("kind") == "token":
        out.append(_badge("token", "TOKEN"))
    if card.get("status") == "missing":
        out.append(_badge("missing", "MISSING"))
    # "Low res" means the only image is a placeholder-quality scan, not an ordinary 300 dpi scan
    # (those are upscaled and get the UPSCALE badge instead).
    out.append(_badge("low", "LOW RES", not (card.get("status") == "lowres" or (ch and ch.get("lowres")))))
    if card.get("will_upscale") or card.get("upscaled_from"):
        src = f' from {_esc(card["upscaled_from"])} dpi' if card.get("upscaled_from") else ""
        out.append(_badge("up", "UPSCALE" + src))
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
    if card.get("slots"):
        parts.append('<div class="ctl"><span>Spread over <b class="n"></b> arts</span>'
                     '<div class="seg" data-ctl="slots"><button type="button" data-d="-1" aria-label="fewer">−</button>'
                     '<button type="button" data-d="1" aria-label="more">+</button></div>'
                     '<small class="split"></small></div>')
    return f'<div class="ctls">{"".join(parts)}</div>' if parts else ""


def _row(i: int, card: dict) -> str:
    ch = card.get("chosen") or {}
    cands = list(enumerate(card.get("candidates") or []))
    # The chosen candidate first, then the rest in ranking order.
    cands.sort(key=lambda jc: not _same(jc[1], ch))
    if cands:
        track = "".join(_slide(j, c, ch) for j, c in cands)
        car = (f'<div class="carwrap"><button type="button" class="arr prev" aria-label="Previous art">‹</button>'
               f'<div class="car" tabindex="0">{track}</div>'
               f'<button type="button" class="arr next" aria-label="Next art">›</button></div>'
               f'<div class="pos" aria-live="polite"></div>')
    else:
        car = '<div class="none-img">No printable image</div>'
    return (
        f'<section class="row{" missing" if card.get("status") == "missing" else ""}" data-i="{i}">'
        f'<div class="hd"><h3>{_esc(card.get("name"))}</h3><div class="badges">{_badges(card, ch)}</div></div>'
        f'{car}{_controls(card)}</section>'
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
    parts = {"TITLE": _esc(deck.get("name") or "Gallery"), "STATS": stats_html, "BODY": body,
             "STYLES": _style_buttons(cards), "CSS": CSS, "JS": JS, "DATA": data_json}
    # One pass, so text inside a card name can never be mistaken for a placeholder.
    return re.sub(r"@@([A-Z]+)@@", lambda m: parts[m.group(1)], PAGE)


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
<div id="banners"><div class="ban" id="fail" role="alert" hidden><span id="failmsg"></span><button type="button" id="failx">Dismiss</button></div>
<div class="ban" id="stale" role="alert" hidden><span>This gallery was restarted or stopped. Reload to continue.</span><button type="button" id="reload">Reload</button></div></div>
<header><h1>@@TITLE@@</h1><ul class="stats">@@STATS@@</ul></header>
<div class="bar"><span id="count">0 changed</span><button type="button" id="copy">Copy choices</button></div>
<div class="filters">
<div class="chips" id="fchips" role="group" aria-label="Style">
<button type="button" data-src="all" class="on">all</button><button type="button" data-src="render">renders</button>
<button type="button" data-src="scan">scans</button>@@STYLES@@</div>
<label class="chk"><input type="checkbox" id="noub"> hide Universes Beyond</label>
<label class="chk"><input type="checkbox" id="std"> standard frames only</label>
<input type="search" id="q" placeholder="Filter by artist or name" autocomplete="off"></div>
<main>@@BODY@@<p id="none" hidden>Nothing matches these filters.</p></main>
<div id="toast" role="status" hidden></div>
<script type="application/json" id="data">@@DATA@@</script>
<script>@@JS@@</script></body></html>
"""

CSS = """
:root{--bg:#0f1115;--panel:#181b22;--panel2:#20242d;--line:#2d323d;--fg:#e8eaf0;--dim:#9aa1b0;--acc:#6ea8fe;--ok:#4cc38a;--bad:#ef5b5b;--warn:#e5a93c;--gap:12px}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.35 system-ui,-apple-system,Segoe UI,sans-serif;overflow-x:hidden}
button,input{font:inherit;color:inherit}button{cursor:pointer;min-height:44px}button:disabled{cursor:default}
header,.filters,main{padding-left:16px;padding-right:16px;max-width:1100px;margin:0 auto}
header{padding-top:14px;padding-bottom:4px}h1{margin:0 0 6px;font-size:20px;overflow-wrap:anywhere}
.stats{display:flex;flex-wrap:wrap;gap:6px 14px;list-style:none;margin:0;padding:0;color:var(--dim)}.stats b{color:var(--fg)}
.bar{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:6px 16px;background:#12151bf2;border-bottom:1px solid var(--line);backdrop-filter:blur(6px)}
#count{font-weight:600}#count.some{color:var(--acc)}
#copy,.chips>button,.seg button{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:0 14px}
.filters{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding-top:10px;padding-bottom:10px}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chips>button.on,.seg button.on{background:var(--acc);border-color:var(--acc);color:#0b1020;font-weight:600}
.chk{display:flex;align-items:center;gap:6px;min-height:44px}.chk input{width:22px;height:22px}
#q{flex:1 1 180px;min-width:0;min-height:44px;padding:0 12px;background:var(--panel);border:1px solid var(--line);border-radius:8px}
main{padding-bottom:60px}.grp{margin:22px 0 8px;font-size:16px;color:var(--acc);border-bottom:1px solid var(--line);padding-bottom:4px}.grp small{color:var(--dim)}
.row{min-width:0;padding:12px 0 14px;margin:0 0 10px;border-bottom:1px solid var(--line)}.row[hidden]{display:none}
.hd{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;margin-bottom:8px}.hd h3{margin:0;font-size:18px;overflow-wrap:anywhere}
.badges{display:flex;flex-wrap:wrap;gap:4px}
.b{font-size:11px;font-weight:700;letter-spacing:.03em;padding:2px 7px;border-radius:99px;background:var(--panel2);border:1px solid var(--line)}.b[hidden]{display:none}
.b.low,.b.missing{color:var(--bad);border-color:var(--bad)}.b.up{color:var(--acc)}.b.token{color:var(--warn)}
.carwrap{display:grid;grid-template-columns:minmax(0,1fr);align-items:center}
.car{display:flex;gap:var(--gap);overflow-x:auto;overflow-y:hidden;scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain;position:relative;scrollbar-width:none;min-width:0}
.car::-webkit-scrollbar{display:none}.car:focus-visible{outline:2px solid var(--acc)}
.slide{flex:0 0 min(100%,420px);margin:0;scroll-snap-align:center;display:flex;flex-direction:column;gap:6px;padding:6px;background:var(--panel);border:2px solid transparent;border-radius:12px}
.slide.on{border-color:var(--acc)}.slide[hidden]{display:none}
.img{position:relative;aspect-ratio:63/88;width:100%;border-radius:4.5%;overflow:hidden;background:var(--panel2)}
.img img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}.img img.ph{filter:blur(2px)}
figcaption{display:flex;flex-direction:column;gap:2px;min-height:4.6em}.l{overflow-wrap:anywhere;font-weight:600}.a{color:var(--dim);font-size:13px}
.chips .chip{font-size:10px;font-weight:700;padding:1px 6px;border-radius:99px;background:var(--panel2);border:1px solid var(--line)}
.chip.render{color:var(--ok)}.chip.scan{color:var(--warn)}.chip.sty{color:var(--acc);text-transform:uppercase}
.chip.nostd{color:var(--dim);background:transparent;border-style:dashed}
.slide .chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}
.acts{display:flex;gap:6px}.acts .use{width:auto;flex:1 1 0;min-width:0}
.hidebtn{flex:none;min-width:64px;min-height:44px;padding:0 12px;background:transparent;border:1px solid var(--line);border-radius:8px;color:var(--dim)}.hidebtn[hidden]{display:none}
.hidestrip{display:flex;flex-direction:column;gap:6px}.hidestrip[hidden]{display:none}
.hidestrip button{min-height:44px;padding:4px 10px;border-radius:8px;border:1px solid var(--bad);background:transparent;color:var(--bad);font-weight:600;overflow-wrap:anywhere}
.hidestrip button[data-act=cancel]{border-color:var(--line);color:var(--dim)}
.chip.lang{color:var(--warn)}
.use{width:100%;min-height:44px;border:1px solid var(--acc);border-radius:8px;background:var(--acc);color:#0b1020;font-weight:700}
.use:disabled{background:var(--panel2);border-color:var(--line);color:var(--dim)}.slide.busy{opacity:.55}
.arr{display:none;width:44px;height:44px;border-radius:50%;background:var(--panel2);border:1px solid var(--line);font-size:24px;line-height:1;padding:0}
.pos{text-align:center;color:var(--dim);font-size:13px;margin-top:6px;font-variant-numeric:tabular-nums}
.none-img{padding:28px 12px;text-align:center;color:var(--dim);border:1px dashed var(--bad);border-radius:12px}
.ctls{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:8px}.ctl{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--dim)}.ctl[hidden]{display:none}
.seg{display:inline-flex;gap:4px}.seg button{min-width:44px}.ctl small{color:var(--dim)}
#banners{position:fixed;top:0;left:0;right:0;z-index:20}
.ban{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 16px;font-weight:600;border-bottom:2px solid var(--bad);background:#5a1717}.ban[hidden]{display:none}
#stale{border-color:var(--warn);background:#4a3a12}.ban button{flex:none;padding:0 14px;background:var(--panel2);border:1px solid var(--line);border-radius:8px}
#toast{position:fixed;left:16px;right:16px;bottom:14px;z-index:9;padding:12px 14px;background:#2b1d1d;border:1px solid var(--bad);border-radius:10px}
#toast.good{background:#16261e;border-color:var(--ok)}
@media (min-width:700px){
.carwrap{grid-template-columns:44px minmax(0,1fr) 44px;gap:8px}.arr{display:block}.arr[disabled]{opacity:.3}
.slide{flex-basis:min(100%,300px)}}
"""

JS = r"""
(function(){
'use strict';
var D=JSON.parse(document.getElementById('data').textContent), cards=D.cards;
var T=new URLSearchParams(location.search).get('t')||'';
var KEY='gallery:'+(D.deck.name||''), changed={}, f={src:'all',sty:[],noub:false,std:false,q:''};
function $(s,r){return (r||document).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
function store(k,v){try{if(v===undefined)return localStorage.getItem(KEY+k);localStorage.setItem(KEY+k,v)}catch(e){}return null}
var tt;function toast(msg,good){var t=$('#toast');t.textContent=msg;t.className=good?'good':'';t.hidden=false;clearTimeout(tt);tt=setTimeout(function(){t.hidden=true},good?2000:7000)}
function post(path,body){
  body.t=T;
  return fetch(path+'?t='+encodeURIComponent(T),{method:'POST',headers:{'Content-Type':'application/json','X-Token':T},body:JSON.stringify(body)})
   .then(function(r){
     return r.json().then(null,function(){return null}).then(function(j){
       if(r.ok&&j&&j.ok===true)return j;
       return {ok:false,error:(j&&j.error)||('HTTP '+r.status)};
     });
   },function(){return {ok:false,gone:true}});
}
var GONE='Not saved: the gallery server is not answering. Reload the page (same link) and try again.';
function fail(res){
  var m=$('#failmsg');
  m.textContent=(res&&res.gone)?GONE:'Not saved: '+((res&&res.error)||'unknown error')+'. Reload the page (same link) and try again.';
  $('#fail').hidden=false;
}
function clearFail(){$('#fail').hidden=true}

/* heartbeat: tells the person when the server behind this page was restarted or stopped */
var misses=0;
function beat(){
  return fetch('/done?t='+encodeURIComponent(T),{cache:'no-store'}).then(function(r){
    if(!r.ok)throw new Error('HTTP '+r.status);
    misses=0;$('#stale').hidden=true;
  }).then(null,function(){
    misses++;if(misses>=2)$('#stale').hidden=false;
  });
}
function updateBar(){var n=Object.keys(changed).length,c=$('#count');c.textContent=n+' changed';c.className=n?'some':''}
function row(i){return $('.row[data-i="'+i+'"]')}
function same(a,b){return !!a&&!!b&&a.id===b.id&&a.source===b.source}

/* position indicator and arrows */
function pos(r){
  var car=$('.car',r);if(!car)return;
  var vis=$$('.slide',car).filter(function(s){return !s.hidden}),mid=car.scrollLeft+car.clientWidth/2,best=0,d=1e9;
  vis.forEach(function(s,k){var x=Math.abs(s.offsetLeft+s.offsetWidth/2-mid);if(x<d){d=x;best=k}});
  $('.pos',r).textContent=vis.length?(best+1)+' / '+vis.length:'';
  var p=$('.prev',r),n=$('.next',r);
  if(p){p.disabled=car.scrollLeft<4;n.disabled=car.scrollLeft+car.clientWidth>=car.scrollWidth-4}
}
function slideStep(car){var s=$('.slide:not([hidden])',car);return s?s.offsetWidth+12:car.clientWidth}

function paint(i){
  var c=cards[i],ch=c.chosen||{},r=row(i);
  $$('.slide',r).forEach(function(s){
    var cd=c.candidates[+s.dataset.j],on=same(cd,ch),b=$('.use',s);
    s.classList.toggle('on',on);b.disabled=on;b.textContent=on?(cd._gone?'Chosen (hidden; re-run art)':'Chosen'):'Use this art';
  });
  var low=$('.b.low',r);if(low)low.hidden=!ch.lowres;
  var cmp=$('[data-ctl=compare]',r);
  if(cmp){cmp.parentNode.hidden=!same(ch,c.original||ch);$$('button',cmp).forEach(function(x){x.classList.toggle('on',x.dataset.which==='after')})}
}

function choose(i,s){
  var c=cards[i],cand=c.candidates[+s.dataset.j];
  if(same(cand,c.chosen)||s.classList.contains('busy'))return;
  s.classList.add('busy');
  post('/choose',{name:c.name,source:cand.source,id:cand.id}).then(function(res){
    s.classList.remove('busy');
    /* Nothing is changed on the page unless the server confirmed the save. */
    if(!res.ok){fail(res);return}
    clearFail();
    if(c.original===undefined)c.original=c.chosen||{};
    c.chosen=cand;paint(i);sweep(i);
    if(same(c.original,cand))delete changed[c.name];else changed[c.name]={source:cand.source,id:cand.id};
    updateBar();
    apply();
    var car=$('.car',row(i));
    if(car&&car.scrollTo)car.scrollTo({left:Math.max(0,s.offsetLeft-(car.clientWidth-s.offsetWidth)/2)});
    pos(row(i));
    toast('Saved: '+(cand.label||cand.id),true);
  });
}

/* hidden art: drop the slides, but a chosen one stays (marked) until another art is chosen */
function live(c){return c.candidates.filter(function(x){return !x._gone})}
function sweep(k){
  var r=row(k),c=cards[k];
  $$('.slide',r).forEach(function(s){
    var x=c.candidates[+s.dataset.j];if(!x._gone)return;
    if(same(x,c.chosen)){var hb=$('.hidebtn',s),st=$('.hidestrip',s);if(hb)hb.hidden=true;if(st)st.hidden=true}
    else s.remove();
  });
  if(!$$('.slide',r).length){
    var w=$('.carwrap',r),p=$('.pos',r),d=document.createElement('div');
    d.className='none-img';d.textContent='No printable image';
    if(w)w.replaceWith(d);if(p)p.remove();
  }
}
function hideArt(i,s,all){
  var c=cards[i],cand=c.candidates[+s.dataset.j];
  if(s.classList.contains('busy'))return;
  var body={name:c.name,id:cand.id};
  if(all&&cand.render_source)body.source_name=cand.render_source;
  s.classList.add('busy');
  post('/hide',body).then(function(res){
    s.classList.remove('busy');
    if(!res.ok){fail(res);return}
    clearFail();
    cards.forEach(function(cc,k){
      var hit=false;
      cc.candidates.forEach(function(x){
        if(all&&body.source_name?x.render_source===body.source_name:(k===i&&same(x,cand))){x._gone=true;hit=true}
      });
      if(hit){paint(k);sweep(k)}
    });
    apply();
    toast('Hidden',true);
  });
}

function splitSlots(i,n){
  var c=cards[i],ids=live(c).slice(0,n),tot=0,k;
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
    var i=+r.dataset.i,c=cards[i],car=$('.car',r);
    if(car){
      $$('.use',car).forEach(function(b){b.addEventListener('click',function(){choose(i,b.closest('.slide'))})});
      $$('.slide',car).forEach(function(s){
        var hb=$('.hidebtn',s),st=$('.hidestrip',s);
        hb.addEventListener('click',function(){st.hidden=!st.hidden});
        $$('button',st).forEach(function(b){b.addEventListener('click',function(){
          if(b.dataset.act==='cancel'){st.hidden=true;return}
          hideArt(i,s,b.dataset.act==='all');
        })});
      });
      var tick=false;
      car.addEventListener('scroll',function(){if(!tick){tick=true;requestAnimationFrame(function(){tick=false;pos(r)})}},{passive:true});
      ['prev','next'].forEach(function(k,n){var b=$('.'+k,r);b.addEventListener('click',function(){
        car.scrollBy({left:(n?1:-1)*Math.max(slideStep(car),car.clientWidth-slideStep(car)/2),behavior:'smooth'})})});
    }
    var up=$('[data-ctl=upscale]',r);
    if(up)$$('button',up).forEach(function(b){b.addEventListener('click',function(){
      post('/upscale',{name:c.name,mode:b.dataset.mode}).then(function(res){
        if(!res.ok){fail(res);return}
        c.upscale=b.dataset.mode;$$('button',up).forEach(function(x){x.classList.toggle('on',x===b)});
      })})});
    var cp=$('[data-ctl=compare]',r);
    if(cp)$$('button',cp).forEach(function(b){b.addEventListener('click',function(){
      var u=c.compare[b.dataset.which],img=$('.slide.on .large',r);if(!u||!img)return;
      img.src=u;$$('button',cp).forEach(function(x){x.classList.toggle('on',x===b)});
    })});
    var sl=$('[data-ctl=slots]',r);
    if(sl){showSlots(i);$$('button',sl).forEach(function(b){b.addEventListener('click',function(){
      var n=Math.max(1,Math.min(4,live(c).length,Object.keys(c.slots).length+(+b.dataset.d)));
      var slots=splitSlots(i,n);
      post('/slots',{name:c.name,slots:slots}).then(function(res){
        if(!res.ok){fail(res);return}
        c.slots=slots;showSlots(i);
      })})})}
  });
}

function apply(){
  var any=false,q=f.q;
  $$('.row').forEach(function(r){
    var c=cards[+r.dataset.i],nameHit=!q||String(c.name).toLowerCase().indexOf(q)>=0,hit=nameHit;
    $$('.slide',r).forEach(function(s){
      var ok=true,on=s.classList.contains('on');
      if(f.src!=='all'&&s.dataset.style!==f.src)ok=false;
      if(f.sty.length&&!f.sty.some(function(k){return s.dataset.styles.indexOf('|'+k+'|')>=0}))ok=false;
      if(f.noub&&s.dataset.ub==='1')ok=false;
      if(f.std&&s.dataset.std==='0')ok=false;
      var m=nameHit||s.dataset.q.indexOf(q)>=0;if(m&&ok)hit=true;
      s.hidden=!(on||(ok&&m));
    });
    r.hidden=!hit;if(hit){any=true;pos(r)}
  });
  $$('.grp').forEach(function(h){var n=h.nextElementSibling,v=false;while(n&&n.classList.contains('row')){if(!n.hidden)v=true;n=n.nextElementSibling}h.hidden=!v});
  $('#none').hidden=any;
  store('filters',JSON.stringify(f));
}

function chipState(){
  $$('#fchips>button').forEach(function(b){
    var on=b.dataset.key?f.sty.indexOf(b.dataset.key)>=0:b.dataset.src==='all'?(f.src==='all'&&!f.sty.length):b.dataset.src===f.src;
    b.classList.toggle('on',on);b.setAttribute('aria-pressed',on?'true':'false');
  });
}
function filters(){
  try{var s=JSON.parse(store('filters')||'null');if(s&&typeof s==='object')f=Object.assign(f,s)}catch(e){}
  var keys=$$('#fchips>button[data-key]').map(function(b){return b.dataset.key});
  if(f.src!=='render'&&f.src!=='scan')f.src='all';
  f.sty=(Array.isArray(f.sty)?f.sty:[]).filter(function(k){return keys.indexOf(k)>=0});
  f.noub=!!f.noub;f.std=!!f.std;f.q=String(f.q||'');
  chipState();
  $$('#fchips>button').forEach(function(b){
    b.addEventListener('click',function(){
      if(b.dataset.key){var k=b.dataset.key,at=f.sty.indexOf(k);if(at>=0)f.sty.splice(at,1);else f.sty.push(k)}
      else if(b.dataset.src==='all'){f.src='all';f.sty=[]}
      else f.src=b.dataset.src;
      chipState();apply();
    });
  });
  $('#noub').checked=f.noub;$('#std').checked=f.std;$('#q').value=f.q;
  $('#noub').addEventListener('change',function(){f.noub=this.checked;apply()});
  $('#std').addEventListener('change',function(){f.std=this.checked;apply()});
  $('#q').addEventListener('input',function(){f.q=this.value.trim().toLowerCase();apply()});
}

function fragment(){
  return Object.keys(changed).map(function(n){var x=changed[n];
    return '[[choices]]\nname = '+JSON.stringify(n)+'\nsource = '+JSON.stringify(x.source)+'\nid = '+JSON.stringify(x.id)+'\n'}).join('\n');
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
$('#failx').addEventListener('click',clearFail);$('#reload').addEventListener('click',function(){location.reload()});
setInterval(beat,15000);
filters();bind();apply();updateBar();
window.addEventListener('resize',function(){$$('.row').forEach(pos)});
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


def serve(out_path: Path, on_choose, on_upscale=None, on_hide=None, *, bind: str | None = None, port: int = 0,
          token: str | None = None) -> GalleryServer:
    """Serve the page at out_path and write taps back through the callbacks.

    A given `token` is used as is (so a restarted server keeps the same URL); otherwise one is generated.
    """
    out_path = Path(out_path)
    if token is None:
        token = secrets.token_urlsafe(16)
    elif not re.fullmatch(r"[A-Za-z0-9_-]{16,}", token):
        raise ValueError("token must be at least 16 characters of A-Z a-z 0-9 _ -")
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
                elif parts.path == "/hide":
                    ident, source_name = body.get("id"), body.get("source_name")
                    if on_hide is None:
                        return self._json(400, {"ok": False, "error": "hiding is not supported"})
                    if not isinstance(ident, str) or not ident:
                        return self._json(400, {"ok": False, "error": "id is required"})
                    if source_name is not None and (not isinstance(source_name, str) or not source_name):
                        return self._json(400, {"ok": False, "error": "source_name must be a non-empty string"})
                    on_hide(name, ident, source_name)
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
    ap.add_argument("--token", help="use this token (16+ chars of A-Z a-z 0-9 _ -) so a restart keeps the same URL")
    args = ap.parse_args(argv)
    data = json.loads(args.json_file.read_text(encoding="utf-8"))
    out = write(data["deck"], data["cards"], args.json_file.with_suffix(".gallery.html"))

    def on_choose(name, source, ident, slots=None):
        print(f"choose {name!r}: slots={slots}" if slots is not None else f"choose {name!r}: {source} {ident}", file=sys.stderr, flush=True)

    def on_upscale(name, mode):
        print(f"upscale {name!r}: {mode}", file=sys.stderr, flush=True)

    def on_hide(name, ident, source_name=None):
        print(f"hide {name!r}: {ident}" + (f" (all from {source_name!r})" if source_name else ""), file=sys.stderr, flush=True)

    how = "localhost" if args.bind else pick_bind_address()[1]
    server = serve(out, on_choose, on_upscale, on_hide, bind=args.bind, port=args.port, token=args.token)
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
