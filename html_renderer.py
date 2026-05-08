# html_renderer.py — Smart per-department HTML report renderer
# ============================================================
# อ่านไฟล์ HTML จากแต่ละหน่วยงาน → วิเคราะห์ตาราง → แสดงผลเฉพาะทาง
# ============================================================
from __future__ import annotations
import io, re
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config import DEPARTMENTS, TRAFFIC

TC = {"green": "#00C853", "yellow": "#FFD600", "red": "#D50000"}

# ─── Per-department column detection hints ──────────────────
# ระบบจะค้นหาชื่อคอลัมน์ที่ตรงกับ hints เหล่านี้ (ทั้งภาษาไทยและอังกฤษ)
DEPT_CONFIGS: dict[str, dict] = {
    "01_Audit_Supplier": {
        "title": "รายงาน Audit Supplier",
        "score_hints":  ["score", "คะแนน", "audit_score", "rating", "grade", "เกรด", "point"],
        "name_hints":   ["supplier", "vendor", "ผู้จำหน่าย", "company", "บริษัท", "name", "ชื่อ", "supplier_name"],
        "status_hints": ["status", "result", "สถานะ", "ผล", "pass_fail", "ผ่าน", "grade"],
        "date_hints":   ["date", "วันที่", "audit_date", "วันตรวจ", "inspect_date"],
        "chart_primary":  "bar_score_by_name",
        "chart_secondary": "trend",
        "kpi_label": "คะแนน Audit เฉลี่ย",
        "summary_cols": ["name_hints", "score_hints", "status_hints", "date_hints"],
    },
    "02_Raw_Material": {
        "title": "รายงานตรวจสอบวัตถุดิบ",
        "score_hints":  ["moisture", "quality_score", "คะแนน", "quality", "คุณภาพ", "pct", "percent", "%"],
        "name_hints":   ["material", "raw_material", "วัตถุดิบ", "lot", "lot_number", "ล็อต", "item", "รายการ"],
        "status_hints": ["status", "result", "สถานะ", "ผล", "inspection", "accept", "reject", "ผ่าน"],
        "date_hints":   ["date", "receive_date", "วันที่", "วันรับ", "received", "inspect_date"],
        "chart_primary":  "status_pie",
        "chart_secondary": "trend",
        "kpi_label": "อัตราผ่านเกณฑ์วัตถุดิบ",
        "summary_cols": ["name_hints", "status_hints", "date_hints"],
    },
    "03_Technical": {
        "title": "รายงาน Technical QA",
        "score_hints":  ["conformance", "pass_rate", "คะแนน", "actual", "measured", "value", "ค่า", "result"],
        "name_hints":   ["product", "spec_name", "test_name", "ผลิตภัณฑ์", "รายการ", "parameter", "spec"],
        "status_hints": ["status", "result", "conform", "สถานะ", "ผ่าน", "ไม่ผ่าน", "accept"],
        "date_hints":   ["date", "test_date", "วันที่", "วันทดสอบ", "production_date"],
        "chart_primary":  "status_pie",
        "chart_secondary": "bar_score_by_name",
        "kpi_label": "อัตรา Conformance",
        "summary_cols": ["name_hints", "status_hints"],
    },
    "04_Hygiene": {
        "title": "รายงาน Hygiene Monitoring",
        "score_hints":  ["cfu", "count", "colony", "จำนวน", "ค่า", "value", "reading", "bacteria"],
        "name_hints":   ["area", "zone", "location", "จุด", "พื้นที่", "swab_point", "station", "สถานี"],
        "status_hints": ["status", "result", "สถานะ", "ผล", "pass", "clean", "ผ่าน", "สะอาด"],
        "date_hints":   ["date", "check_date", "วันที่", "วันตรวจ", "sample_date"],
        "chart_primary":  "status_pie",
        "chart_secondary": "bar_area",
        "kpi_label": "อัตราจุดสะอาด (Hygiene Pass Rate)",
        "summary_cols": ["name_hints", "score_hints", "status_hints"],
    },
    "05_Pest_Control": {
        "title": "รายงาน Pest Control",
        "score_hints":  ["count", "จำนวน", "pest_count", "quantity", "found", "พบ"],
        "name_hints":   ["area", "station", "station_id", "จุด", "สถานี", "pest_type", "แมลง", "location"],
        "status_hints": ["status", "action", "สถานะ", "ดำเนินการ", "พบ", "result", "level"],
        "date_hints":   ["date", "inspect_date", "วันที่", "วันตรวจ", "check_date"],
        "chart_primary":  "pest_bar",
        "chart_secondary": "trend",
        "kpi_label": "สถานีที่ตรวจไม่พบแมลง (%)",
        "summary_cols": ["name_hints", "score_hints", "status_hints"],
    },
    "06_Monitor": {
        "title": "รายงาน Environmental Monitoring",
        "score_hints":  ["value", "ค่า", "temperature", "temp", "humidity", "อุณหภูมิ", "ความชื้น", "reading", "actual"],
        "name_hints":   ["parameter", "location", "area", "จุดตรวจ", "พารามิเตอร์", "sensor", "point", "ชื่อ"],
        "status_hints": ["status", "in_spec", "สถานะ", "ผ่าน", "เกิน", "result", "alarm"],
        "date_hints":   ["date", "record_date", "วันที่", "time", "เวลา", "timestamp", "datetime"],
        "chart_primary":  "status_pie",
        "chart_secondary": "trend",
        "kpi_label": "อัตราค่าอยู่ในเกณฑ์",
        "summary_cols": ["name_hints", "score_hints", "status_hints"],
    },
    "07_Lab_Micro": {
        "title": "รายงานผล Lab จุลชีววิทยา",
        "score_hints":  ["result", "count", "cfu", "organism_count", "ผล", "จำนวน", "value", "detected"],
        "name_hints":   ["organism", "test", "sample", "ตัวอย่าง", "การทดสอบ", "เชื้อ", "bacteria", "product"],
        "status_hints": ["status", "pass_fail", "สถานะ", "ผ่าน", "เกิน", "conform", "result"],
        "date_hints":   ["date", "sample_date", "วันที่", "วันเก็บตัวอย่าง", "test_date", "analysis_date"],
        "chart_primary":  "status_pie",
        "chart_secondary": "bar_score_by_name",
        "kpi_label": "อัตราผ่านเกณฑ์จุลชีววิทยา",
        "summary_cols": ["name_hints", "score_hints", "status_hints"],
    },
    "08_Lab_Chem": {
        "title": "รายงานผล Lab เคมี",
        "score_hints":  ["result", "value", "ค่า", "actual", "measured", "concentration", "content"],
        "name_hints":   ["analyte", "parameter", "test", "ตัวอย่าง", "พารามิเตอร์", "test_name", "sample", "product"],
        "status_hints": ["status", "in_spec", "สถานะ", "ผ่าน", "conform", "accept", "result"],
        "date_hints":   ["date", "sample_date", "วันที่", "analysis_date", "test_date"],
        "chart_primary":  "status_pie",
        "chart_secondary": "chem_bar",
        "kpi_label": "อัตราผ่านเกณฑ์เคมี",
        "summary_cols": ["name_hints", "score_hints", "status_hints"],
    },
    "09_Sensory": {
        "title": "รายงานประเมินประสาทสัมผัส",
        "score_hints":  ["score", "คะแนน", "rating", "point", "ค่า", "appearance", "taste", "smell",
                         "texture", "color", "สี", "กลิ่น", "รสชาติ", "เนื้อสัมผัส", "รูปลักษณ์"],
        "name_hints":   ["product", "attribute", "หัวข้อ", "ผลิตภัณฑ์", "evaluator", "ผู้ประเมิน",
                         "criteria", "category", "item"],
        "status_hints": ["status", "result", "สถานะ", "ผ่าน", "ยอมรับ", "accept", "reject"],
        "date_hints":   ["date", "eval_date", "วันที่", "วันประเมิน", "session_date"],
        "chart_primary":  "sensory_radar",
        "chart_secondary": "bar_score_by_name",
        "kpi_label": "คะแนนประสาทสัมผัสเฉลี่ย",
        "summary_cols": ["name_hints", "score_hints"],
    },
    "10_Load": {
        "title": "รายงานตรวจสอบการบรรทุก / ส่งออก",
        "score_hints":  ["quantity", "จำนวน", "weight", "น้ำหนัก", "amount", "volume", "มูลค่า"],
        "name_hints":   ["shipment", "destination", "lot", "ปลายทาย", "ปลายทาง", "เลขที่", "product",
                         "container", "truck", "vehicle"],
        "status_hints": ["status", "result", "สถานะ", "ผ่าน", "ผล", "inspection_result", "approved"],
        "date_hints":   ["date", "ship_date", "วันที่", "วันส่ง", "วันตรวจ", "dispatch_date", "load_date"],
        "chart_primary":  "status_pie",
        "chart_secondary": "trend",
        "kpi_label": "อัตราผ่านการตรวจ (Load QA)",
        "summary_cols": ["name_hints", "status_hints", "date_hints"],
    },
    "11_Data_Regulatory": {
        "title": "รายงานเอกสารกำกับดูแล (Regulatory)",
        "score_hints":  ["days_left", "อายุ", "validity", "days_remaining", "days", "วัน"],
        "name_hints":   ["document", "doc_name", "certificate", "เอกสาร", "ใบอนุญาต", "cert_name",
                         "license", "permit", "ใบรับรอง", "name", "ชื่อ"],
        "status_hints": ["status", "สถานะ", "valid", "expired", "active", "หมดอายุ", "บังคับ"],
        "date_hints":   ["expiry_date", "expire_date", "valid_until", "วันหมดอายุ", "issued_date",
                         "expiry", "expiration", "valid_to"],
        "chart_primary":  "doc_status",
        "chart_secondary": "doc_timeline",
        "kpi_label": "เอกสารที่ยังมีผลบังคับใช้",
        "summary_cols": ["name_hints", "status_hints", "date_hints"],
    },
}


