# exec_dashboard.py — HTML Executive Command Center Generator
# ============================================================
# สร้าง HTML Dashboard สำหรับ Tab 2 — ตามสไตล์ Chemical/Pesticide Lab
# ใช้ Chart.js ผ่าน CDN — สีเขียว #1a7a3d, แดง #e24b4a, น้ำเงิน #0f4c8a
# ============================================================
from __future__ import annotations
import json
from datetime import datetime
from config import DEPARTMENTS, GROUPS, TRAFFIC

G  = "#1a7a3d"   # green
R  = "#e24b4a"   # red
Y  = "#d4900a"   # yellow/amber
B  = "#0f4c8a"   # blue header
B2 = "#185fa5"   # blue lighter

def _tc(traffic: str) -> str:
    return {"green": G, "yellow": Y, "red": R}.get(traffic, B)

def _tc_bg(traffic: str) -> str:
    return {"green": "#d6f2e0", "yellow": "#fef3cd", "red": "#fde8e8"}.get(traffic, "#e6f1fb")

def _pct(val: float) -> int:
    return max(0, min(100, round(val)))


# ════════════════════════════════════════════════════════════
# HTML BUILDERS
# ════════════════════════════════════════════════════════════

def _donut_card(canvas_id: str, title: str, score: float, traffic: str,
                label_pass: str, label_fail: str, footnote: str) -> str:
    color = _tc(traffic)
    nd = _pct(score)
    d  = 100 - nd
    return f"""
  <div class="card">
    <div class="card-title">{title}</div>
    <div class="donut-wrap">
      <div class="donut-canvas-wrap">
        <canvas id="{canvas_id}"></canvas>
        <div class="donut-center">
          <div class="donut-pct" style="color:{color};">{nd}%</div>
          <div class="donut-lbl">score</div>
        </div>
      </div>
      <div class="leg-wrap">
        <div class="leg-row">
          <span class="leg-dot" style="background:{color};"></span>
          <span class="leg-name">{label_pass}</span>
          <span class="leg-val" style="color:{color};">{nd}</span>
        </div>
        <div class="leg-row">
          <span class="leg-dot" style="background:{R};"></span>
          <span class="leg-name">{label_fail}</span>
          <span class="leg-val" style="color:{R};">{d}</span>
        </div>
        <div style="border-top:0.5px solid #e2e8f0;padding-top:6px;margin-top:4px;font-size:10px;color:#64748b;">{footnote}</div>
      </div>
    </div>
  </div>"""


def _dept_cards(dept_kpis: dict) -> str:
    html = ""
    for dk, dc in DEPARTMENTS.items():
        kpi = dept_kpis.get(dk, {})
        score   = kpi.get("score") or 0
        traffic = kpi.get("traffic", "red")
        pending = kpi.get("pending", 0)
        color   = _tc(traffic)
        bg      = _tc_bg(traffic)
        emoji   = TRAFFIC[traffic]["emoji"]
        pend_html = f'<div style="font-size:9px;color:#64748b;">⏳{pending}</div>' if pending else ""
        html += f"""
      <div class="dept-card" style="border-left:3px solid {color};background:{bg};">
        <div style="font-size:1.2rem;">{dc['icon']}</div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:10px;color:#374151;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{dc['name_th']}</div>
          <div style="font-size:13px;font-weight:700;color:{color};">{score:.0f}%</div>
          {pend_html}
        </div>
        <div style="font-size:1rem;">{emoji}</div>
      </div>"""
    return html


def _issues_html(top_issues: list, alerts: list) -> str:
    html = '<div class="section-label">🚨 Top 3 Urgent Issues</div>'
    if top_issues:
        for i, issue in enumerate(top_issues[:3]):
            icon_bg = R if i == 0 else (Y if i == 1 else "#64748b")
            html += f"""
      <div class="issue-row">
        <span style="background:{icon_bg};color:#fff;border-radius:50%;width:18px;height:18px;
              display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;flex-shrink:0;">{i+1}</span>
        <span style="flex:1;font-size:11px;color:#374151;line-height:1.4;">{issue}</span>
      </div>"""
    else:
        html += f'<div style="color:{G};font-size:11px;padding:8px 0;">✅ ทุกหน่วยงานอยู่ในเกณฑ์มาตรฐาน</div>'

    html += '<div style="margin-top:10px;"></div><div class="section-label">🔗 Cross-Dept Alerts</div>'
    crits = [a for a in alerts if a.get("severity") == "critical"][:3]
    if crits:
        for a in crits:
            html += f'<div style="background:#fff5f5;border-left:3px solid {R};border-radius:4px;padding:5px 8px;margin-bottom:3px;font-size:10px;color:#7f1d1d;">🔴 <b>{a["message"]}</b><br><span style="color:#9ca3af;">{a["trigger"]} → {a["target"]}</span></div>'
    else:
        html += f'<div style="color:{G};font-size:11px;padding:8px 0;">✅ ไม่พบ Cross-Dept Alerts</div>'
    return html


