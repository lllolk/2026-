#!/usr/bin/env python3
"""Summarize the course formal experiment and generate the two required SVG figures."""

import csv
import html
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "course_runs" / "experiments" / "20261014-175759" / "results.csv"
OUT = ROOT / "analysis_results" / "20261014-175759"

NUMERIC = {
    "repeat", "queries", "selectivity_min", "selectivity_median", "selectivity_max",
    "L", "k", "threads", "beamwidth", "index_bytes", "elapsed_seconds",
    "peak_rss_kb", "qps", "mean_latency_us", "p999_latency_us", "recall_percent",
    "mean_ios", "pre_filter_queries", "in_filter_queries", "post_filter_queries",
    "filter_false_positives", "filter_skips", "io_time_us", "tunnel_time_us",
    "process_time_us",
}


def load_rows():
    with INPUT.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key in NUMERIC:
            value = row.get(key, "")
            row[key] = None if value == "" else float(value)
    return rows


def med(values):
    return statistics.median(v for v in values if v is not None)


def bounds(values):
    clean = [v for v in values if v is not None]
    return (min(clean), max(clean)) if clean else (None, None)


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["system"], row["bucket"], int(row["L"]))].append(row)
    if len(rows) != 30 or any(len(group) != 3 for group in groups.values()):
        raise ValueError("Expected 30 rows and exactly three repeats per system+bucket+L")

    metrics = [
        "recall_percent", "mean_latency_us", "qps", "mean_ios", "peak_rss_kb",
        "filter_false_positives", "filter_skips", "io_time_us", "tunnel_time_us",
        "process_time_us", "pre_filter_queries", "in_filter_queries", "post_filter_queries",
    ]
    result = []
    for (system, bucket, l_value), group in sorted(groups.items()):
        item = {
            "system": system,
            "bucket": bucket,
            "L": l_value,
            "repeats": len(group),
            "selectivity_min": med([r["selectivity_min"] for r in group]),
            "selectivity_median": med([r["selectivity_median"] for r in group]),
            "selectivity_max": med([r["selectivity_max"] for r in group]),
            "index_gib": med([r["index_bytes"] for r in group]) / 1024**3,
        }
        for metric in metrics:
            values = [r[metric] for r in group]
            clean = [v for v in values if v is not None]
            if clean:
                item[f"{metric}_median"] = med(clean)
                item[f"{metric}_min"], item[f"{metric}_max"] = bounds(clean)
            else:
                item[f"{metric}_median"] = None
                item[f"{metric}_min"] = None
                item[f"{metric}_max"] = None
        result.append(item)
    return result