# ════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ════════════════════════════════════════════════════════════

def _find_col(df: pd.DataFrame, hints: list[str]) -> str | None:
    """ค้นหาคอลัมน์แรกที่ตรงกับ hint ใดก็ได้ (case-insensitive, partial match)"""
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for hint in hints:
        for cl, c in cols_lower.items():
            if hint.lower() in cl:
                return c
    return None


def _detect_cols(df: pd.DataFrame, cfg: dict) -> dict:
    """ตรวจหาคอลัมน์ทุกประเภทสำหรับหน่วยงานนี้"""
    return {
        "score_col":  _find_col(df, cfg.get("score_hints", [])),
        "name_col":   _find_col(df, cfg.get("name_hints", [])),
        "status_col": _find_col(df, cfg.get("status_hints", [])),
        "date_col":   _find_col(df, cfg.get("date_hints", [])),
    }


def _get_best_table(tables: list[pd.DataFrame], dept_key: str) -> pd.DataFrame | None:
    """เลือกตารางที่เหมาะสมที่สุดสำหรับหน่วยงาน (ให้คะแนนตาม column match)"""
    if not tables:
        return None
    cfg = DEPT_CONFIGS.get(dept_key, {})
    best_score, best_table = -1, None
    for df in tables:
        if df.empty or len(df.columns) < 2:
            continue
        score = len(df) * 0.1  # base = จำนวนแถว (น้ำหนักน้อย)
        cols_text = " ".join(str(c) for c in df.columns).lower()
        for hint_key in ["score_hints", "name_hints", "status_hints", "date_hints"]:
            for hint in cfg.get(hint_key, []):
                if hint.lower() in cols_text:
                    score += 15
        if score > best_score:
            best_score, best_table = score, df
    return best_table