def _compliance_rows(export_kpi: dict, domestic_kpi: dict, factory_kpi: dict) -> str:
    rows = [
        ("🏠 Domestic 95%",  domestic_kpi.get("score", 0),  domestic_kpi.get("status", "red")),
        ("🌐 Export 5%",     export_kpi.get("score", 0),    export_kpi.get("status", "red")),
        ("🏭 Factory Overall", factory_kpi.get("factory_score", 0), factory_kpi.get("factory_traffic", "red")),
    ]
    html = ""
    for label, score, traffic in rows:
        color = _tc(traffic)
        pct = _pct(score)
        html += f"""
      <div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:0.5px solid #f1f5f9;">
        <span style="font-size:11px;font-weight:500;color:#374151;min-width:110px;">{label}</span>
        <div style="background:#e2e8f0;border-radius:4px;height:8px;flex:1;margin:0 10px;overflow:hidden;">
          <div style="width:{pct}%;height:100%;border-radius:4px;background:{color};transition:width 0.6s;"></div>
        </div>
        <span style="font-size:12px;font-weight:700;color:{color};min-width:36px;text-align:right;">{pct}%</span>
      </div>"""
    return html


def _regulatory_tracker(dept_kpis: dict) -> str:
    """Government compliance tracker — กรมประมง, ปศุสัตว์, มกอช., อย."""
    agencies = [
        ("🐟 กรมประมง", "11_Data_Regulatory"),
        ("🐄 กรมปศุสัตว์", "11_Data_Regulatory"),
        ("🌾 มกอช.", "03_Technical"),
        ("💊 อย.", "08_Lab_Chem"),
    ]
    html = '<div class="section-label">🏛️ Government Compliance Tracker</div>'
    for label, dk in agencies:
        kpi = dept_kpis.get(dk, {})
        score   = kpi.get("score") or 0
        traffic = kpi.get("traffic", "red")
        color   = _tc(traffic)
        pct     = _pct(score)
        emoji   = TRAFFIC[traffic]["emoji"]
        status_label = {"green": "ครบถ้วน ✅", "yellow": "ตรวจสอบเพิ่ม ⚠️", "red": "ขาด/หมดอายุ ❌"}.get(traffic, "—")
        html += f"""
      <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:0.5px solid #f1f5f9;">
        <span style="font-size:11px;font-weight:500;color:#374151;min-width:100px;">{label}</span>
        <div style="background:#e2e8f0;border-radius:4px;height:7px;flex:1;overflow:hidden;">
          <div style="width:{pct}%;height:100%;background:{color};border-radius:4px;"></div>
        </div>
        <span style="font-size:10px;color:{color};min-width:90px;text-align:right;">{emoji} {status_label}</span>
      </div>"""
    return html


# ════════════════════════════════════════════════════════════
# CHART.JS DATA BUILDERS
# ════════════════════════════════════════════════════════════