def write_summary_csv(summary):
    path = OUT / "summary_by_system_bucket_L.csv"
    keys = list(summary[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(summary)


COLORS = {"pipeann": "#2878B5", "gateann": "#D95319"}
LABELS = {"pipeann": "PipeANN-Filter", "gateann": "GateANN"}


def esc(text):
    return html.escape(str(text))


def svg_text(x, y, text, size=13, anchor="middle", weight="normal", rotate=None):
    transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" font-weight="{weight}"{transform}>'
            f'{esc(text)}</text>')


def line_figure(summary):
    data = [s for s in summary if s["bucket"] == "high"]
    width, height = 900, 600
    left, right, top, bottom = 105, 45, 70, 90
    pw, ph = width-left-right, height-top-bottom
    xs = [s["mean_latency_us_median"] / 1000 for s in data]
    ys = [s["recall_percent_median"] for s in data]
    xmin, xmax = min(xs)*0.88, max(xs)*1.08
    ymin, ymax = max(0, min(ys)-7), min(100, max(ys)+3)
    sx = lambda x: left + (x-xmin)/(xmax-xmin)*pw
    sy = lambda y: top + (ymax-y)/(ymax-ymin)*ph
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             svg_text(width/2, 32, "High Workload: Recall@10 vs Mean Latency", 20, weight="bold")]
    for i in range(6):
        x = xmin + (xmax-xmin)*i/5
        px = sx(x)
        parts += [f'<line x1="{px}" y1="{top}" x2="{px}" y2="{top+ph}" stroke="#e4e4e4"/>',
                  svg_text(px, top+ph+25, f"{x:.0f}")]
    for i in range(6):
        y = ymin + (ymax-ymin)*i/5
        py = sy(y)
        parts += [f'<line x1="{left}" y1="{py}" x2="{left+pw}" y2="{py}" stroke="#e4e4e4"/>',
                  svg_text(left-12, py+5, f"{y:.0f}", anchor="end")]
    parts += [f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" stroke="black"/>',
              f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" stroke="black"/>',
              svg_text(left+pw/2, height-35, "Mean latency (ms)", 15),
              svg_text(28, top+ph/2, "Recall@10 (%)", 15, rotate=-90)]
    for system in ("pipeann", "gateann"):
        points = sorted((s for s in data if s["system"] == system), key=lambda s: s["L"])
        poly = " ".join(f'{sx(p["mean_latency_us_median"]/1000):.1f},{sy(p["recall_percent_median"]):.1f}' for p in points)
        parts.append(f'<polyline points="{poly}" fill="none" stroke="{COLORS[system]}" stroke-width="3"/>')
        for p in points:
            x = p["mean_latency_us_median"] / 1000
            y = p["recall_percent_median"]
            xlo, xhi = p["mean_latency_us_min"]/1000, p["mean_latency_us_max"]/1000
            ylo, yhi = p["recall_percent_min"], p["recall_percent_max"]
            px, py = sx(x), sy(y)
            parts += [f'<line x1="{sx(xlo)}" y1="{py}" x2="{sx(xhi)}" y2="{py}" stroke="{COLORS[system]}"/>',
                      f'<line x1="{px}" y1="{sy(ylo)}" x2="{px}" y2="{sy(yhi)}" stroke="{COLORS[system]}"/>',
                      f'<circle cx="{px}" cy="{py}" r="6" fill="{COLORS[system]}"/>',
                      svg_text(px+8, py-10, f'L={p["L"]}', 12, anchor="start")]
    for i, system in enumerate(("pipeann", "gateann")):
        y = 55 + i*22
        parts += [f'<line x1="650" y1="{y}" x2="680" y2="{y}" stroke="{COLORS[system]}" stroke-width="3"/>',
                  svg_text(690, y+5, LABELS[system], 13, anchor="start")]
    parts.append('</svg>')
    (OUT / "figure1_recall_latency_high.svg").write_text("\n".join(parts), encoding="utf-8")