def _clean_table(df: pd.DataFrame) -> pd.DataFrame:
    """ทำความสะอาด DataFrame จาก HTML (ลบแถว header ซ้ำ, Unnamed cols)"""
    df = df.dropna(how="all").copy()
    # ถ้า row แรกดูเหมือน header → ยกขึ้น
    if df.shape[0] > 1:
        first_row = df.iloc[0].astype(str)
        num_unnamed = first_row.str.contains("Unnamed", na=False).sum()
        if num_unnamed > len(df.columns) * 0.5:
            df.columns = df.iloc[0].astype(str).str.strip()
            df = df.iloc[1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    return df.reset_index(drop=True)


# ════════════════════════════════════════════════════════════
# SUMMARY METRICS
# ════════════════════════════════════════════════════════════

PASS_KEYWORDS = ["pass", "ok", "valid", "clean", "conform", "active", "accept",
                 "ผ่าน", "สะอาด", "ยอมรับ", "บังคับ", "ปกติ"]

def _is_pass(val: str) -> bool:
    v = str(val).lower()
    return any(k in v for k in PASS_KEYWORDS)


def _compute_pass_rate(df: pd.DataFrame, cols: dict, dept_key: str) -> tuple[float, int, int]:
    """คำนวณ Pass Rate จากคอลัมน์ status หรือ score"""
    total = len(df)
    status_col = cols["status_col"]
    score_col  = cols["score_col"]
    cfg_dept   = DEPARTMENTS[dept_key]

    if status_col and status_col in df.columns:
        pass_count = df[status_col].astype(str).apply(_is_pass).sum()
        return round(pass_count / total * 100, 1) if total else 0.0, int(pass_count), total

    if score_col and score_col in df.columns:
        vals = pd.to_numeric(df[score_col], errors="coerce").dropna()
        if len(vals):
            thr = cfg_dept.get("threshold_green", 85)
            pass_count = int((vals >= thr).sum())
            avg = round(float(vals.mean()), 1)
            return avg, pass_count, total

    return 0.0, 0, total


def _render_summary(df: pd.DataFrame, cols: dict, dept_key: str):
    """แสดง Metric Cards สรุปหน่วยงาน"""
    cfg_dept = DEPARTMENTS[dept_key]
    cfg_html = DEPT_CONFIGS.get(dept_key, {})
    pass_rate, pass_count, total = _compute_pass_rate(df, cols, dept_key)
    thr_g = cfg_dept.get("threshold_green", 85)
    thr_y = cfg_dept.get("threshold_yellow", 70)
    traffic = "green" if pass_rate >= thr_g else ("yellow" if pass_rate >= thr_y else "red")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 จำนวนรายการ", f"{total:,}")
    c2.metric(cfg_html.get("kpi_label", "KPI Score"), f"{pass_rate}%")
    c3.metric("✅ ผ่านเกณฑ์", f"{pass_count:,}")
    c4.markdown(
        f'<div style="background:{TC[traffic]};border-radius:10px;padding:14px;'
        f'text-align:center;color:{"white" if traffic!="yellow" else "#333"};margin-top:4px">'
        f'<div style="font-size:1.3rem">{TRAFFIC[traffic]["emoji"]}</div>'
        f'<div style="font-weight:700">{TRAFFIC[traffic]["label"]}</div></div>',
        unsafe_allow_html=True
    )
    return pass_rate, traffic


# ════════════════════════════════════════════════════════════
# CHART FUNCTIONS
# ════════════════════════════════════════════════════════════

STATUS_COLOR_MAP = {
    "PASS": "#00C853", "OK": "#00C853", "VALID": "#00C853", "CLEAN": "#00C853",
    "CONFORM": "#00C853", "ACTIVE": "#00C853", "ACCEPT": "#00C853",
    "ผ่าน": "#00C853", "สะอาด": "#00C853", "ยอมรับ": "#00C853",
    "FAIL": "#D50000", "REJECT": "#D50000", "EXPIRED": "#D50000",
    "ไม่ผ่าน": "#D50000", "หมดอายุ": "#D50000",
    "WARNING": "#FFD600", "EXPIRING_SOON": "#FFD600", "PENDING": "#FFD600",
    "เฝ้าระวัง": "#FFD600", "ใกล้หมดอายุ": "#FFD600",
}


def _color_for_status(s: str) -> str:
    return STATUS_COLOR_MAP.get(str(s).upper(), STATUS_COLOR_MAP.get(str(s), "#90A4AE"))


def _chart_status_pie(df: pd.DataFrame, status_col: str, dept_key: str):
    """Pie chart — สัดส่วนสถานะ"""
    vc = df[status_col].astype(str).value_counts().reset_index()
    vc.columns = ["Status", "Count"]
    color_map = {s: _color_for_status(s) for s in vc["Status"]}
    fig = px.pie(vc, names="Status", values="Count", color="Status",
                 color_discrete_map=color_map,
                 title=f"สัดส่วนสถานะ — {DEPARTMENTS[dept_key]['name_th']}")
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)