def _build_js(factory_kpi, export_kpi, domestic_kpi, comp_kpi, dept_kpis) -> str:
    f_score   = factory_kpi.get("factory_score", 0)
    e_score   = export_kpi.get("score", 0)
    d_score   = domestic_kpi.get("score", 0)
    c_score   = comp_kpi.get("score") or 0
    f_traffic = factory_kpi.get("factory_traffic", "red")
    e_traffic = export_kpi.get("status", "red")
    d_traffic = domestic_kpi.get("status", "red")
    c_traffic = comp_kpi.get("traffic", "red")

    dept_names  = [DEPARTMENTS[dk]["icon"] + " " + DEPARTMENTS[dk]["name_th"][:8] for dk in DEPARTMENTS]
    dept_scores = [round(dept_kpis.get(dk, {}).get("score") or 0, 1) for dk in DEPARTMENTS]
    dept_colors = [_tc(dept_kpis.get(dk, {}).get("traffic", "red")) for dk in DEPARTMENTS]

    return f"""
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const G='{G}',R='{R}',Y='{Y}',B='{B}';

function mkDonut(id, score, color) {{
  const nd=Math.round(score), d=100-nd;
  new Chart(document.getElementById(id), {{
    type:'doughnut',
    data:{{
      labels:['ผ่าน','ไม่ผ่าน'],
      datasets:[{{
        data:[nd, d||0.5],
        backgroundColor:[color, d===0?'#e2e8f0':R],
        borderWidth:2,borderColor:'#fff',hoverBorderWidth:0
      }}]
    }},
    options:{{
      responsive:true,maintainAspectRatio:true,cutout:'72%',
      plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>' '+ctx.parsed+'%'}}}}}}
    }}
  }});
}}
mkDonut('donutFactory', {_pct(f_score)}, '{_tc(f_traffic)}');
mkDonut('donutExport',  {_pct(e_score)}, '{_tc(e_traffic)}');
mkDonut('donutDomestic',{_pct(d_score)}, '{_tc(d_traffic)}');
mkDonut('donutComp',    {_pct(c_score)}, '{_tc(c_traffic)}');

// Dept bar chart
const dNames  = {json.dumps(dept_names)};
const dScores = {json.dumps(dept_scores)};
const dColors = {json.dumps(dept_colors)};

new Chart(document.getElementById('deptBar'), {{
  type:'bar',
  data:{{
    labels:dNames,
    datasets:[{{
      data:dScores,
      backgroundColor:dColors,
      borderRadius:4,
      borderSkipped:false
    }}]
  }},
  options:{{
    responsive:true,maintainAspectRatio:false,
    plugins:{{
      legend:{{display:false}},
      tooltip:{{callbacks:{{label:ctx=>' KPI: '+ctx.parsed.toFixed(1)+'%'}}}}
    }},
    scales:{{
      x:{{grid:{{display:false}},ticks:{{font:{{size:9}},color:'#555',maxRotation:50}}}},
      y:{{
        beginAtZero:true,max:100,
        grid:{{color:'rgba(0,0,0,0.04)'}},
        ticks:{{font:{{size:9}},color:'#666',stepSize:25}},
        border:{{display:false}}
      }}
    }},
    animation:{{
      onComplete:function(){{
        const ctx=this.ctx;
        const meta=this.getDatasetMeta(0);
        meta.data.forEach((bar,i)=>{{
          const val=dScores[i];
          if(val>5){{
            ctx.fillStyle='#fff';ctx.font='bold 9px sans-serif';
            ctx.textAlign='center';
            ctx.fillText(val+'%',bar.x,bar.y+12);
          }}
        }});
        // threshold line label
        ctx.fillStyle=G;ctx.font='500 9px sans-serif';ctx.textAlign='left';
        ctx.fillText('▶ เกณฑ์ 85%',4,this.scales.y.getPixelForValue(85)+4);
      }}
    }}
  }}
}});
</script>"""


# ════════════════════════════════════════════════════════════
# MAIN BUILD FUNCTION
# ════════════════════════════════════════════════════════════

def _rsi_panel(dept_rsi: dict) -> str:
    SIGNAL = {
        "overbought": ("🔴", "Overbought", R,        "#fde8e8"),
        "oversold":   ("🔵", "Oversold",   "#1565c0", "#e3f2fd"),
        "neutral":    ("🟢", "Neutral",    G,         "#d6f2e0"),
        "no_data":    ("⬜", "N/A",        "#94a3b8", "#f8fafc"),
    }
    html = '<div class="section-label">📈 RSI KPI Momentum (14d)</div>'
    html += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:4px;">'
    for dk, dc in DEPARTMENTS.items():
        rd = dept_rsi.get(dk, {})
        rsi_val = rd.get("rsi")
        signal  = rd.get("signal", "no_data")
        icon, label, color, bg = SIGNAL.get(signal, SIGNAL["no_data"])
        rsi_display = f"{rsi_val:.0f}" if rsi_val is not None else "N/A"
        bar_pct = rsi_val if rsi_val is not None else 0
        overbought_w = max(0, bar_pct - 70) / 30 * 100 if bar_pct >= 70 else 0
        neutral_w    = (min(bar_pct, 70) - min(bar_pct, 30)) / 40 * 100 if bar_pct > 30 else 0
        oversold_w   = min(bar_pct, 30) / 30 * 100 if bar_pct < 30 else 0
        html += f"""
      <div style="background:{bg};border-radius:6px;padding:5px 8px;display:flex;align-items:center;gap:6px;">
        <span style="font-size:0.9rem;">{dc['icon']}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-size:9px;color:#374151;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{dc['name_th'][:12]}</div>
          <div style="background:#e2e8f0;border-radius:3px;height:5px;margin-top:3px;overflow:hidden;display:flex;">
            <div style="width:{min(bar_pct,30)/100*100:.0f}%;height:100%;background:#1565c0;"></div>
            <div style="width:{max(0,min(bar_pct,70)-30)/100*100:.0f}%;height:100%;background:{G};"></div>
            <div style="width:{max(0,bar_pct-70)/100*100:.0f}%;height:100%;background:{R};"></div>
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0;">
          <div style="font-size:11px;font-weight:700;color:{color};">{rsi_display}</div>
          <div style="font-size:8px;color:{color};">{label}</div>
        </div>
      </div>"""
    html += '</div>'
    html += f"""<div style="display:flex;gap:12px;margin-top:6px;font-size:9px;color:#64748b;padding-top:4px;border-top:0.5px solid #e2e8f0;">
      <span>🔵 &lt;30 Oversold (KPI ตกต่ำ)</span>
      <span>🟢 30–70 Neutral</span>
      <span>🔴 &gt;70 Overbought (KPI วิ่งแรง)</span>
    </div>"""
    return html