def selectivity_figure(summary):
    chosen = [s for s in summary if (s["system"] == "pipeann" and s["L"] == 40) or
              (s["system"] == "gateann" and s["L"] == 320)]
    buckets = ["low", "medium", "high"]
    metrics = [("recall_percent", "Recall@10 (%)"), ("mean_latency_us", "Mean latency (ms)"),
               ("mean_ios", "Mean logical I/O")]
    width, height = 1320, 470
    margin, gap, top, bottom = 75, 55, 75, 85
    panel_w = (width-2*margin-2*gap)/3
    ph = height-top-bottom
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             svg_text(width/2, 30, "Selectivity–Performance (median with min–max range)", 20, weight="bold")]
    for panel, (metric, title) in enumerate(metrics):
        x0 = margin + panel*(panel_w+gap)
        vals = []
        for p in chosen:
            scale = 1000 if metric == "mean_latency_us" else 1
            vals.extend([p[f"{metric}_min"]/scale, p[f"{metric}_max"]/scale])
        ymax = max(vals)*1.18
        sx = lambda i: x0 + panel_w*(0.15 + 0.35*i)
        sy = lambda y: top + ph*(1-y/ymax)
        for i in range(5):
            y = ymax*i/4
            py = sy(y)
            parts += [f'<line x1="{x0}" y1="{py}" x2="{x0+panel_w}" y2="{py}" stroke="#e4e4e4"/>',
                      svg_text(x0-8, py+4, f"{y:.1f}", 11, anchor="end")]
        parts += [svg_text(x0+panel_w/2, 56, title, 15, weight="bold"),
                  f'<line x1="{x0}" y1="{top+ph}" x2="{x0+panel_w}" y2="{top+ph}" stroke="black"/>',
                  f'<line x1="{x0}" y1="{top}" x2="{x0}" y2="{top+ph}" stroke="black"/>']
        for i, bucket in enumerate(buckets):
            px = sx(i)
            sel = next(p for p in chosen if p["bucket"] == bucket)["selectivity_median"]*100
            parts += [svg_text(px, top+ph+23, bucket.title(), 12),
                      svg_text(px, top+ph+40, f"({sel:.3f}%)", 10)]
        for system in ("pipeann", "gateann"):
            pts = []
            for i, bucket in enumerate(buckets):
                p = next(x for x in chosen if x["system"] == system and x["bucket"] == bucket)
                scale = 1000 if metric == "mean_latency_us" else 1
                value = p[f"{metric}_median"]/scale
                lo, hi = p[f"{metric}_min"]/scale, p[f"{metric}_max"]/scale
                px, py = sx(i), sy(value)
                pts.append(f"{px:.1f},{py:.1f}")
                parts += [f'<line x1="{px}" y1="{sy(lo)}" x2="{px}" y2="{sy(hi)}" stroke="{COLORS[system]}"/>',
                          f'<circle cx="{px}" cy="{py}" r="5" fill="{COLORS[system]}"/>']
            parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{COLORS[system]}" stroke-width="2.5"/>')
    for i, system in enumerate(("pipeann", "gateann")):
        x = 505 + i*190
        parts += [f'<line x1="{x}" y1="{height-18}" x2="{x+30}" y2="{height-18}" stroke="{COLORS[system]}" stroke-width="3"/>',
                  svg_text(x+38, height-13, LABELS[system], 13, anchor="start")]
    parts.append('</svg>')
    (OUT / "figure2_selectivity_performance.svg").write_text("\n".join(parts), encoding="utf-8")