def _chart_bar_score_by_name(df: pd.DataFrame, score_col: str, name_col: str, dept_key: str, title_prefix: str = ""):
    """Bar chart — คะแนนเฉลี่ยแต่ละรายการ"""
    try:
        df2 = df[[name_col, score_col]].copy()
        df2[score_col] = pd.to_numeric(df2[score_col], errors="coerce")
        df2 = df2.dropna().groupby(name_col)[score_col].mean().reset_index()
        df2.columns = ["ชื่อ", "คะแนน"]
        df2 = df2.sort_values("คะแนน").tail(20)
        thr_g = DEPARTMENTS[dept_key].get("threshold_green", 85)
        thr_y = DEPARTMENTS[dept_key].get("threshold_yellow", 70)
        colors = ["#00C853" if v >= thr_g else "#FFD600" if v >= thr_y else "#D50000"
                  for v in df2["คะแนน"]]
        fig = go.Figure(go.Bar(
            x=df2["คะแนน"], y=df2["ชื่อ"], orientation="h",
            marker_color=colors,
            text=df2["คะแนน"].round(1), textposition="outside"
        ))
        fig.add_vline(x=thr_g, line_dash="dot", line_color="green", annotation_text="เกณฑ์ผ่าน")
        prefix = f"{title_prefix} — " if title_prefix else ""
        fig.update_layout(
            height=max(280, len(df2) * 28),
            title=f"{prefix}{DEPARTMENTS[dept_key]['name_th']}",
            xaxis_title="คะแนน",
            margin=dict(l=20, r=60, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.caption(f"ไม่สามารถสร้างกราฟได้: {e}")


def _chart_trend(df: pd.DataFrame, date_col: str, score_col: str | None, status_col: str | None, dept_key: str):
    """Line chart — แนวโน้มตามเวลา"""
    try:
        if score_col and score_col in df.columns:
            df2 = df[[date_col, score_col]].copy()
            df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
            df2[score_col] = pd.to_numeric(df2[score_col], errors="coerce")
            df2 = df2.dropna().groupby(df2[date_col].dt.date)[score_col].mean().reset_index()
            df2.columns = ["วันที่", "ค่าเฉลี่ย"]
            y_col, y_label = "ค่าเฉลี่ย", score_col
        elif status_col and status_col in df.columns:
            df2 = df[[date_col, status_col]].copy()
            df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
            df2["pass"] = df2[status_col].astype(str).apply(_is_pass)
            df2 = df2.dropna(subset=[date_col]).groupby(df2[date_col].dt.date)["pass"].mean().mul(100).reset_index()
            df2.columns = ["วันที่", "อัตราผ่านเกณฑ์ (%)"]
            y_col, y_label = "อัตราผ่านเกณฑ์ (%)", "อัตราผ่านเกณฑ์ (%)"
        else:
            return

        if len(df2) < 2:
            return

        fig = px.line(df2, x="วันที่", y=y_col, markers=True,
                      title=f"แนวโน้ม — {DEPARTMENTS[dept_key]['name_th']}")
        fig.add_hline(y=DEPARTMENTS[dept_key].get("threshold_green", 85),
                      line_dash="dot", line_color="green", annotation_text="เกณฑ์มาตรฐาน")
        fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass


def _chart_sensory_radar(df: pd.DataFrame, name_col: str, score_col: str, dept_key: str):
    """Radar chart — สำหรับ Sensory หรือ Multi-attribute"""
    try:
        df2 = df[[name_col, score_col]].copy()
        df2[score_col] = pd.to_numeric(df2[score_col], errors="coerce")
        summary = df2.dropna().groupby(name_col)[score_col].mean()
        names  = summary.index.tolist()
        scores = summary.values.tolist()

        if len(names) < 3:
            _chart_bar_score_by_name(df, score_col, name_col, dept_key, "คะแนนประสาทสัมผัส")
            return

        max_score = max(scores) if scores else 10
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=scores + [scores[0]], theta=names + [names[0]],
            fill="toself", fillcolor="rgba(26,35,126,0.15)",
            line=dict(color="#1a237e", width=2), name="คะแนนเฉลี่ย"
        ))
        thr = DEPARTMENTS[dept_key].get("threshold_green", 7)
        fig.add_trace(go.Scatterpolar(
            r=[thr] * len(names) + [thr], theta=names + [names[0]],
            mode="lines", line=dict(color="green", width=1, dash="dot"),
            name=f"เกณฑ์ผ่าน ({thr})"
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, max(max_score * 1.2, thr * 1.2)])),
            title=f"Sensory Radar — {DEPARTMENTS[dept_key]['name_th']}",
            height=350, margin=dict(l=40, r=40, t=40, b=20), showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        if score_col and name_col:
            _chart_bar_score_by_name(df, score_col, name_col, dept_key, "คะแนนประสาทสัมผัส")