def build_exec_html(
    factory_kpi:  dict,
    export_kpi:   dict,
    domestic_kpi: dict,
    dept_kpis:    dict,
    alerts:       list,
    dept_rsi:     dict = None,
) -> str:
    """
    สร้าง HTML Executive Dashboard ครบสมบูรณ์
    เรียกใช้ใน Tab 2 ของ app.py ผ่าน st.components.v1.html()
    """
    now      = datetime.now().strftime("%d %b %Y, %H:%M")
    f_score  = factory_kpi.get("factory_score", 0)
    f_traffic = factory_kpi.get("factory_traffic", "red")
    e_score  = export_kpi.get("score", 0)
    e_traffic = export_kpi.get("status", "red")
    d_score  = domestic_kpi.get("score", 0)
    d_traffic = domestic_kpi.get("status", "red")
    comp_kpi  = dept_kpis.get("11_Data_Regulatory", {})
    comp_score = comp_kpi.get("score") or 0
    comp_traffic = comp_kpi.get("traffic", "red")
    top_issues = factory_kpi.get("top_issues", [])

    css = f"""
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Tahoma,sans-serif;}}
body{{background:#eef2f7;padding:0;}}
.dash{{padding:14px;max-width:1200px;margin:0 auto;}}
/* Header */
.header{{background:{B};border-radius:10px;padding:14px 20px;display:flex;align-items:center;
         justify-content:space-between;margin-bottom:12px;box-shadow:0 2px 8px rgba(15,76,138,0.3);}}
.header-title{{color:#fff;font-size:16px;font-weight:600;letter-spacing:0.2px;}}
.header-sub{{color:#a8c8f0;font-size:11px;margin-top:3px;}}
.header-right{{display:flex;align-items:center;gap:10px;}}
.header-date{{background:#1a6bbd;color:#dbeeff;font-size:11px;padding:5px 12px;border-radius:6px;border:1px solid #2e80d8;white-space:nowrap;}}
.header-badge{{padding:4px 10px;border-radius:20px;font-size:10px;font-weight:600;}}
/* Cards */
.card{{background:#fff;border:0.5px solid #e2e8f0;border-radius:10px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);}}
.card-title{{font-size:10px;font-weight:600;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.6px;}}
/* KPI row */
.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px;}}
/* Donut */
.donut-wrap{{display:flex;align-items:center;gap:12px;}}
.donut-canvas-wrap{{position:relative;width:90px;height:90px;flex-shrink:0;}}
.donut-center{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;line-height:1.2;}}
.donut-pct{{font-size:17px;font-weight:600;}}
.donut-lbl{{font-size:9px;color:#94a3b8;}}
.leg-wrap{{display:flex;flex-direction:column;gap:6px;flex:1;}}
.leg-row{{display:flex;align-items:center;gap:6px;}}
.leg-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}
.leg-name{{font-size:10px;color:#64748b;flex:1;line-height:1.3;}}
.leg-val{{font-size:11px;font-weight:600;}}
/* Charts row */
.charts-row{{display:grid;grid-template-columns:1.3fr 1fr;gap:10px;margin-bottom:12px;}}
/* Dept grid */
.dept-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;}}
.dept-card{{display:flex;align-items:center;gap:8px;border-radius:8px;padding:7px 9px;}}
/* Issue row */
.issue-row{{display:flex;align-items:flex-start;gap:8px;padding:5px 0;border-bottom:0.5px solid #f1f5f9;}}
/* Bottom */
.bottom-row{{display:grid;grid-template-columns:1fr 1fr;gap:10px;}}
.section-label{{font-size:10px;font-weight:600;color:{B};background:#e6f1fb;padding:2px 8px;
                border-radius:4px;display:inline-block;margin-bottom:8px;}}
</style>"""

    header_traffic_color = _tc(f_traffic)
    header_badge_bg      = _tc_bg(f_traffic)
    header_badge_label   = {"green": "✅ ปกติ", "yellow": "⚠️ เฝ้าระวัง", "red": "🔴 วิกฤต"}.get(f_traffic, "")

    header_html = f"""
<div class="header">
  <div>
    <div class="header-title">🏭 QA Executive Command Center — CPRAM ลาดหลุมแก้ว</div>
    <div class="header-sub">ภาพรวม 11 หน่วยงาน QA | Unified Quality Dashboard</div>
  </div>
  <div class="header-right">
    <span class="header-badge" style="background:{header_badge_bg};color:{header_traffic_color};">{header_badge_label}</span>
    <div class="header-date">📅 {now}</div>
  </div>
</div>"""

    kpi_row = (
        '<div class="kpi-row">'
        + _donut_card("donutFactory", "🏭 Factory QA Health",
                      f_score, f_traffic, "ผ่านเกณฑ์", "ต้องปรับปรุง",
                      f'🔴 {factory_kpi.get("red_count",0)} วิกฤต &nbsp;🟡 {factory_kpi.get("yellow_count",0)} เฝ้าระวัง')
        + _donut_card("donutExport", "🌐 Export Readiness (5%)",
                      e_score, e_traffic, "พร้อมส่งออก", "ไม่พร้อม",
                      export_kpi.get("label", "—"))
        + _donut_card("donutDomestic", "🏠 Domestic Quality (95%)",
                      d_score, d_traffic, "มาตรฐาน", "ต่ำกว่าเกณฑ์",
                      domestic_kpi.get("label", "—"))
        + _donut_card("donutComp", "📋 Regulatory Compliance",
                      comp_score, comp_traffic, "เอกสารครบ", "ขาด/หมดอายุ",
                      "กรมประมง + ปศุสัตว์ + อย.")
        + '</div>'
    )

    charts_row = f"""
<div class="charts-row">
  <div class="card">
    <div class="section-label">🏭 สถานะ 11 หน่วยงาน QA</div>
    <div class="dept-grid">{_dept_cards(dept_kpis)}</div>
    <div style="margin-top:10px;">
      <canvas id="deptBar" style="max-height:160px;"></canvas>
    </div>
  </div>
  <div class="card">
    {_issues_html(top_issues, alerts)}
  </div>
</div>"""

    bottom_row = f"""
<div class="bottom-row">
  <div class="card">
    <div class="section-label">📊 Domestic vs Export Status</div>
    {_compliance_rows(export_kpi, domestic_kpi, factory_kpi)}
    <div style="margin-top:12px;">
      <div style="display:flex;justify-content:space-between;font-size:10px;color:#64748b;margin-bottom:4px;">
        <span>⏳ งานค้าง (Pending): <b style="color:{Y};">{factory_kpi.get("total_pending",0)} รายการ</b></span>
        <span>🔔 Cross-Dept Alerts: <b style="color:{R};">{len(alerts)} รายการ</b></span>
      </div>
    </div>
  </div>
  <div class="card">
    {_regulatory_tracker(dept_kpis)}
  </div>
</div>"""

    js = _build_js(factory_kpi, export_kpi, domestic_kpi, comp_kpi, dept_kpis)

    rsi_row = ""
    if dept_rsi:
        rsi_row = f'<div class="card" style="margin-bottom:12px;">{_rsi_panel(dept_rsi)}</div>'

    return f"""<!DOCTYPE html>
<html lang="th">
<head><meta charset="UTF-8">{css}</head>
<body>
<div class="dash">
{header_html}
{kpi_row}
{charts_row}
{bottom_row}
{rsi_row}
</div>
{js}
</body>
</html>"""