def gateann_breakdown_figure(summary):
    points = sorted((p for p in summary if p["system"] == "gateann" and p["bucket"] == "high"), key=lambda p: p["L"])
    width, height = 850, 520
    left, right, top, bottom = 90, 40, 70, 90
    pw, ph = width-left-right, height-top-bottom
    components = [("io_time_us_median", "I/O", "#4C78A8"), ("tunnel_time_us_median", "Tunnel", "#F58518"), ("process_time_us_median", "Process", "#54A24B")]
    totals = [sum(p[k] for k, _, _ in components)/1000 for p in points]
    ymax = max(totals)*1.18
    sy = lambda y: top + ph*(1-y/ymax)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', svg_text(width/2, 32, "GateANN High: Internal Time Breakdown", 20, weight="bold")]
    for i in range(6):
        y = ymax*i/5
        py = sy(y)
        parts += [f'<line x1="{left}" y1="{py}" x2="{left+pw}" y2="{py}" stroke="#e4e4e4"/>', svg_text(left-10, py+4, f"{y:.0f}", 11, anchor="end")]
    bar_w = 105
    for i, p in enumerate(points):
        x = left + pw*(0.2+0.3*i)
        base = 0
        for key, _, color in components:
            value = p[key]/1000
            y1, y2 = sy(base+value), sy(base)
            parts.append(f'<rect x="{x-bar_w/2}" y="{y1}" width="{bar_w}" height="{y2-y1}" fill="{color}"/>')
            base += value
        parts += [svg_text(x, top+ph+25, f'L={p["L"]}', 13), svg_text(x, sy(base)-8, f"{base:.2f}", 11)]
    parts += [f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" stroke="black"/>', f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" stroke="black"/>', svg_text(28, top+ph/2, "Reported time (ms/query)", 14, rotate=-90)]
    for i, (_, label, color) in enumerate(components):
        x = 235+i*150
        parts += [f'<rect x="{x}" y="{height-35}" width="18" height="12" fill="{color}"/>', svg_text(x+26, height-24, label, 12, anchor="start")]
    parts.append('</svg>')
    (OUT / "figure3_gateann_time_breakdown.svg").write_text("\n".join(parts), encoding="utf-8")


def mechanism_figure(summary):
    pipe = [p for p in summary if p["system"] == "pipeann" and p["L"] == 40]
    gate = [p for p in summary if p["system"] == "gateann" and p["L"] == 320]
    order = {"low": 0, "medium": 1, "high": 2}
    pipe.sort(key=lambda p: order[p["bucket"]]); gate.sort(key=lambda p: order[p["bucket"]])
    width, height = 1100, 500
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', svg_text(width/2, 30, "Filtering Mechanism Indicators across Selectivity", 20, weight="bold")]
    panels = [(65, 475), (625, 410)]
    x0, pw = panels[0]
    top, ph = 75, 315
    colors = [("pre_filter_queries_median", "Pre", "#4C78A8"), ("in_filter_queries_median", "In", "#F58518"), ("post_filter_queries_median", "Post", "#54A24B")]
    parts.append(svg_text(x0+pw/2, 57, "PipeANN-Filter routing (L=40)", 15, weight="bold"))
    for i in range(5):
        y = 200*i/4; py = top+ph*(1-y/200)
        parts += [f'<line x1="{x0}" y1="{py}" x2="{x0+pw}" y2="{py}" stroke="#e4e4e4"/>', svg_text(x0-8, py+4, f"{y:.0f}", 11, anchor="end")]
    for i, p in enumerate(pipe):
        x = x0+pw*(0.18+0.32*i); base=0
        for key, _, color in colors:
            value=p[key]; y1=top+ph*(1-(base+value)/200); y2=top+ph*(1-base/200)
            if value: parts.append(f'<rect x="{x-42}" y="{y1}" width="84" height="{y2-y1}" fill="{color}"/>')
            base += value
        parts += [svg_text(x, top+ph+22, p["bucket"].title(), 12), svg_text(x, top+ph+39, f'FP={p["filter_false_positives_median"]:.1f}', 10)]
    parts += [svg_text(18, top+ph/2, "Queries", 13, rotate=-90)]
    for i, (_, label, color) in enumerate(colors):
        x=x0+95+i*100; parts += [f'<rect x="{x}" y="{height-38}" width="16" height="11" fill="{color}"/>', svg_text(x+22,height-28,label,11,anchor="start")]
    x0, pw = panels[1]
    parts.append(svg_text(x0+pw/2, 57, "GateANN indicators (L=320)", 15, weight="bold"))
    ymax=350
    sy=lambda y: top+ph*(1-y/ymax)
    for i in range(5):
        y=ymax*i/4; py=sy(y); parts += [f'<line x1="{x0}" y1="{py}" x2="{x0+pw}" y2="{py}" stroke="#e4e4e4"/>',svg_text(x0-8,py+4,f"{y:.0f}",11,anchor="end")]
    for metric,label,color in [("filter_skips_median","FilterSkips","#D95319"),("mean_ios_median","Mean I/O","#2878B5")]:
        pts=[]
        for i,p in enumerate(gate):
            x=x0+pw*(0.18+0.32*i); y=sy(p[metric]); pts.append(f"{x},{y}")
            parts += [f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>',svg_text(x,top+ph+22,p["bucket"].title(),12)] if metric=="filter_skips_median" else [f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>']
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
    parts += [svg_text(580,top+ph/2,"Reported count/query",13,rotate=-90),f'<line x1="{x0+70}" y1="{height-32}" x2="{x0+95}" y2="{height-32}" stroke="#D95319" stroke-width="3"/>',svg_text(x0+102,height-27,"FilterSkips",11,anchor="start"),f'<line x1="{x0+230}" y1="{height-32}" x2="{x0+255}" y2="{height-32}" stroke="#2878B5" stroke-width="3"/>',svg_text(x0+262,height-27,"Mean I/O",11,anchor="start")]
    parts.append('</svg>')
    (OUT / "figure4_filtering_mechanisms.svg").write_text("\n".join(parts),encoding="utf-8")


def resource_figure(summary):
    width,height=950,500; top,bottom=75,75
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="white"/>',svg_text(width/2,30,"Resource Trade-off",20,weight="bold")]
    systems=("pipeann","gateann")
    values=[]
    for s in systems:
        pts=[p for p in summary if p["system"]==s]
        values.append((pts[0]["index_gib"],statistics.median(p["peak_rss_kb_median"]/1024 for p in pts)))
    for panel,(title,idx,ylabel) in enumerate([("Index size",0,"GiB"),("Peak RSS",1,"MiB")]):
        x0=65+panel*470; pw=390; ph=315; ymax=max(v[idx] for v in values)*1.18
        parts.append(svg_text(x0+pw/2,58,title,15,weight="bold"))
        for i in range(5):
            y=ymax*i/4; py=top+ph*(1-y/ymax); parts += [f'<line x1="{x0}" y1="{py}" x2="{x0+pw}" y2="{py}" stroke="#e4e4e4"/>',svg_text(x0-8,py+4,f"{y:.1f}",11,anchor="end")]
        for i,s in enumerate(systems):
            x=x0+pw*(0.28+0.45*i); val=values[i][idx]; y=top+ph*(1-val/ymax)
            parts += [f'<rect x="{x-55}" y="{y}" width="110" height="{top+ph-y}" fill="{COLORS[s]}"/>',svg_text(x,y-9,f"{val:.3f}" if idx==0 else f"{val:.1f}",12),svg_text(x,top+ph+23,LABELS[s],11)]
        parts.append(svg_text(x0-42,top+ph/2,ylabel,13,rotate=-90))
    parts.append('</svg>'); (OUT/"figure5_resource_tradeoff.svg").write_text("\n".join(parts),encoding="utf-8")


def repeat_stability_figure(rows):
    width,height=1100,540; left,right,top,bottom=90,35,70,130; pw,ph=width-left-right,height-top-bottom
    configs=[]
    for system in ("pipeann","gateann"):
        subset=sorted({(r["bucket"],int(r["L"])) for r in rows if r["system"]==system},key=lambda x:({"low":0,"medium":1,"high":2}[x[0]],x[1]))
        configs += [(system,b,l) for b,l in subset]
    ymax=max(r["mean_latency_us"] for r in rows)/1000*1.12
    sy=lambda y:top+ph*(1-y/ymax)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="white"/>',svg_text(width/2,30,"Three-repeat Mean Latency Stability",20,weight="bold")]
    for i in range(6):
        y=ymax*i/5; py=sy(y); parts += [f'<line x1="{left}" y1="{py}" x2="{left+pw}" y2="{py}" stroke="#e4e4e4"/>',svg_text(left-8,py+4,f"{y:.0f}",11,anchor="end")]
    for i,(system,bucket,lval) in enumerate(configs):
        x=left+pw*(i+0.5)/len(configs); vals=sorted(r["mean_latency_us"]/1000 for r in rows if r["system"]==system and r["bucket"]==bucket and int(r["L"])==lval)
        parts += [f'<line x1="{x}" y1="{sy(min(vals))}" x2="{x}" y2="{sy(max(vals))}" stroke="{COLORS[system]}" stroke-width="3"/>']
        for j,v in enumerate(vals): parts.append(f'<circle cx="{x+(j-1)*5}" cy="{sy(v)}" r="4" fill="{COLORS[system]}"/>')
        parts.append(svg_text(x,top+ph+18,f'{"P" if system=="pipeann" else "G"}-{bucket[0].upper()}-L{lval}',10,rotate=35))
    parts += [svg_text(27,top+ph/2,"Mean latency (ms)",14,rotate=-90),svg_text(width/2,height-22,"P=PipeANN-Filter, G=GateANN; L/M/H=Low/Medium/High",11)]
    parts.append('</svg>'); (OUT/"figure6_repeat_stability.svg").write_text("\n".join(parts),encoding="utf-8")


def fmt(value, digits=2):
    return "—" if value is None else f"{value:.{digits}f}"


def write_report_tables(summary):
    high = [s for s in summary if s["bucket"] == "high"]
    chosen = [s for s in summary if (s["system"] == "pipeann" and s["L"] == 40) or
              (s["system"] == "gateann" and s["L"] == 320)]
    lines = ["# 正式实验数据汇总", "", "实验 ID：`20261014-175759`。所有中心值均为三轮中位数，方括号为最小值–最大值。", "",
             "## High workload：Recall–Latency", "",
             "| 系统 | L | Recall@10（%） | Mean Latency（ms） | QPS | Mean I/O |", "|---|---:|---:|---:|---:|---:|"]
    for p in sorted(high, key=lambda x: (x["system"], x["L"])):
        lines.append(f'| {LABELS[p["system"]]} | {p["L"]} | {fmt(p["recall_percent_median"],1)} [{fmt(p["recall_percent_min"],1)}–{fmt(p["recall_percent_max"],1)}] | {fmt(p["mean_latency_us_median"]/1000,2)} [{fmt(p["mean_latency_us_min"]/1000,2)}–{fmt(p["mean_latency_us_max"]/1000,2)}] | {fmt(p["qps_median"],1)} | {fmt(p["mean_ios_median"],2)} |')
    lines += ["", "## Selectivity–Performance（固定 PipeANN L=40、GateANN L=320）", "",
              "| 系统 | Bucket | Selectivity min/median/max（%） | Recall@10（%） | Mean Latency（ms） | Mean I/O | 关键内部指标 |",
              "|---|---|---:|---:|---:|---:|---|"]
    order = {"low": 0, "medium": 1, "high": 2}
    for p in sorted(chosen, key=lambda x: (x["system"], order[x["bucket"]])):
        if p["system"] == "pipeann":
            internal = f'Pre/In/Post={fmt(p["pre_filter_queries_median"],0)}/{fmt(p["in_filter_queries_median"],0)}/{fmt(p["post_filter_queries_median"],0)}; FP={fmt(p["filter_false_positives_median"],1)}'
        else:
            internal = f'FilterSkips={fmt(p["filter_skips_median"],2)}; Tunnel={fmt(p["tunnel_time_us_median"],0)} us'
        lines.append(f'| {LABELS[p["system"]]} | {p["bucket"].title()} | {p["selectivity_min"]*100:.3f}/{p["selectivity_median"]*100:.3f}/{p["selectivity_max"]*100:.3f} | {fmt(p["recall_percent_median"],1)} | {fmt(p["mean_latency_us_median"]/1000,2)} | {fmt(p["mean_ios_median"],2)} | {internal} |')
    lines += ["", "## 资源数据", "", "| 系统 | 索引大小（GiB） | 查询峰值 RSS 中位数范围（MiB） |", "|---|---:|---:|"]
    for system in ("pipeann", "gateann"):
        pts = [p for p in summary if p["system"] == system]
        rss_medians = [p["peak_rss_kb_median"]/1024 for p in pts]
        rss_min = min(p["peak_rss_kb_min"] for p in pts)/1024
        rss_max = max(p["peak_rss_kb_max"] for p in pts)/1024
        lines.append(f'| {LABELS[system]} | {pts[0]["index_gib"]:.3f} | {statistics.median(rss_medians):.1f}（全配置 {rss_min:.1f}–{rss_max:.1f}） |')
    lines += ["", "## 使用边界", "", "- `mean_ios` 是系统内部逻辑 I/O，两套系统页面大小和统计实现不同，不能直接当作物理 I/O 横向排名。", "- Low、Medium、High 使用不同真实标签，不是严格单变量实验。", "- 两套系统的 L 含义和合理取值不同，横向比较需同时报告 Recall。", "- SVG 图中的误差线表示三轮最小值–最大值。", ""]
    (OUT / "report_tables.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    summary = summarize(rows)
    write_summary_csv(summary)
    line_figure(summary)
    selectivity_figure(summary)
    gateann_breakdown_figure(summary)
    mechanism_figure(summary)
    resource_figure(summary)
    repeat_stability_figure(rows)
    write_report_tables(summary)
    print(f"Validated {len(rows)} rows in {len(summary)} groups")
    for path in sorted(OUT.iterdir()):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