def _chart_pest_bar(df: pd.DataFrame, name_col: str, score_col: str | None, status_col: str | None, dept_key: str):
    """Bar chart — จำนวนแมลง/สัตว์รบกวนต่อสถานี"""
    try:
        if score_col and name_col:
            df2 = df[[name_col, score_col]].copy()
            df2[score_col] = pd.to_numeric(df2[score_col], errors="coerce").fillna(0)
            df2 = df2.groupby(name_col)[score_col].sum().reset_index()
            df2.columns = ["สถานี", "จำนวนที่พบ"]
            df2 = df2.sort_values("จำนวนที่พบ", ascending=False).head(20)
            colors = ["#D50000" if v > 0 else "#00C853" for v in df2["จำนวนที่พบ"]]
            fig = go.Figure(go.Bar(
                x=df2["สถานี"], y=df2["จำนวนที่พบ"],
                marker_color=colors, text=df2["จำนวนที่พบ"], textposition="outside"
            ))
            fig.update_layout(
                title=f"จำนวนแมลง/สัตว์รบกวนต่อสถานี — {DEPARTMENTS[dept_key]['name_th']}",
                height=320, margin=dict(l=20, r=20, t=40, b=80),
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
        elif status_col:
            _chart_status_pie(df, status_col, dept_key)
    except Exception as e:
        st.caption(f"ไม่สามารถสร้างกราฟได้: {e}")


def _chart_doc_timeline(df: pd.DataFrame, name_col: str, date_col: str, dept_key: str):
    """แสดงวันหมดอายุเอกสาร Regulatory"""
    try:
        df2 = df[[name_col, date_col]].dropna().copy()
        df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
        df2 = df2.dropna().sort_values(date_col)
        if df2.empty:
            return
        now = pd.Timestamp.now()
        df2["days_left"] = (df2[date_col] - now).dt.days
        df2["color"] = df2["days_left"].apply(
            lambda d: "#D50000" if d < 0 else "#FFD600" if d < 90 else "#00C853"
        )
        df2["label"] = df2["days_left"].apply(
            lambda d: f"หมดอายุแล้ว {-d} วัน" if d < 0 else
                      f"อีก {d} วัน" if d < 90 else f"อีก {d} วัน ✅"
        )
        fig = go.Figure(go.Bar(
            x=df2["days_left"],
            y=df2[name_col].astype(str).str[:30],
            orientation="h",
            marker_color=df2["color"],
            text=df2["label"], textposition="outside"
        ))
        fig.add_vline(x=0, line_dash="solid", line_color="black", line_width=2)
        fig.add_vline(x=90, line_dash="dot", line_color="orange", annotation_text="90 วัน")
        fig.update_layout(
            title=f"วันที่เหลือก่อนหมดอายุ — {DEPARTMENTS[dept_key]['name_th']}",
            height=max(300, len(df2) * 30),
            xaxis_title="จำนวนวันที่เหลือ",
            margin=dict(l=20, r=100, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.caption(f"ไม่สามารถสร้างกราฟได้: {e}")


def _chart_chem_bar(df: pd.DataFrame, name_col: str, score_col: str, dept_key: str):
    """Bar chart พร้อม spec range — สำหรับ Lab Chem"""
    try:
        # ถ้ามีคอลัมน์ min/max spec → แสดง range
        spec_max_col = _find_col(df, ["max", "upper", "limit", "spec_max", "usl", "maximum"])
        spec_min_col = _find_col(df, ["min", "lower", "spec_min", "lsl", "minimum"])

        df2 = df[[name_col, score_col]].copy()
        df2[score_col] = pd.to_numeric(df2[score_col], errors="coerce")
        df2 = df2.dropna().groupby(name_col)[score_col].mean().reset_index()
        df2.columns = ["รายการ", "ค่าเฉลี่ย"]
        df2 = df2.head(20)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df2["รายการ"], y=df2["ค่าเฉลี่ย"],
            name="ค่าวัดได้", marker_color="#1976D2",
            text=df2["ค่าเฉลี่ย"].round(3), textposition="outside"
        ))
        fig.update_layout(
            title=f"ผลการวิเคราะห์เคมี — {DEPARTMENTS[dept_key]['name_th']}",
            height=320, margin=dict(l=20, r=20, t=40, b=80),
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        if name_col and score_col:
            _chart_bar_score_by_name(df, score_col, name_col, dept_key, "ผลเคมี")


# ════════════════════════════════════════════════════════════
# DEPT-SPECIFIC TABLE HIGHLIGHTS
# ════════════════════════════════════════════════════════════

def _highlight_table(df: pd.DataFrame, status_col: str | None) -> pd.DataFrame:
    """สร้าง DataFrame พร้อม column สถานะเน้นสี (ใช้ st.dataframe column_config)"""
    return df


def _render_table_section(df: pd.DataFrame, tables: list[pd.DataFrame], dept_key: str, cols: dict):
    """แสดงตารางข้อมูล — ถ้ามีหลายตาราง ใช้ tabs"""
    if len(tables) > 1:
        st.subheader(f"📊 ตารางข้อมูลทั้งหมดในรายงาน ({len(tables)} ตาราง)")
        tab_labels = [f"ตาราง {i + 1}  ({len(t):,} แถว)" for i, t in enumerate(tables)]
        tab_objs = st.tabs(tab_labels)
        for tab_obj, t in zip(tab_objs, tables):
            with tab_obj:
                st.dataframe(t, use_container_width=True, height=300)
    else:
        st.subheader("📋 ตารางข้อมูล")
        st.dataframe(df, use_container_width=True, height=360)
        st.download_button(
            "⬇️ ดาวน์โหลด CSV",
            df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
            f"{dept_key}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )


# ════════════════════════════════════════════════════════════
# PREBUILT DASHBOARD DETECTION & RENDERING
# ════════════════════════════════════════════════════════════

def _is_prebuilt_dashboard(html_str: str) -> bool:
    """ตรวจว่า HTML เป็น Dashboard สำเร็จรูป (มี Chart.js / canvas / D3)"""
    markers = ["<canvas", "new Chart(", "chart.umd", "Chart.js",
               "chartjs", "d3.js", "echarts", "highcharts", "apexcharts"]
    hl = html_str.lower()
    return sum(1 for m in markers if m.lower() in hl) >= 2


def _extract_summary_from_html(html_str: str) -> str | None:
    """ดึง summary จาก sr-only / h1 / h2 / aria-label"""
    patterns = [
        r'class=["\'][^"\']*sr-only[^"\']*["\'][^>]*>(.*?)</\w+>',
        r'<h[12][^>]*>(.*?)</h[12]>',
        r'aria-label=["\']([^"\']{20,})["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html_str, re.DOTALL | re.IGNORECASE)
        if m:
            text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if len(text) > 10:
                return text
    return None


def _extract_metrics_from_prebuilt(html_str: str) -> list[dict]:
    """
    ดึงตัวเลข KPI จาก HTML สำเร็จรูป
    คืนค่า list ของ {label, value, color}
    """
    metrics = []

    # ── 1. ดึงจากตัวเลขใน donut-pct / donut-lbl ──────
    pct_blocks = re.findall(
        r'class=["\']donut-pct["\'][^>]*style=["\'][^"\']*color:([^;"\';]+)[^>]*>(.*?)</div>'
        r'.*?class=["\']donut-lbl["\'][^>]*>(.*?)</div>',
        html_str, re.DOTALL
    )
    for color, pct, lbl in pct_blocks:
        metrics.append({
            "label": re.sub(r'<[^>]+>', '', lbl).strip(),
            "value": re.sub(r'<[^>]+>', '', pct).strip(),
            "color": color.strip()
        })

    # ── 2. ดึงจาก card-title + ตัวเลขถัดมา ──────────
    if not metrics:
        titles = re.findall(r'class=["\']card-title["\'][^>]*>(.*?)</div>', html_str, re.DOTALL)
        for t in titles[:4]:
            clean = re.sub(r'<[^>]+>', '', t).strip()
            if clean:
                metrics.append({"label": clean, "value": "—", "color": "#1a237e"})

    return metrics[:6]


def _render_prebuilt_dashboard(dept_key: str, html_str: str, tables: list[pd.DataFrame]):
    """
    แสดงผล HTML Dashboard สำเร็จรูป (มี Chart.js)
    → แสดง HTML โดยตรง + สรุปตาราง (ถ้ามี)
    """
    dept_cfg = DEPARTMENTS[dept_key]

    # ── Summary text ────────────────────────────────────
    summary = _extract_summary_from_html(html_str)
    if summary:
        st.info(f"📋 {summary}")

    # ── Metric cards จาก HTML ───────────────────────────
    metrics = _extract_metrics_from_prebuilt(html_str)
    if metrics:
        cols_m = st.columns(min(len(metrics), 4))
        for i, m in enumerate(metrics[:4]):
            with cols_m[i]:
                color = m.get("color", "#1a237e")
                if not color.startswith("#"):
                    color = "#1a237e"
                st.markdown(
                    f'<div style="border-radius:10px;border:2px solid {color};'
                    f'padding:12px;text-align:center;background:#fafafa">'
                    f'<div style="font-size:1.6rem;font-weight:700;color:{color}">{m["value"]}</div>'
                    f'<div style="font-size:0.8rem;color:#555;margin-top:4px">{m["label"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        st.write("")

    st.divider()

    # ── Dashboard HTML ───────────────────────────────────
    st.markdown("#### 📊 รายงาน Dashboard")
    _render_raw_html(html_str)

    # ── ตารางสรุป (ถ้าพบ) ────────────────────────────────
    if tables:
        st.divider()
        st.markdown("#### 📋 ตารางข้อมูลในรายงาน")
        tab_labels = [f"ตาราง {i+1} ({len(t):,} แถว)" for i, t in enumerate(tables)]
        if len(tables) == 1:
            st.dataframe(tables[0], use_container_width=True)
            st.download_button(
                "⬇️ ดาวน์โหลด CSV",
                tables[0].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                f"{dept_key}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv", "text/csv"
            )
        else:
            tab_objs = st.tabs(tab_labels)
            for tab_obj, t in zip(tab_objs, tables):
                with tab_obj:
                    st.dataframe(t, use_container_width=True)


# ════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTION
# ════════════════════════════════════════════════════════════

def render_html_dashboard(dept_key: str, html_str: str):
    """
    Entry point หลัก — เรียกจาก Tab 3 ใน app.py
    รองรับ 2 โหมด:
      1. HTML Dashboard สำเร็จรูป (Chart.js) → แสดงตรงๆ
      2. HTML ตารางข้อมูล → วิเคราะห์และสร้างกราฟ
    """
    cfg = DEPT_CONFIGS.get(dept_key, {})
    dept_name = DEPARTMENTS[dept_key]["name_th"]
    dept_icon = DEPARTMENTS[dept_key]["icon"]

    st.markdown(f"### {dept_icon} {cfg.get('title', dept_name)}")
    st.caption("📄 วิเคราะห์จากไฟล์ HTML ที่อัปโหลด")

    # ── Parse tables ─────────────────────────────────────
    try:
        raw_tables = pd.read_html(io.StringIO(html_str))
        tables = [_clean_table(t) for t in raw_tables if not t.empty]
    except Exception:
        tables = []

    # ── ตรวจว่าเป็น Dashboard สำเร็จรูปหรือไม่ ──────────
    if _is_prebuilt_dashboard(html_str):
        st.markdown(
            '<span style="background:#e3f2fd;color:#1565C0;border-radius:12px;'
            'padding:3px 10px;font-size:0.82rem">📊 Dashboard สำเร็จรูป (Chart.js)</span>',
            unsafe_allow_html=True
        )
        st.write("")
        _render_prebuilt_dashboard(dept_key, html_str, tables)
        return

    # ── HTML ตารางข้อมูล → วิเคราะห์แบบละเอียด ──────────
    if not tables:
        st.warning("⚠️ ไม่พบตารางข้อมูลในไฟล์ HTML — แสดงรายงานต้นฉบับ")
        _render_raw_html(html_str)
        return

    df = _get_best_table(tables, dept_key)
    if df is None or df.empty:
        st.warning("⚠️ ไม่พบข้อมูลที่ประมวลผลได้")
        _render_raw_html(html_str)
        return

    cols = _detect_cols(df, cfg)
    pass_rate, traffic = _render_summary(df, cols, dept_key)

    with st.expander("🔍 คอลัมน์ที่ระบบตรวจพบ", expanded=False):
        col_info = {
            "Score/ค่า": cols["score_col"] or "❌ ไม่พบ",
            "ชื่อ/รายการ": cols["name_col"] or "❌ ไม่พบ",
            "สถานะ": cols["status_col"] or "❌ ไม่พบ",
            "วันที่": cols["date_col"] or "❌ ไม่พบ",
        }
        cc1, cc2, cc3, cc4 = st.columns(4)
        for col_w, (k, v) in zip([cc1, cc2, cc3, cc4], col_info.items()):
            col_w.info(f"**{k}**\n\n`{v}`")

    st.divider()

    chart_primary   = cfg.get("chart_primary", "status_pie")
    chart_secondary = cfg.get("chart_secondary", "trend")
    score_col  = cols["score_col"]
    name_col   = cols["name_col"]
    status_col = cols["status_col"]
    date_col   = cols["date_col"]

    col_left, col_right = st.columns(2)

    with col_left:
        if chart_primary == "bar_score_by_name" and score_col and name_col:
            _chart_bar_score_by_name(df, score_col, name_col, dept_key)
        elif chart_primary == "sensory_radar" and score_col and name_col:
            _chart_sensory_radar(df, name_col, score_col, dept_key)
        elif chart_primary == "pest_bar":
            _chart_pest_bar(df, name_col, score_col, status_col, dept_key)
        elif chart_primary == "doc_status" and status_col:
            _chart_status_pie(df, status_col, dept_key)
        elif status_col:
            _chart_status_pie(df, status_col, dept_key)
        elif score_col and name_col:
            _chart_bar_score_by_name(df, score_col, name_col, dept_key)
        else:
            cat_cols = df.select_dtypes(include="object").columns.tolist()
            if cat_cols:
                vc = df[cat_cols[0]].value_counts().head(15).reset_index()
                vc.columns = ["ค่า", "จำนวน"]
                fig = px.bar(vc, x="ค่า", y="จำนวน", title=f"การกระจายข้อมูล — {dept_name}")
                fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=60), xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

    with col_right:
        if chart_secondary == "trend" and date_col:
            _chart_trend(df, date_col, score_col, status_col, dept_key)
        elif chart_secondary == "bar_score_by_name" and score_col and name_col:
            _chart_bar_score_by_name(df, score_col, name_col, dept_key, "Top รายการ")
        elif chart_secondary == "doc_timeline" and name_col and date_col:
            _chart_doc_timeline(df, name_col, date_col, dept_key)
        elif chart_secondary == "chem_bar" and name_col and score_col:
            _chart_chem_bar(df, name_col, score_col, dept_key)
        elif chart_secondary == "bar_area" and name_col and (score_col or status_col):
            if score_col:
                _chart_bar_score_by_name(df, score_col, name_col, dept_key, "ค่าตามพื้นที่")
            elif status_col:
                try:
                    df2 = df[[name_col, status_col]].copy()
                    df2["pass"] = df2[status_col].astype(str).apply(_is_pass).astype(int)
                    df2 = df2.groupby(name_col)["pass"].mean().mul(100).reset_index()
                    df2.columns = ["พื้นที่", "อัตราผ่าน (%)"]
                    fig = px.bar(df2, x="พื้นที่", y="อัตราผ่าน (%)",
                                 title=f"อัตราผ่านเกณฑ์ต่อพื้นที่ — {dept_name}")
                    fig.update_layout(height=300, xaxis_tickangle=-30)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass
        elif date_col and (score_col or status_col):
            _chart_trend(df, date_col, score_col, status_col, dept_key)

    st.divider()
    _render_table_section(df, tables, dept_key, cols)

    st.divider()
    with st.expander("🌐 ดูรายงาน HTML ต้นฉบับ", expanded=False):
        st.caption(f"ไฟล์ HTML ต้นฉบับ ({len(html_str):,} ตัวอักษร)")
        _render_raw_html(html_str)


def _render_raw_html(html_str: str):
    """Render HTML ต้นฉบับใน iframe"""
    components.html(html_str, height=650, scrolling=True)


def extract_html_kpi(html_str: str) -> float | None:
    """
    ดึงค่า KPI % หลักจาก HTML Dashboard (Chart.js)
    ค้นหาตัวเลขเปอร์เซ็นต์ที่อยู่ใกล้ keyword "ผ่านเกณฑ์" / "pass rate" / "อัตรา"
    """
    import re

    # ── Strategy 1: % อยู่ติดกับ keyword ผ่านเกณฑ์ ──────────
    kw_patterns = [
        r'(\d{1,3}\.?\d*)\s*%(?:[^<]{0,30})(?:ผ่านเกณฑ์|อัตราผ่าน|pass\s*rate|compliance)',
        r'(?:ผ่านเกณฑ์|อัตราผ่าน|pass\s*rate|compliance)(?:[^<]{0,60})(\d{1,3}\.?\d*)\s*%',
        r'(?:อัตราผ่านเกณฑ์|Pass\s*Rate|Compliance\s*Rate)(?:<[^>]+>|\s){0,5}(\d{1,3}\.?\d*)',
    ]
    for pat in kw_patterns:
        m = re.search(pat, html_str, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                val = float(m.group(1))
                if 50.0 <= val <= 100.0:
                    return val
            except Exception:
                pass

    # ── Strategy 2: aria-label ที่มี pass/ND/ผ่าน ────────────
    for aria_m in re.finditer(r'aria-label=["\']([^"\']{10,})["\']', html_str, re.IGNORECASE):
        text = aria_m.group(1)
        if any(kw in text.lower() for kw in ["pass", "nd", "ผ่าน", "not detected", "ไม่พบ"]):
            pct_m = re.search(r'(\d{1,3}\.?\d*)\s*%', text)
            if pct_m:
                try:
                    val = float(pct_m.group(1))
                    if 50.0 <= val <= 100.0:
                        return val
                except Exception:
                    pass

    # ── Strategy 3: sr-only / h2 summary text ────────────────
    summary = _extract_summary_from_html(html_str) or ""
    pct_matches = re.findall(r'(\d{1,3}\.?\d*)\s*%', summary)
    for p in pct_matches:
        try:
            val = float(p)
            if 50.0 <= val <= 100.0:
                return val
        except Exception:
            pass

    # ── Strategy 4: หา % ทั้งหมด แล้วเลือกค่าที่น่าจะเป็น KPI ─
    all_pcts = re.findall(r'(\d{1,3}\.?\d+)%', html_str)
    candidates = []
    for p in all_pcts:
        try:
            val = float(p)
            if 50.0 <= val < 100.0:  # KPI จริงมักไม่ใช่ 100% พอดี
                candidates.append(val)
        except Exception:
            pass
    if candidates:
        # เลือก median
        candidates.sort()
        return candidates[len(candidates) // 2]

    return None
