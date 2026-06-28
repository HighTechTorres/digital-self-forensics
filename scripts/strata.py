#!/usr/bin/env python3
"""
strata.py — render the local extracts into "Strata", an interactive, offline portrait of your
digital life: the layers and eras your machine has quietly recorded, as a single self-contained
HTML page.

Design language (modern data-design principles): high data-ink ratio, small multiples,
compressed typographic hierarchy, purposeful whitespace, a single restrained accent, big tabular
callout numbers, the cross-source findings as the lead, and a scroll-driven narrative reveal. The
data drives the design — sections appear only when their data exists.

100% LOCAL / OFFLINE BY CONSTRUCTION. Interactivity uses two small MIT-licensed libraries that are
**vendored into this skill and inlined into the output** (assets/vendor/): uPlot (charts) and
Scrollama (scroll reveal). Nothing is fetched at runtime — no CDNs, web fonts, trackers, or network
calls of any kind. The page reads only the on-disk extracts and opens with no connection.

PRIVACY (it's a publication layer — conservative like the redacted edition):
  * Personal/inner layer excluded by default. --include-personal folds in note-derived story seeds
    only; raw note bodies are NEVER embedded. Photo GPS is never plotted (counts only).

Usage:
    python3 strata.py EXTRACT_DIR [--out FILE] [--title T] [--subtitle S]
                                  [--accent HEX | --palette NAME] [--include-personal]

Palettes (single accent only): blue (default) · orange · green · yellow · turquoise · red

Reads (any subset; degrades gracefully): app-usage.csv, download-provenance.csv, git-timeline.csv,
installs.csv, shell-tools.csv, saas-account-footprint.txt, launch-agents.txt, photo-exif.csv,
correlations.json, story-seeds.json. Output: strata.html in EXTRACT_DIR (or --out).
"""
import os, sys, csv, json, re, argparse, collections, html, datetime

PALETTES = {"blue": "#2b5fa8", "orange": "#e8743b", "green": "#3aa76d",
            "yellow": "#c9a227", "turquoise": "#1aa6a6", "red": "#c0392b"}

# Audience lenses — who the report is *for* shapes what it leads with, the framing copy, and the
# accent. These are plain audience presets (no jargon in any output); the ordering choices reflect
# what each audience's center of gravity values most: output/achievement leads with results and
# rankings; community leads with the human story; systems leads with how the parts connect;
# holistic leads with the long arc. "professional" is the neutral, balanced default.
LENSES = {
    "professional": {"accent": "blue",
        "subtitle": "An interactive portrait of your digital life",
        "order": ["stats", "findings", "seams", "years", "rhythm", "rankings", "seeds"]},
    "achievement": {"accent": "orange",
        "subtitle": "Your years in output",
        "order": ["stats", "rankings", "years", "findings", "rhythm", "seams", "seeds"]},
    "community": {"accent": "green",
        "subtitle": "The story your data tells",
        "order": ["stats", "seeds", "rhythm", "findings", "years", "rankings", "seams"]},
    "systems": {"accent": "yellow",
        "subtitle": "How the parts of your work connect",
        "order": ["stats", "findings", "seams", "years", "rankings", "rhythm", "seeds"]},
    "holistic": {"accent": "turquoise",
        "subtitle": "The long arc of your digital life",
        "order": ["stats", "findings", "seams", "years", "seeds", "rhythm", "rankings"]},
}
VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "vendor")

