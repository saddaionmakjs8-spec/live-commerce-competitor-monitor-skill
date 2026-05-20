#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path


CSV_NAMES = {
    "session": "session_meta.csv",
    "recording": "recording_chunks.csv",
    "metrics": "metric_samples.csv",
    "speech": "speech_segments.csv",
    "products": "product_events.csv",
    "comments": "comment_events.csv",
    "orders": "order_signals.csv",
    "shots": "screenshot_events.csv",
    "loops": "loop_markers.csv",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def find_csv_dir(root: Path) -> Path:
    candidates = [
        root / "_internal_技术底稿" / "原始报表csv",
        root / "report",
        root / "report-v2",
        root / "原始报表csv",
    ]
    for candidate in candidates:
        if candidate.exists() and any(candidate.glob("*.csv")):
            return candidate
    return root


def md_section(md: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)", re.S | re.M)
    match = pattern.search(md)
    return match.group(1).strip() if match else ""


def bullets(text: str) -> list[str]:
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            result.append(stripped[2:].strip())
    return result


def paragraphs(text: str) -> list[str]:
    result: list[str] = []
    buf: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if buf:
                result.append(" ".join(buf))
                buf = []
            continue
        if stripped.startswith("#") or stripped.startswith("- "):
            continue
        buf.append(stripped)
    if buf:
        result.append(" ".join(buf))
    return result


def speech_modules(md: str) -> list[dict[str, str]]:
    block = md_section(md, "主要话术模块")
    modules: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in block.splitlines():
        stripped = line.strip()
        match = re.match(r"^###\s+\d+\.\s*(.+)$", stripped)
        if match:
            if current:
                modules.append(current)
            current = {"title": match.group(1), "quote": "", "effect": ""}
            continue
        if current is None:
            continue
        if stripped.startswith("代表话术："):
            current["quote"] = stripped.replace("代表话术：", "", 1).strip()
        elif stripped.startswith("作用："):
            current["effect"] = stripped.replace("作用：", "", 1).strip()
    if current:
        modules.append(current)
    return modules


def time_only(value: str) -> str:
    match = re.search(r"T(\d{2}:\d{2}:\d{2})", value or "")
    return match.group(1) if match else (value or "")


def rel_from(path: Path, base: Path) -> str:
    return os.path.relpath(path, base).replace(os.sep, "/")


def first_existing(patterns: list[str], root: Path) -> Path | None:
    for pattern in patterns:
        found = sorted(root.glob(pattern))
        if found:
            return found[0]
    return None


def evidence_bytes(root: Path) -> int:
    patterns = [
        "01_完整录屏_*",
        "04_关键截图/*",
        "02_直播逐字稿_带时间轴.xlsx",
        "03_结构化数据总表.xlsx",
        "raw/screen-recording-*.mov",
        "raw/screenshots/*",
    ]
    total = 0
    seen: set[Path] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                total += path.stat().st_size
    return total


def collect_screenshots(root: Path, html_dir: Path) -> list[dict[str, str]]:
    shot_dirs = [root / "04_关键截图", root / "raw" / "screenshots", root / "_internal_技术底稿" / "raw" / "screenshots"]
    shot_dir = next((p for p in shot_dirs if p.exists()), None)
    if not shot_dir:
        return []
    shots = []
    for path in sorted(shot_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        stem = path.stem
        match = re.match(r"^(\d+)分(\d+)秒_(.+)$", stem)
        if match:
            timecode = f"00:{int(match.group(1)):02d}:{int(match.group(2)):02d}"
            title = match.group(3).replace("_", " ")
        else:
            timecode = ""
            title = stem.replace("_", " ")
        shots.append({"timecode": timecode, "title": title, "file": rel_from(path, html_dir)})
    return shots


def build_data(root: Path, html_path: Path, title: str) -> dict:
    html_dir = html_path.parent
    csv_dir = find_csv_dir(root)
    tables = {key: read_csv(csv_dir / name) for key, name in CSV_NAMES.items()}

    for rows, key in [
        (tables["metrics"], "timestamp"),
        (tables["speech"], "start_time"),
        (tables["products"], "timestamp"),
        (tables["comments"], "timestamp"),
        (tables["orders"], "timestamp"),
        (tables["loops"], "timestamp"),
    ]:
        for row in rows:
            row["_time"] = time_only(row.get(key, ""))

    summary_md = read_text(first_existing(["00_先看这个_本次结论.md", "summary.md", "report/summary.md"], root) or Path())
    analysis_md = read_text(first_existing(["05_话术分析报告.md", "report/summary.md", "report-v2/summary.md"], root) or Path())

    viewer_values: list[int] = []
    hot_values: list[int] = []
    for row in tables["metrics"]:
        try:
            viewer_values.append(int(float(row.get("online_viewers") or 0)))
        except ValueError:
            pass
        try:
            hot_values.append(int(float(row.get("hot_sale_count") or 0)))
        except ValueError:
            pass

    recording_file = first_existing(["01_完整录屏_*.mov", "raw/screen-recording-*.mov", "raw/*.mov"], root)
    transcript_file = first_existing(["02_直播逐字稿_带时间轴.xlsx"], root)
    structured_file = first_existing(["03_结构化数据总表.xlsx"], root)
    summary_file = first_existing(["00_先看这个_本次结论.md"], root)
    analysis_file = first_existing(["05_话术分析报告.md"], root)

    def optional_rel(path: Path | None) -> str:
        return rel_from(path, html_dir) if path and path.exists() else ""

    kpis = {
        "viewer_start": viewer_values[0] if viewer_values else None,
        "viewer_end": viewer_values[-1] if viewer_values else None,
        "viewer_min": min(viewer_values) if viewer_values else None,
        "viewer_max": max(viewer_values) if viewer_values else None,
        "hot_start": hot_values[0] if hot_values else None,
        "hot_end": hot_values[-1] if hot_values else None,
        "hot_delta": hot_values[-1] - hot_values[0] if len(hot_values) >= 2 else None,
        "speech_count": len(tables["speech"]),
        "screenshot_count": 0,
        "product_switch_count": len(tables["products"]),
        "order_signal_count": len(tables["orders"]),
    }

    screenshots = collect_screenshots(root, html_dir)
    kpis["screenshot_count"] = len(screenshots)

    return {
        "title": title,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "root_name": root.name,
        "evidence_bytes": evidence_bytes(root),
        "session": tables["session"][0] if tables["session"] else {},
        "recording": tables["recording"][0] if tables["recording"] else {},
        "files": {
            "recording": optional_rel(recording_file),
            "transcript_xlsx": optional_rel(transcript_file),
            "structured_xlsx": optional_rel(structured_file),
            "summary_md": optional_rel(summary_file),
            "analysis_md": optional_rel(analysis_file),
            "screenshots_dir": rel_from(root / "04_关键截图", html_dir) + "/" if (root / "04_关键截图").exists() else "",
        },
        "kpis": kpis,
        "summary": {
            "conclusion": paragraphs(md_section(summary_md, "先看结论")),
            "data_scope": bullets(md_section(summary_md, "本次数据口径")),
            "key_numbers": bullets(md_section(summary_md, "关键数字")),
            "core_method": paragraphs(md_section(analysis_md, "核心打法")),
            "relation": bullets(md_section(analysis_md, "话术与数据关系")),
            "learn": bullets(md_section(analysis_md, "可以借鉴")),
            "caution": bullets(md_section(analysis_md, "不建议照搬")),
        },
        "speech_modules": speech_modules(analysis_md),
        "metrics": tables["metrics"],
        "speech_segments": tables["speech"],
        "product_events": tables["products"],
        "comment_events": tables["comments"],
        "order_signals": tables["orders"],
        "loop_markers": tables["loops"],
        "screenshots": screenshots,
    }


def html_template(data_script: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>直播分析可视化看板</title>
  <style>
    :root{{--bg:#f6f8fb;--panel:#fff;--text:#17202a;--muted:#667085;--line:#d8e0ea;--cyan:#0aa6b5;--amber:#d88a16;--green:#1f9d68;--side:#101820;--shadow:0 18px 50px rgba(15,23,42,.08);--mono:"SFMono-Regular","Menlo","Consolas",monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif}}
    *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);line-height:1.55;letter-spacing:0}} a{{color:inherit}}
    .page{{display:grid;grid-template-columns:260px minmax(0,1fr);min-height:100vh}} .side{{position:sticky;top:0;height:100vh;padding:28px 18px;background:var(--side);color:#fff;border-right:1px solid rgba(255,255,255,.08)}} .brand{{display:flex;gap:12px;align-items:center;margin-bottom:28px}} .mark{{width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,var(--cyan),#51c0a6);box-shadow:0 0 0 6px rgba(10,166,181,.14)}} .brand h1{{font-size:16px;line-height:1.3;margin:0}} .brand p{{margin:4px 0 0;color:#a9b5c5;font-size:12px}} .nav{{display:grid;gap:6px}} .nav a{{text-decoration:none;color:#cbd5e1;padding:10px 12px;border-radius:10px;font-size:13px}} .nav a:hover{{background:rgba(255,255,255,.08);color:#fff}} .side-foot{{position:absolute;left:18px;right:18px;bottom:22px;color:#94a3b8;font-size:12px}} .mode{{font-family:var(--mono);font-size:11px;color:#7dd3fc;background:rgba(14,165,233,.12);padding:6px 8px;border-radius:999px;display:inline-block;margin-top:8px}}
    main{{padding:34px 42px 60px;max-width:1500px}} .hero{{padding:30px;border-radius:24px;background:linear-gradient(135deg,#fff 0%,#eef7f8 100%);box-shadow:var(--shadow);border:1px solid #e1e8f0}} .eyebrow{{font-size:12px;color:var(--cyan);font-weight:700;text-transform:uppercase;letter-spacing:.08em}} h2{{font-size:34px;line-height:1.16;margin:10px 0 12px;letter-spacing:0}} .hero p{{max-width:980px;margin:0;color:#3b4756;font-size:16px}} .meta{{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}} .pill{{display:inline-flex;gap:7px;align-items:center;padding:8px 11px;background:#fff;border:1px solid var(--line);border-radius:999px;color:#344054;font-size:13px}} .dot{{width:7px;height:7px;border-radius:50%;background:var(--cyan)}} section{{margin-top:28px}} .head{{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;margin-bottom:14px}} .head h3{{margin:0;font-size:22px}} .head p{{margin:0;color:var(--muted);font-size:13px}} .grid{{display:grid;gap:16px}} .kpis{{grid-template-columns:repeat(6,minmax(0,1fr))}} .panel{{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:0 10px 28px rgba(15,23,42,.05);padding:18px}} .kpi .label{{font-size:12px;color:var(--muted)}} .kpi .value{{font-family:var(--mono);font-size:28px;line-height:1.15;margin-top:8px;color:#0b1220}} .kpi .sub{{font-size:12px;color:var(--muted);margin-top:6px}} .two{{grid-template-columns:minmax(0,1.1fr) minmax(360px,.9fr)}} .three{{grid-template-columns:repeat(3,minmax(0,1fr))}}
    ul.list{{padding:0;margin:0;display:grid;gap:10px;list-style:none}} .list li{{padding-left:18px;position:relative;color:#344054}} .list li:before{{content:"";position:absolute;left:0;top:.72em;width:7px;height:7px;border-radius:50%;background:var(--cyan)}} .video{{background:#0f1720;border-radius:18px;overflow:hidden;border:1px solid #263445}} .video video{{display:block;width:100%;aspect-ratio:16/9;background:#0f1720}} .links{{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}} .links a{{font-size:13px;text-decoration:none;border:1px solid var(--line);padding:8px 10px;border-radius:10px;background:#fff;color:#344054}} .chart-wrap{{height:300px}} .chart svg{{width:100%;height:100%;display:block}} .legend{{display:flex;gap:14px;align-items:center;margin-top:10px;color:var(--muted);font-size:12px}} .legend span{{display:inline-flex;align-items:center;gap:6px}} .legend i{{width:18px;height:3px;border-radius:4px;display:inline-block}}
    .event{{display:grid;grid-template-columns:92px 118px minmax(0,1fr);gap:12px;align-items:start;padding:13px 14px;border:1px solid var(--line);border-radius:14px;background:#fff;margin-bottom:12px}} .event-time{{font-family:var(--mono);color:var(--cyan);font-size:13px}} .event-kind{{font-size:12px;border-radius:999px;padding:4px 8px;text-align:center;background:#eef3f8;color:#344054}} .event-title{{font-weight:700}} .event-text{{font-size:13px;color:var(--muted);margin-top:4px}} .kind-speech{{background:#e6f7f9;color:#087b86}} .kind-product{{background:#fff2dc;color:#9a5c04}} .kind-order{{background:#eaf7ef;color:#0f6f45}} .kind-comment{{background:#f1ecff;color:#6941c6}}
    .quote{{border-left:3px solid var(--cyan);padding:10px 12px;background:#f4fbfc;border-radius:0 10px 10px 0;color:#1f2937}} .effect{{font-size:13px;color:var(--muted);margin-top:10px}} .shots{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}} figure{{margin:0;overflow:hidden;padding:0}} figure img{{width:100%;aspect-ratio:16/10;object-fit:cover;display:block;background:#e5e7eb}} figcaption{{padding:12px}} .shot-time{{font-family:var(--mono);font-size:12px;color:var(--cyan);font-weight:700}} .shot-title{{font-size:13px;color:#344054;margin-top:4px}} .table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:14px;background:#fff}} table{{width:100%;border-collapse:collapse;min-width:760px}} th,td{{text-align:left;border-bottom:1px solid #edf1f5;padding:10px 12px;font-size:13px;vertical-align:top}} th{{background:#f8fafc;color:#475467;font-weight:700;position:sticky;top:0}} td{{color:#344054}} .note{{color:var(--muted);font-size:13px}} .empty{{padding:16px;color:var(--muted);background:#fff;border:1px dashed var(--line);border-radius:14px}} .footer{{margin-top:34px;color:#667085;font-size:12px;text-align:center}}
    @media (max-width:1180px){{.page{{grid-template-columns:1fr}}.side{{position:relative;height:auto}}.side-foot{{position:static;margin-top:20px}}main{{padding:24px}}.kpis{{grid-template-columns:repeat(3,1fr)}}.two,.three{{grid-template-columns:1fr}}.shots{{grid-template-columns:repeat(2,1fr)}}}} @media (max-width:680px){{main{{padding:16px}}h2{{font-size:26px}}.kpis{{grid-template-columns:repeat(2,1fr)}}.event{{grid-template-columns:1fr}}.shots{{grid-template-columns:1fr}}.head{{display:block}}}}
  </style>
</head>
<body>
  <div class="page"><aside class="side"><div class="brand"><div class="mark"></div><div><h1>直播竞品分析看板</h1><p>Local live monitor</p></div></div><nav class="nav"><a href="#overview">总览</a><a href="#evidence">录屏与证据</a><a href="#metrics">人数与热卖</a><a href="#timeline">时间线</a><a href="#speech">话术模块</a><a href="#relation">关系分析</a><a href="#screenshots">关键截图</a><a href="#raw">结构化明细</a></nav><div class="side-foot"><div>本地数据模式</div><span class="mode" id="mode">loading</span></div></aside>
  <main><header class="hero" id="overview"><div class="eyebrow">Local HTML Dashboard</div><h2 id="title">直播分析可视化看板</h2><p id="conclusion">正在载入本地数据...</p><div class="meta" id="meta"></div></header><section><div class="grid kpis" id="kpis"></div></section>
  <section class="grid two" id="evidence"><div><div class="head"><h3>录屏证据</h3><p>引用本地视频文件，不写入 HTML</p></div><div class="video"><video id="video" controls preload="metadata"></video></div><div class="links" id="links"></div></div><div><div class="head"><h3>核心判断</h3><p>从报告中抽取</p></div><div class="panel"><ul class="list" id="keyNumbers"></ul></div><div class="panel" style="margin-top:14px"><h4 style="margin:0 0 10px">打法主轴</h4><div id="coreMethod" class="note"></div></div></section>
  <section id="metrics"><div class="head"><h3>在线人数与热卖变化</h3><p>横轴为采样时间，纵轴按各自区间归一化</p></div><div class="panel chart"><div class="chart-wrap" id="chart"></div><div class="legend"><span><i style="background:var(--cyan)"></i>在线人数</span><span><i style="background:var(--amber)"></i>热卖数</span></div></div></section>
  <section id="timeline"><div class="head"><h3>直播时间线</h3><p>商品、话术、评论、下单信号合并排序</p></div><div id="timelineList"></div></section>
  <section id="speech"><div class="head"><h3>高价值话术模块</h3><p>按销售意图拆解</p></div><div class="grid three" id="speechModules"></div></section>
  <section id="relation" class="grid two"><div><div class="head"><h3>话术与数据关系</h3><p>只做时间接近判断，不夸大因果</p></div><div class="panel"><ul class="list" id="relationList"></ul></div></div><div><div class="head"><h3>借鉴与边界</h3><p>适合迁移到自家直播间的部分</p></div><div class="panel"><h4 style="margin:0 0 8px">可以借鉴</h4><ul class="list" id="learnList"></ul></div><div class="panel" style="margin-top:14px"><h4 style="margin:0 0 8px">不要照搬</h4><ul class="list" id="cautionList"></ul></div></div></section>
  <section id="screenshots"><div class="head"><h3>关键截图索引</h3><p>画面产生变化时留证</p></div><div class="shots" id="shotGrid"></div></section>
  <section id="raw"><div class="head"><h3>结构化明细</h3><p>来自本地 CSV / JSONL 生成的数据</p></div><div class="grid two"><div><h4>话术片段</h4><div class="table-wrap" id="speechTable"></div></div><div><h4>下单与评论信号</h4><div class="table-wrap" id="signalTable"></div></div></div></section><div class="footer" id="footer"></div></main></div>
  {data_script}
  <script>
    const data = window.__LIVE_MONITOR_DATA__;
    const $ = (id) => document.getElementById(id);
    const esc = (v) => String(v ?? '').replace(/[&<>"]/g, s => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[s]));
    const rich = (v) => esc(v).replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
    const url = (p) => p ? encodeURI(p).replace(/#/g,'%23') : '';
    const trim = (v,n=120) => {{ v=String(v??''); return v.length>n ? v.slice(0,n-1)+'…' : v; }};
    const list = (id, arr) => {{ $(id).innerHTML = (arr&&arr.length) ? arr.map(x=>`<li>${{rich(x)}}</li>`).join('') : '<li>暂无数据</li>'; }};
    function meta(){{ const s=data.session||{{}}, r=data.recording||{{}}; const items=[s.platform,s.account_name,s.session_date,r.duration_seconds?Math.round(Number(r.duration_seconds))+' 秒':'',s.capture_method,s.screen_scope].filter(Boolean); $('meta').innerHTML=items.map(x=>`<span class="pill"><i class="dot"></i>${{esc(x)}}</span>`).join(''); $('mode').textContent=data.render_mode||'inline'; $('title').textContent=data.title; $('conclusion').innerHTML=(data.summary.conclusion||[]).map(rich).join('<br>'); $('coreMethod').innerHTML=(data.summary.core_method||[]).map(p=>`<p>${{esc(p)}}</p>`).join(''); $('footer').textContent=`生成时间：${{data.generated_at}} ｜ 数据目录：${{data.root_name}}`; }}
    function kpis(){{ const k=data.kpis||{{}}; const defs=[['在线开始',k.viewer_start,'开场采样'],['在线峰值',k.viewer_max,`最低 ${{k.viewer_min??'-'}}`],['在线结束',k.viewer_end,'结束采样'],['热卖增量',k.hot_delta==null?'-':`+${{k.hot_delta}}`,`${{k.hot_start??'-'}} → ${{k.hot_end??'-'}}`],['话术片段',k.speech_count,'结构化分段'],['关键截图',k.screenshot_count,'画面变化留证']]; $('kpis').innerHTML=defs.map(([a,b,c])=>`<div class="panel kpi"><div class="label">${{esc(a)}}</div><div class="value">${{esc(b??'-')}}</div><div class="sub">${{esc(c)}}</div></div>`).join(''); }}
    function files(){{ const f=data.files||{{}}; $('video').src=url(f.recording); const links=[['完整录屏',f.recording],['逐字稿 Excel',f.transcript_xlsx],['结构化总表 Excel',f.structured_xlsx],['结论 Markdown',f.summary_md],['话术报告 Markdown',f.analysis_md],['截图文件夹',f.screenshots_dir]].filter(x=>x[1]); $('links').innerHTML=links.map(([a,b])=>`<a href="${{url(b)}}" target="_blank">${{esc(a)}}</a>`).join(''); list('keyNumbers',data.summary.key_numbers); }}
    function chart(){{ const rows=data.metrics||[]; if(!rows.length){{ $('chart').innerHTML='<div class="empty">暂无指标采样</div>'; return; }} const W=1000,H=280,pad=34; const nums=(field)=>rows.map(r=>Number(r[field])).filter(Number.isFinite); const vs=nums('online_viewers'), hs=nums('hot_sale_count'); const vMin=Math.min(...vs), vMax=Math.max(...vs), hMin=Math.min(...hs), hMax=Math.max(...hs); const x=i=>pad+(W-pad*2)*(rows.length===1?.5:i/(rows.length-1)); const y=(val,min,max)=>H-pad-(H-pad*2)*((Number(val)-min)/((max-min)||1)); const pts=(field,min,max)=>rows.map((r,i)=>`${{x(i)}},${{y(r[field],min,max)}}`).join(' '); const dots=rows.map((r,i)=>`<circle cx="${{x(i)}}" cy="${{y(r.online_viewers,vMin,vMax)}}" r="4" fill="var(--cyan)"><title>${{r._time}} 在线 ${{r.online_viewers}}</title></circle><circle cx="${{x(i)}}" cy="${{y(r.hot_sale_count,hMin,hMax)}}" r="4" fill="var(--amber)"><title>${{r._time}} 热卖 ${{r.hot_sale_count}}</title></circle><text x="${{x(i)}}" y="${{H-6}}" text-anchor="middle" font-size="11" fill="#667085">${{esc((r._time||'').slice(3))}}</text>`).join(''); $('chart').innerHTML=`<svg viewBox="0 0 ${{W}} ${{H}}"><line x1="${{pad}}" y1="${{H-pad}}" x2="${{W-pad}}" y2="${{H-pad}}" stroke="#d8e0ea"/><line x1="${{pad}}" y1="${{pad}}" x2="${{pad}}" y2="${{H-pad}}" stroke="#d8e0ea"/><polyline points="${{pts('online_viewers',vMin,vMax)}}" fill="none" stroke="var(--cyan)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="${{pts('hot_sale_count',hMin,hMax)}}" fill="none" stroke="var(--amber)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>${{dots}}<text x="${{pad}}" y="20" font-size="12" fill="#667085">在线 ${{vMin}}-${{vMax}} ｜ 热卖 ${{hMin}}-${{hMax}}</text></svg>`; }}
    function timeline(){{ const ev=[]; (data.product_events||[]).forEach(r=>ev.push({{t:r.timestamp,time:r._time,kind:'product',label:'商品切换',title:`${{r.link_number||''}}号 ${{r.product_title||''}}`,text:`价格 ${{r.price||'-'}} ｜ ${{r.claim_text||''}}`}})); (data.speech_segments||[]).forEach(r=>ev.push({{t:r.start_time,time:r._time,kind:'speech',label:r.speech_type||'话术',title:r.sales_intent||r.speech_type||'主播话术',text:r.quote||''}})); (data.order_signals||[]).forEach(r=>ev.push({{t:r.timestamp,time:r._time,kind:'order',label:'下单信号',title:r.signal_kind||'order',text:r.signal_text||''}})); (data.comment_events||[]).forEach(r=>ev.push({{t:r.timestamp,time:r._time,kind:'comment',label:r.comment_type||'评论',title:r.commenter||'评论区',text:r.comment_text||''}})); ev.sort((a,b)=>String(a.t).localeCompare(String(b.t))); $('timelineList').innerHTML=ev.map(e=>`<div class="event"><div class="event-time">${{esc(e.time)}}</div><div class="event-kind kind-${{e.kind}}">${{esc(e.label)}}</div><div><div class="event-title">${{esc(trim(e.title,80))}}</div><div class="event-text">${{esc(trim(e.text,180))}}</div></div></div>`).join('')||'<div class="empty">暂无时间线数据</div>'; }}
    function speech(){{ $('speechModules').innerHTML=(data.speech_modules||[]).map(m=>`<div class="panel"><h4 style="margin:0 0 10px">${{esc(m.title)}}</h4><div class="quote">${{esc(m.quote)}}</div><div class="effect">${{esc(m.effect)}}</div></div>`).join('')||'<div class="empty">暂无话术模块</div>'; list('relationList',data.summary.relation); list('learnList',data.summary.learn); list('cautionList',data.summary.caution); }}
    function shots(){{ $('shotGrid').innerHTML=(data.screenshots||[]).map(s=>`<figure class="panel"><a href="${{url(s.file)}}" target="_blank"><img loading="lazy" src="${{url(s.file)}}" alt="${{esc(s.title)}}"></a><figcaption><div class="shot-time">${{esc(s.timecode)}}</div><div class="shot-title">${{esc(s.title)}}</div></figcaption></figure>`).join('')||'<div class="empty">暂无截图</div>'; }}
    function table(rows, cols){{ if(!rows||!rows.length)return'<div class="empty">暂无数据</div>'; return `<table><thead><tr>${{cols.map(c=>`<th>${{esc(c[1])}}</th>`).join('')}}</tr></thead><tbody>${{rows.map(r=>`<tr>${{cols.map(c=>`<td>${{esc(trim(r[c[0]],c[2]||160))}}</td>`).join('')}}</tr>`).join('')}}</tbody></table>`; }}
    function tables(){{ $('speechTable').innerHTML=table(data.speech_segments,[['_time','时间',20],['speech_type','类型',40],['sales_intent','销售意图',70],['quote','原话/整理话术',180],['confidence','置信度',30]]); const signals=[...(data.order_signals||[]).map(r=>({{...r,type:'下单信号',text:r.signal_text}})),...(data.comment_events||[]).map(r=>({{...r,type:'评论',text:r.comment_text}}))].sort((a,b)=>String(a.timestamp).localeCompare(String(b.timestamp))); $('signalTable').innerHTML=table(signals,[['_time','时间',20],['type','类型',30],['signal_kind','信号/评论类型',60],['text','内容',180],['confidence','置信度',30]]); }}
    function boot(){{ if(!data){{document.body.innerHTML='<div style="padding:40px;font-family:sans-serif">没有载入本地数据。</div>';return}} meta(); kpis(); files(); chart(); timeline(); speech(); shots(); tables(); }}
    boot();
  </script>
</body>
</html>
"""


def write_dashboard(
    data: dict,
    html_path: Path,
    mode: str,
    inline_threshold_kb: int,
    media_threshold_mb: int,
) -> tuple[str, Path | None]:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    payload_size = len(payload.encode("utf-8"))
    render_mode = mode
    if mode == "auto":
        structured_large = payload_size > inline_threshold_kb * 1024
        evidence_large = int(data.get("evidence_bytes") or 0) > media_threshold_mb * 1024 * 1024
        render_mode = "local-js" if structured_large or evidence_large else "inline"
    data["render_mode"] = render_mode
    data["data_payload_bytes"] = payload_size
    data["auto_mode_reason"] = (
        f"structured={payload_size} bytes; evidence={int(data.get('evidence_bytes') or 0)} bytes"
    )
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")

    if render_mode == "inline":
        data_script = f"<script>window.__LIVE_MONITOR_DATA__ = {payload};</script>"
        data_path = None
    else:
        data_dir = html_path.parent / "_internal_技术底稿" / "html_data"
        data_dir.mkdir(parents=True, exist_ok=True)
        data_path = data_dir / "直播分析数据.js"
        data_path.write_text(f"window.__LIVE_MONITOR_DATA__ = {payload};\n", encoding="utf-8")
        src = rel_from(data_path, html_path.parent)
        data_script = f'<script src="{src}"></script>'

    html_path.write_text(html_template(data_script), encoding="utf-8")
    return render_mode, data_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local HTML dashboard for live-commerce monitor outputs.")
    parser.add_argument("--delivery-dir", required=True, help="Live monitor delivery or run directory.")
    parser.add_argument("--mode", choices=["auto", "inline", "local-js"], default="auto")
    parser.add_argument("--inline-threshold-kb", type=int, default=180)
    parser.add_argument("--media-threshold-mb", type=int, default=50)
    parser.add_argument("--out", help="Output HTML path. Defaults to 07_直播分析可视化看板.html in delivery-dir.")
    parser.add_argument("--title", default="直播分析可视化看板")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.delivery_dir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"delivery-dir not found: {root}")
    html_path = Path(args.out).expanduser().resolve() if args.out else root / "07_直播分析可视化看板.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    data = build_data(root, html_path, args.title)
    render_mode, data_path = write_dashboard(
        data,
        html_path,
        args.mode,
        args.inline_threshold_kb,
        args.media_threshold_mb,
    )
    print(f"HTML: {html_path}")
    print(f"mode: {render_mode}")
    if data_path:
        print(f"data: {data_path}")
    print(f"metrics: {len(data['metrics'])}, speech: {len(data['speech_segments'])}, screenshots: {len(data['screenshots'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