# ---------- data loading ----------
def read_csv(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        return list(csv.DictReader(f))

def read_lines(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        return [ln.strip() for ln in f if ln.strip()]

def read_json(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return json.load(f)
    except Exception:
        return {}

def read_asset(name):
    p = os.path.join(VENDOR, name)
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def year_of(s):
    m = re.search(r'(19|20)\d\d', s or "")
    if not m: return None
    y = int(m.group(0)); return y if 1995 <= y <= 2035 else None

def host_of(url):
    u = (url or "").strip()
    # SCP-style git remote: git@github.com:owner/repo.git -> github.com
    m = re.match(r'^[\w.+-]+@([^:/]+):', u)
    if m: return m.group(1).lower()
    u = re.sub(r'^\w+://', '', u)        # strip scheme (https://, ssh://, …)
    u = re.sub(r'^[\w.+-]+@', '', u)     # strip user@ (ssh://git@host/…)
    h = u.split('/')[0].split(':')[0].replace('www.', '')
    return h.lower() if h else ""

def hour_of(row):
    """Hour-of-day for the rhythm chart, robust across extractors: prefer epoch, then ISO 'T08:',
    then any 'HH:MM' (Linux `last` rows look like 'Wed Jun 24 08:13', not ISO)."""
    ep = (row.get("start_epoch", "") or "").strip()
    if ep:
        try: return datetime.datetime.fromtimestamp(int(float(ep))).hour
        except Exception: pass
    s = row.get("start", "") or ""
    m = re.search(r'T(\d\d):', s) or re.search(r'\b(\d{2}):\d{2}\b', s)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23: return h
    return None

def short_app(name):
    return name.split(".")[-1] if "." in name else name

def esc(s):
    return html.escape(str(s), quote=True)

# ---------- inline SVG/HTML primitives (work even with JS disabled) ----------
def svg_columns(pairs, accent, height=120, barw=22, gap=10, pad_top=18):
    pairs = [(str(k), float(v)) for k, v in pairs]
    if not pairs: return ""
    mx = max((v for _, v in pairs), default=0) or 1
    w = len(pairs) * (barw + gap) + gap
    rows = []
    for i, (k, v) in enumerate(pairs):
        x = gap + i * (barw + gap)
        bh = (v / mx) * (height - pad_top - 16)
        y = height - 16 - bh
        lab = str(int(v)) if v == int(v) else f"{v:.1f}"
        rows.append(f'<rect x="{x}" y="{y:.1f}" width="{barw}" height="{bh:.1f}" fill="{accent}"><title>{esc(k)}: {lab}</title></rect>')
        if v: rows.append(f'<text x="{x+barw/2:.1f}" y="{y-3:.1f}" text-anchor="middle" class="cval">{lab}</text>')
        rows.append(f'<text x="{x+barw/2:.1f}" y="{height-4}" text-anchor="middle" class="clbl">{esc(k)}</text>')
    return f'<svg viewBox="0 0 {w} {height}" class="cols" preserveAspectRatio="xMinYMid meet" role="img">{"".join(rows)}</svg>'

def hbars(pairs, accent, maxn=10):
    pairs = [(str(k), float(v)) for k, v in pairs][:maxn]
    if not pairs: return ""
    mx = max((v for _, v in pairs), default=0) or 1
    out = ['<div class="bars">']
    for k, v in pairs:
        pct = max(2, (v / mx) * 100)
        vlabel = f"{int(v)}" if v == int(v) else f"{v:.1f}"
        out.append(f'<div class="bar-row"><div class="k" title="{esc(k)}">{esc(k)}</div>'
                   f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>'
                   f'<div class="v">{vlabel}</div></div>')
    out.append('</div>')
    return "\n".join(out)

def stat(num, label, sub=""):
    subhtml = f'<div class="ssub">{esc(sub)}</div>' if sub else ""
    return f'<div class="stat"><div class="num">{esc(num)}</div><div class="lbl">{esc(label)}</div>{subhtml}</div>'

def section(title, body, sid=""):
    if not body: return ""
    idattr = f' id="{sid}"' if sid else ""
    return f'<section class="section"{idattr}><h2>{esc(title)}</h2>{body}</section>'

def shade(hexcolor, factor):
    """Lighten a hex color toward white by factor 0..1 — for multi-series chart strokes."""
    h = hexcolor.lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    try: r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception: return hexcolor
    r = int(r + (255 - r) * factor); g = int(g + (255 - g) * factor); b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"

# ---------- build ----------
def build(d, opts):
    accent = opts["accent"]
    prov = read_csv(os.path.join(d, "download-provenance.csv"))
    git = read_csv(os.path.join(d, "git-timeline.csv"))
    installs = read_csv(os.path.join(d, "installs.csv"))
    shell = read_csv(os.path.join(d, "shell-tools.csv"))
    appusage = read_csv(os.path.join(d, "app-usage.csv"))
    services = read_lines(os.path.join(d, "saas-account-footprint.txt"))
    autos = read_lines(os.path.join(d, "launch-agents.txt"))
    photos = read_csv(os.path.join(d, "photo-exif.csv"))
    corr = read_json(os.path.join(d, "correlations.json"))
    seedsj = read_json(os.path.join(d, "story-seeds.json"))

    dl_year = collections.Counter(); dl_host = collections.Counter()
    for r in prov:
        y = year_of(r.get("downloaded", ""))
        if y: dl_year[y] += 1
        h = host_of(r.get("page_url", ""))
        if h: dl_host[h] += 1
    commits_total = sum(int(r.get("commits") or 0) for r in git)
    repo_first_year = collections.Counter()
    for r in git:
        y = year_of(r.get("first", ""))
        if y: repo_first_year[y] += 1
    top_repos = sorted(((r.get("repo", ""), int(r.get("commits") or 0)) for r in git), key=lambda t: -t[1])[:10]
    code_hosts = collections.Counter(host_of(r.get("remote", "")) for r in git if r.get("remote"))
    adopt_year = collections.Counter()
    for r in installs:
        y = year_of(r.get("first_seen", ""))
        if y: adopt_year[y] += 1
    cli = [(r.get("command", ""), int(r.get("count") or 0)) for r in shell if r.get("command")][:10]
    app_hours = collections.Counter(); by_hour = collections.Counter()
    for r in appusage:
        try: mins = float(r.get("minutes") or 0)
        except ValueError: mins = 0
        a = short_app(r.get("app", "") or "")
        if a: app_hours[a] += mins
        h = hour_of(r)
        if h is not None: by_hour[h] += mins
    top_apps = [(a, round(m / 60, 1)) for a, m in app_hours.most_common(10)]
    rhythm = [(f"{h:02d}", round(by_hour.get(h, 0) / 60, 1)) for h in range(0, 24, 2)]
    photo_year = collections.Counter(); cameras = collections.Counter(); geotagged = 0
    for r in photos:
        y = year_of(r.get("taken", "")) or year_of(r.get("year", ""))
        if y: photo_year[y] += 1
        if r.get("camera"): cameras[r["camera"]] += 1
        if r.get("lat") and r.get("lon"): geotagged += 1
    all_years = sorted(set(list(dl_year) + list(repo_first_year) + list(adopt_year) + list(photo_year)))
    span = f"{all_years[0]}–{all_years[-1]}" if all_years else ""

    lens = opts.get("lens", "professional")
    lensdef = LENSES.get(lens, LENSES["professional"])
    comp = {}  # named section components; emitted later in lens order
    title = opts["title"] or "Strata"
    subtitle = opts["subtitle"] or lensdef["subtitle"]
    masthead = (f'<header class="masthead"><div class="kicker">{esc(subtitle)}</div>'
                f'<h1>{esc(title)}</h1>'
                f'<div class="sub">{esc(span)} &nbsp;·&nbsp; built from on-disk artifacts &nbsp;·&nbsp; '
                f'processed locally, nothing transmitted</div></header>')

    stats = []
    if commits_total: stats.append(stat(f"{commits_total:,}", "git commits", f"{len(git)} repositories"))
    if dl_year: stats.append(stat(f"{sum(dl_year.values()):,}", "downloads", f"{len(dl_host)} sources"))
    if services: stats.append(stat(f"{len(services):,}", "services", "with saved logins"))
    if installs: stats.append(stat(f"{len(installs):,}", "tools adopted", "by install date"))
    if app_hours: stats.append(stat(f"{round(sum(app_hours.values())/60):,}", "tracked hours", "of app usage"))
    if photos: stats.append(stat(f"{len(photos):,}", "photos dated", f"{geotagged} geotagged" if geotagged else ""))
    if autos: stats.append(stat(f"{len(autos):,}", "automations", "running for you"))
    if cameras: stats.append(stat(f"{len(cameras):,}", "cameras", "across the years"))
    if stats:
        comp["stats"] = f'<section class="section"><div class="stats">{"".join(stats[:8])}</div></section>'

    findings = corr.get("findings", [])
    if findings:
        fhtml = []
        for f in findings[:6]:
            t = f.get("inference") or f.get("id", ""); so = f.get("so_what", ""); conf = f.get("confidence", "")
            fhtml.append(f'<div class="finding"><div class="t">{esc(t)}</div>'
                         + (f'<div class="so">→ {esc(so)}</div>' if so else "")
                         + (f'<div class="tag">{esc(conf)} confidence · {esc(", ".join(f.get("sources", [])))}</div>' if conf else "")
                         + '</div>')
        comp["findings"] = section("The cross-source story", "".join(fhtml))

    seams = corr.get("era_seams", [])
    if seams:
        chips = "".join(f'<div class="seam"><div class="seam-y">{esc(s.get("window",""))}</div>'
                        f'<div class="seam-s">{esc(", ".join(s.get("signals", [])))}</div></div>' for s in seams)
        comp["seams"] = section("Era seams — where the chapters turn", f'<div class="seams">{chips}</div>')

    # The years: interactive uPlot hero if available, else SVG small multiples
    year_series = []
    if dl_year: year_series.append(("Downloads", dl_year))
    if adopt_year: year_series.append(("Tools adopted", adopt_year))
    if repo_first_year: year_series.append(("New repos", repo_first_year))
    if photo_year: year_series.append(("Photos", photo_year))
    hero_js = ""
    if year_series and all_years and opts["have_uplot"]:
        xs = all_years
        udata = [xs] + [[cnt.get(y, 0) for y in xs] for _, cnt in year_series]
        strokes = [accent, shade(accent, 0.45), "#8a8a8a", shade(accent, 0.7)]
        series_defs = [{"label": "Year"}]
        for i, (lbl, _) in enumerate(year_series):
            series_defs.append({"label": lbl, "stroke": strokes[i % len(strokes)], "width": 2,
                                "points": {"show": True, "size": 5}})
        cfg = {"data": udata, "series": series_defs, "accent": accent}
        comp["years"] = section("The shape of your years",
                                '<div id="strata-hero" class="hero"></div>'
                                '<div class="hint">hover the chart — each line is a source, by year</div>',
                                sid="years")
        hero_js = "window.__STRATA__=" + json.dumps(cfg) + ";"
    elif year_series:
        sm = [(lbl, svg_columns(sorted(cnt.items()), accent)) for lbl, cnt in year_series]
        cards = "".join(f'<div class="mult"><div class="mult-t">{esc(t)}</div>{svg}</div>' for t, svg in sm)
        comp["years"] = section("The shape of your years", f'<div class="mults">{cards}</div>', sid="years")

    # daily rhythm always SVG
    if any(v for _, v in rhythm):
        comp["rhythm"] = section("Daily rhythm — hours by time of day",
                                 f'<div class="mult wide"><div class="mult-t">Hours of activity</div>{svg_columns(rhythm, accent, height=140)}</div>')

    rb = []
    if top_apps: rb.append(("Where the hours went (apps)", hbars(top_apps, accent)))
    if cli: rb.append(("Terminal tools", hbars(cli, accent)))
    if top_repos and any(v for _, v in top_repos): rb.append(("Most-committed projects", hbars(top_repos, accent)))
    if dl_host: rb.append(("Top download sources", hbars(dl_host.most_common(10), accent)))
    if cameras: rb.append(("Camera eras", hbars(cameras.most_common(8), accent)))
    if code_hosts: rb.append(("Where you host code", hbars([(k, v) for k, v in code_hosts.most_common(6) if k], accent)))
    if rb:
        cards = "".join(f'<div class="rank"><div class="mult-t">{esc(t)}</div>{b}</div>' for t, b in rb)
        comp["rankings"] = section("Rankings", f'<div class="ranks">{cards}</div>')

    seeds = seedsj.get("seeds", []) if seedsj else []
    if seeds:
        shown = [s for s in seeds if s.get("type") != "note-moment" or opts["include_personal"]]
        cards = [f'<div class="seed"><div class="seed-w">{esc(s.get("when",""))}</div>'
                 f'<div class="seed-t">{esc(s.get("title",""))}</div>'
                 f'<div class="seed-p">{esc(s.get("prompt",""))}</div></div>' for s in shown[:8]]
        if cards:
            comp["seeds"] = section("Story seeds — moments worth keeping", f'<div class="seeds">{"".join(cards)}</div>')

    # assemble in the lens's order (only the components that have data)
    parts = [masthead] + [comp[k] for k in lensdef["order"] if comp.get(k)]

    layers = [n for n, present in [
        ("behavior", appusage), ("downloads", prov), ("git", git), ("tools", installs),
        ("shell", shell), ("services", services), ("photos", photos),
        ("correlations", findings), ("story-seeds", seeds)] if present]
    parts.append(f"""<footer class="foot">
      <div>Read: {esc(", ".join(layers) or "n/a")}. Personal layer: {"included" if opts["include_personal"] else "excluded"}.
      Every number is computed locally from this machine's own artifacts; inference is labeled, the data leads.</div>
      <div class="foot2">Strata · Digital Self-Forensics · self-audit only · 100% local · no network, no trackers · works offline.</div>
    </footer>""")

    return wrap_html(title, accent, "\n".join(parts), hero_js, opts)

def wrap_html(title, accent, body, hero_js, opts):
    css = CSS.replace("ACCENT", accent)
    head = [f'<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            f'<title>{esc(title)}</title>']
    if opts["uplot_css"]: head.append(f'<style>{opts["uplot_css"]}</style>')
    head.append(f'<style>{css}</style>')
    scripts = []
    if opts["uplot_js"]: scripts.append(f'<script>{opts["uplot_js"]}</script>')
    if opts["scrollama_js"]: scripts.append(f'<script>{opts["scrollama_js"]}</script>')
    if hero_js: scripts.append(f'<script>{hero_js}</script>')
    scripts.append(f'<script>{INIT_JS}</script>')
    return ("<!DOCTYPE html><html lang=\"en\"><head>" + "".join(head) + "</head><body>"
            f'<div class="wrap">{body}</div>' + "".join(scripts) + "</body></html>")

CSS = """
*{box-sizing:border-box;}
body{margin:0;background:#fff;color:#1a1a1a;font-family:"Helvetica Neue","Arial Nova",Arial,"Liberation Sans",system-ui,sans-serif;font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;}
.wrap{max-width:1080px;margin:0 auto;padding:60px 28px 100px;}
.sub,.lbl,.kicker,.k,.v,.cval,.clbl,.tag,.seam-y,.seam-s,.seed-w,.foot,.hint{font-family:"SF Mono","JetBrains Mono",Menlo,Consolas,"Liberation Mono",monospace;}
.masthead{border-bottom:3px solid #1a1a1a;padding-bottom:20px;}
.kicker{font-size:11px;text-transform:uppercase;letter-spacing:.18em;color:ACCENT;margin-bottom:14px;}
.masthead h1{font-size:clamp(40px,8vw,76px);font-weight:800;letter-spacing:-.03em;line-height:.98;margin:0;text-transform:uppercase;}
.sub{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:#8a8a8a;margin-top:14px;}
.section{margin-top:58px;}
.section>h2{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.16em;color:ACCENT;border-bottom:1px solid #e6e6e6;padding-bottom:9px;margin:0 0 26px;}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#e6e6e6;border:1px solid #e6e6e6;}
.stat{background:#fff;padding:22px 18px;}
.stat .num{font-size:clamp(28px,3.4vw,42px);font-weight:800;letter-spacing:-.03em;line-height:1;font-variant-numeric:tabular-nums;}
.stat .lbl{font-size:10px;text-transform:uppercase;letter-spacing:.07em;margin-top:10px;}
.stat .ssub{font-size:10px;color:#9a9a9a;margin-top:3px;}
.finding{border-left:3px solid ACCENT;padding:2px 0 2px 18px;margin-bottom:22px;}
.finding .t{font-weight:600;font-size:16.5px;line-height:1.35;}
.finding .so{color:#5a5a5a;font-size:13.5px;margin-top:6px;}
.finding .tag{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#9a9a9a;margin-top:7px;}
.seams{display:flex;flex-wrap:wrap;gap:14px;}
.seam{border:1px solid #e6e6e6;border-top:3px solid ACCENT;padding:12px 16px;min-width:120px;}
.seam-y{font-size:20px;font-weight:800;}
.seam-s{font-size:10.5px;color:#8a8a8a;margin-top:5px;}
.hero{width:100%;min-height:300px;}
.hint{font-size:10.5px;color:#9a9a9a;text-transform:uppercase;letter-spacing:.06em;margin-top:8px;}
.mults{display:grid;grid-template-columns:repeat(2,1fr);gap:30px 36px;}
.mult.wide{grid-column:1/-1;}
.mult-t{font-size:12px;font-weight:700;margin-bottom:12px;}
svg.cols{width:100%;height:auto;display:block;overflow:visible;}
svg.cols .cval{font-family:"SF Mono",Menlo,monospace;font-size:8.5px;fill:#9a9a9a;}
svg.cols .clbl{font-family:"SF Mono",Menlo,monospace;font-size:8.5px;fill:#6a6a6a;}
.ranks{display:grid;grid-template-columns:repeat(2,1fr);gap:30px 36px;}
.bars{display:flex;flex-direction:column;gap:7px;}
.bar-row{display:grid;grid-template-columns:130px 1fr 46px;align-items:center;gap:12px;font-size:12px;}
.bar-row .k{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.bar-track{background:#f0f0f0;height:13px;}
.bar-fill{background:ACCENT;height:13px;min-width:2px;}
.bar-row .v{text-align:right;color:#9a9a9a;font-variant-numeric:tabular-nums;}
.seeds{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;}
.seed{border:1px solid #e6e6e6;padding:16px 18px;}
.seed-w{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:ACCENT;}
.seed-t{font-weight:700;font-size:15px;margin:6px 0 8px;}
.seed-p{font-size:13px;color:#5a5a5a;}
.foot{margin-top:80px;border-top:1px solid #e6e6e6;padding-top:18px;font-size:11px;color:#9a9a9a;line-height:1.6;}
.foot2{margin-top:8px;}
.u-legend{font-family:"SF Mono",Menlo,monospace;font-size:11px;}
body.js .section{opacity:0;transform:translateY(16px);transition:opacity .55s ease,transform .55s ease;}
body.js .section.in{opacity:1;transform:none;}
@media(max-width:720px){.stats{grid-template-columns:repeat(2,1fr);}.mults,.ranks,.seeds{grid-template-columns:1fr;}.bar-row{grid-template-columns:104px 1fr 40px;}}
@media print{body.js .section{opacity:1!important;transform:none!important;}.wrap{padding:0;}.section{margin-top:30px;break-inside:avoid;}}
"""

# scroll-reveal + interactive hero chart init (runs only if the vendored libs were inlined)
INIT_JS = """
(function(){
  try{
    if(typeof scrollama!=='undefined'){
      var sc=scrollama();
      sc.setup({step:'.section',offset:0.85,once:true}).onStepEnter(function(r){r.element.classList.add('in');});
      document.body.classList.add('js');  // only hide-then-reveal AFTER setup succeeds
      window.addEventListener('resize',function(){sc.resize();});
    }
  }catch(e){ document.body.classList.remove('js'); }  // never leave sections hidden
  try{
    var cfg=window.__STRATA__;
    if(cfg && typeof uPlot!=='undefined'){
      var el=document.getElementById('strata-hero');
      if(el){
        var draw=function(){
          el.innerHTML='';
          var w=el.clientWidth||640;
          var opts={width:w,height:300,
            scales:{x:{time:false}},
            axes:[{values:function(u,v){return v.map(function(x){return String(Math.round(x));});},
                   grid:{show:false}},
                  {grid:{stroke:'#eee'}}],
            legend:{show:true},
            cursor:{points:{size:7}},
            series:cfg.series};
          window.__strataU=new uPlot(opts,cfg.data,el);
        };
        draw();
        window.addEventListener('resize',function(){
          if(window.__strataU){window.__strataU.setSize({width:el.clientWidth||640,height:300});}
        });
      }
    }
  }catch(e){}
})();
"""

def main():
    ap = argparse.ArgumentParser(description="Render extracts into Strata — an interactive offline data portrait.")
    ap.add_argument("extract_dir")
    ap.add_argument("--out", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--accent", default="")
    ap.add_argument("--palette", default="", choices=list(PALETTES.keys()))
    ap.add_argument("--lens", default="professional", choices=list(LENSES.keys()),
                    help="Audience preset — shapes what the report leads with, its framing, and accent: "
                         "professional (default) · achievement · community · systems · holistic.")
    ap.add_argument("--include-personal", action="store_true",
                    help="Fold in note-derived story seeds (raw note bodies are never embedded).")
    a = ap.parse_args()
    if not os.path.isdir(a.extract_dir):
        print(f"ERROR: extract dir not found: {a.extract_dir}"); sys.exit(2)
    # accent precedence: explicit --accent > --palette > the lens's accent > default blue
    lens_accent = PALETTES.get(LENSES.get(a.lens, {}).get("accent", "blue"), PALETTES["blue"])
    accent = a.accent.strip() or (PALETTES[a.palette] if a.palette else lens_accent)
    if not re.match(r'^#[0-9a-fA-F]{3,8}$', accent):
        print(f"ERROR: --accent must be a hex color (got {accent!r})"); sys.exit(2)

    uplot_js = read_asset("uPlot.iife.min.js"); uplot_css = read_asset("uPlot.min.css")
    scrollama_js = read_asset("scrollama.min.js")
    opts = {"accent": accent, "title": a.title, "subtitle": a.subtitle, "lens": a.lens,
            "include_personal": a.include_personal,
            "uplot_js": uplot_js, "uplot_css": uplot_css, "scrollama_js": scrollama_js,
            "have_uplot": bool(uplot_js)}
    doc = build(a.extract_dir, opts)
    out = a.out or os.path.join(a.extract_dir, "strata.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    kb = round(len(doc) / 1024, 1)
    interactive = "interactive (uPlot + scroll reveal)" if uplot_js else "static SVG (vendored libs not found)"
    print(f"Strata written to: {out}  ({kb} KB, self-contained, offline)")
    print(f"  lens {a.lens} · accent {accent} · {interactive} · personal layer {'included' if a.include_personal else 'excluded'}")

if __name__ == "__main__":
    main()
