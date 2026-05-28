# app.py — QA CPRAM Executive Dashboard
# รัน local:  streamlit run app.py
# Deploy:     Streamlit Cloud (เชื่อม GitHub)
# ============================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from config import APP_TITLE, APP_ICON, DEPARTMENTS, GROUPS, TRAFFIC
from data_processor import (
    compute_factory_kpi, compute_export_readiness,
    compute_domestic_quality, compute_dept_kpi,
    load_uploaded_file, save_snapshot, load_local_html_raw,
    compute_dept_rsi, compute_all_rsi,
)
from linkage_engine import run_linkage_checks, alerts_to_dataframe
from gdrive_handler import (
    get_gdrive_service, get_root_folder_id,
    upload_file_to_drive, load_all_from_drive
)
from html_renderer import render_html_dashboard
from exec_dashboard import build_exec_html
import streamlit.components.v1 as components

# ─── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE, page_icon=APP_ICON,
    layout="wide", initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main .block-container { padding-top: 1rem; }
h1 { color: #1a237e; font-size: 1.6rem !important; }
.tl-card { border-radius:12px; padding:14px 18px; margin:6px 0; color:white;
           font-weight:600; font-size:0.95rem; text-align:center; }
.tl-green  { background: linear-gradient(135deg,#00C853,#69F0AE); }
.tl-yellow { background: linear-gradient(135deg,#FFD600,#FFFF00); color:#333; }
.tl-red    { background: linear-gradient(135deg,#D50000,#FF6D00); }
.metric-box { background:#f5f5f5; border-radius:10px; padding:12px; text-align:center;
              border-left:5px solid #1a237e; margin-bottom:8px; }
.metric-num { font-size:2rem; font-weight:700; color:#1a237e; }
.metric-lbl { font-size:0.8rem; color:#555; }
.alert-critical { background:#ffebee; border-left:4px solid #D50000;
                  padding:8px 12px; border-radius:4px; margin:4px 0; }
.alert-high     { background:#fff8e1; border-left:4px solid #FFD600;
                  padding:8px 12px; border-radius:4px; margin:4px 0; }
.alert-info     { background:#e3f2fd; border-left:4px solid #1976D2;
                  padding:8px 12px; border-radius:4px; margin:4px 0; }
.upload-box { border: 2px dashed #1976D2; border-radius:16px; padding:30px;
              text-align:center; background:#f0f7ff; margin:12px 0; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# SESSION STATE + GOOGLE DRIVE CONNECTION
# ════════════════════════════════════════════════════════════

if "uploaded_override" not in st.session_state:
    st.session_state.uploaded_override = {}
if "html_content" not in st.session_state:
    st.session_state.html_content = {}      # dept_key → raw HTML string
if "html_kpi_scores" not in st.session_state:
    st.session_state.html_kpi_scores = {}   # dept_key → float KPI score จาก HTML

# โหลด HTML จาก local_data เข้า session_state อัตโนมัติ (ครั้งแรก)
if "local_html_loaded" not in st.session_state:
    from html_renderer import extract_html_kpi
    for _dk in DEPARTMENTS:
        if _dk not in st.session_state.html_content:
            _raw = load_local_html_raw(_dk)
            if _raw:
                st.session_state.html_content[_dk] = _raw
                _kpi = extract_html_kpi(_raw)
                if _kpi is not None:
                    st.session_state.html_kpi_scores[_dk] = _kpi
    st.session_state.local_html_loaded = True

# เชื่อม Google Drive ครั้งเดียวต่อ session
@st.cache_resource(show_spinner=False)
def _connect_gdrive():
    return get_gdrive_service()

gdrive     = _connect_gdrive()
root_id    = get_root_folder_id()
gdrive_ok  = gdrive is not None and bool(root_id)


# ─── โหลดข้อมูลทั้งหมด ─────────────────────────────────────
@st.cache_data(ttl=180, show_spinner="🔄 กำลังโหลดข้อมูลจาก Google Drive...")
def load_data_cached(root_id: str, _gdrive):
    from sample_data_generator import GENERATORS
    dept_keys = list(DEPARTMENTS.keys())

    # โหลดจาก Google Drive ก่อน
    drive_data = {}
    if _gdrive and root_id:
        drive_data = load_all_from_drive(_gdrive, root_id, dept_keys)

    # ถ้าหน่วยงานไหนยังไม่มีใน Drive → ใช้ Sample data
    data = {}
    for dk in dept_keys:
        if dk in drive_data:
            data[dk] = drive_data[dk]
        else:
            data[dk] = GENERATORS[dk]()
    return data, len(drive_data)


base_data, drive_dept_count = load_data_cached(root_id, gdrive)
# override ด้วยข้อมูลที่อัปโหลดในเซสชันนี้ (ก่อน save to drive สำเร็จ)
data = {**base_data, **st.session_state.uploaded_override}


# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(f"## {APP_ICON} QA CPRAM\n**ลาดหลุมแก้ว (สำนักงานใหญ่)**")
    st.divider()

    # สถานะการเชื่อมต่อ
    if gdrive_ok:
        st.success(f"✅ Google Drive เชื่อมต่อแล้ว\n\n📁 {drive_dept_count}/11 หน่วยงาน มีข้อมูลใน Drive")
    else:
        st.warning("⚠️ ยังไม่ได้เชื่อม Google Drive\nแสดงข้อมูลตัวอย่าง (Demo)")

    st.divider()

    if st.button("🔄 รีเฟรชข้อมูล", use_container_width=True):
        st.cache_data.clear()
        st.session_state.uploaded_override = {}
        st.rerun()

    st.caption(f"🕐 {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")
    st.divider()
    st.caption("📌 วิธีใช้งาน\n1. ไปที่ Tab **📤 อัปโหลดข้อมูล**\n2. เลือกหน่วยงาน\n3. ลากวางไฟล์ **HTML / CSV / Excel**\n4. กดบันทึก → Dashboard อัปเดตอัตโนมัติ\n\n💡 ไฟล์ HTML จะแสดงผลเฉพาะทางของแต่ละหน่วยงาน")


# ════════════════════════════════════════════════════════════
# คำนวณ KPI
# ════════════════════════════════════════════════════════════

factory_kpi  = compute_factory_kpi(data)
export_kpi   = compute_export_readiness(data)
domestic_kpi = compute_domestic_quality(data)
alerts       = run_linkage_checks(data)
alerts_df    = alerts_to_dataframe(alerts)
dept_kpis    = factory_kpi["dept_kpis"]
dept_rsi     = compute_all_rsi(data)
TC = {"green": "#00C853", "yellow": "#FFD600", "red": "#D50000"}

# ── Override KPI ด้วยค่าจริงจาก HTML Dashboard ───────────────
_html_scores = st.session_state.get("html_kpi_scores", {})
if _html_scores:
    for _dk, _score in _html_scores.items():
        if _dk in dept_kpis and _score is not None:
            _thr_g = DEPARTMENTS[_dk].get("threshold_green", 85)
            _thr_y = DEPARTMENTS[_dk].get("threshold_yellow", 70)
            _traffic = "green" if _score >= _thr_g else ("yellow" if _score >= _thr_y else "red")
            dept_kpis[_dk]["score"]   = round(_score, 1)
            dept_kpis[_dk]["traffic"] = _traffic
    # คำนวณ factory_kpi ใหม่หลัง override
    _scores_all = [v["score"] for v in dept_kpis.values() if v.get("score") is not None]
    _reds    = sum(1 for v in dept_kpis.values() if v.get("traffic") == "red")
    _yellows = sum(1 for v in dept_kpis.values() if v.get("traffic") == "yellow")
    if _scores_all:
        import numpy as _np
        factory_kpi["factory_score"]   = round(float(_np.mean(_scores_all)), 1)
        factory_kpi["factory_traffic"] = "red" if (_reds >= 2 or factory_kpi["factory_score"] < 70) else \
                                         "yellow" if (_reds == 1 or _yellows >= 3 or factory_kpi["factory_score"] < 85) else "green"
        factory_kpi["red_count"]    = _reds
        factory_kpi["yellow_count"] = _yellows


# ════════════════════════════════════════════════════════════
# HEADER + TABS
# ════════════════════════════════════════════════════════════

st.markdown(f"# {APP_ICON} QA CPRAM — Executive Dashboard")
st.caption("ลาดหลุมแก้ว (สำนักงานใหญ่) | ภาพรวม 11 หน่วยงาน QA")

tab_upload, tab_exec, tab_dept, tab_links, tab_raw = st.tabs([
    "📤 อัปโหลดข้อมูล",
    "📊 Executive Overview",
    "🏭 ข้อมูลรายหน่วยงาน",
    "🔗 Cross-Dept Alerts",
    "📋 ข้อมูลดิบ",
])


# ════════════════════════════════════════════════════════════
# TAB 1 — อัปโหลดข้อมูล (หน้าหลัก — ใช้งานง่ายสุด)
# ════════════════════════════════════════════════════════════

with tab_upload:
    st.subheader("📤 อัปโหลดข้อมูลรายหน่วยงาน")

    if gdrive_ok:
        st.success("✅ ไฟล์จะบันทึกลง Google Drive อัตโนมัติ — Dashboard อัปเดตทันที")
    else:
        st.info("💡 ทำงานในโหมด Local — ไฟล์จะถูกใช้งานในเซสชันนี้เท่านั้น")

    st.divider()

    # เลือกหน่วยงาน — แสดงเป็น Grid ปุ่มใหญ่
    st.markdown("### 1️⃣ เลือกหน่วยงานของคุณ")
    dept_options = {k: f"{v['icon']} {v['name_th']}" for k, v in DEPARTMENTS.items()}
    selected_dept = st.selectbox(
        "หน่วยงาน",
        options=list(dept_options.keys()),
        format_func=lambda k: dept_options[k],
        label_visibility="collapsed"
    )

    cfg = DEPARTMENTS[selected_dept]
    kpi_now = dept_kpis.get(selected_dept, {})
    t_now = kpi_now.get("traffic", "red")

    # แสดงสถานะปัจจุบันของหน่วยงานที่เลือก
    c_info1, c_info2, c_info3 = st.columns(3)
    c_info1.metric("📊 KPI ปัจจุบัน", f"{kpi_now.get('score','N/A')}%")
    c_info2.metric("📋 จำนวนรายการ", kpi_now.get("record_count", 0))
    c_info3.metric("สถานะ", f"{TRAFFIC[t_now]['emoji']} {TRAFFIC[t_now]['label']}")

    if not gdrive_ok:
        st.caption("⚠️ แหล่งข้อมูลปัจจุบัน: ข้อมูลตัวอย่าง (Demo)")
    else:
        src = "Google Drive ✅" if selected_dept in base_data and drive_dept_count > 0 else "Demo (ยังไม่มีข้อมูลใน Drive)"
        st.caption(f"แหล่งข้อมูลปัจจุบัน: {src}")

    st.divider()

    # ─── Upload Box ─────────────────────────────────────────
    st.markdown("### 2️⃣ ลากวางไฟล์ หรือคลิกเพื่อเลือก")
    st.markdown(
        '<div class="upload-box">'
        '<div style="font-size:3rem">📂</div>'
        '<div style="font-size:1.1rem;font-weight:600;color:#1976D2">ลากไฟล์มาวางที่นี่</div>'
        '<div style="color:#888;font-size:0.9rem;margin-top:6px">รองรับ CSV, Excel (.xlsx, .xls) และ HTML — ขนาดไม่เกิน 200MB</div>'
        '</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        f"เลือกไฟล์สำหรับ {cfg['icon']} {cfg['name_th']}",
        type=None,   # รับทุกประเภทไฟล์ — HTML, CSV, Excel ทั้งหมด
        label_visibility="collapsed",
        key=f"uploader_{selected_dept}"
    )

    # ─── Template Download ──────────────────────────────────
    from sample_data_generator import GENERATORS
    tmpl = GENERATORS[selected_dept](n=5)
    st.download_button(
        f"⬇️ ดาวน์โหลด Template CSV ของ {cfg['name_th']}",
        data=tmpl.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        file_name=f"template_{selected_dept}.csv",
        mime="text/csv",
        help="ดาวน์โหลดตัวอย่างรูปแบบไฟล์ที่ถูกต้อง"
    )

    # ─── Preview + Save ─────────────────────────────────────
    if uploaded_file is not None:
        is_html = uploaded_file.name.lower().endswith((".html", ".htm"))

        # เก็บ raw HTML ทันทีที่เลือกไฟล์
        if is_html:
            try:
                _raw_preview = uploaded_file.getvalue().decode("utf-8-sig", errors="replace")
                st.session_state.html_content[selected_dept] = _raw_preview
            except Exception:
                pass

        df_new = load_uploaded_file(uploaded_file)
        if df_new is not None and not df_new.empty:
            st.divider()
            st.markdown("### 3️⃣ ตรวจสอบข้อมูลก่อนบันทึก")

            if is_html:
                # HTML Dashboard — แสดง preview จริง
                st.success(f"✅ HTML Dashboard ({uploaded_file.name}) — พร้อมบันทึก")
                if selected_dept in st.session_state.html_content:
                    import streamlit.components.v1 as _comp
                    _comp.html(st.session_state.html_content[selected_dept], height=500, scrolling=True)
            else:
                # CSV/Excel — แสดงตาราง
                st.dataframe(df_new.head(10), use_container_width=True)
                st.caption(f"พบ {len(df_new)} แถว × {len(df_new.columns)} คอลัมน์")
                kpi_col = cfg["kpi_column"]
                if kpi_col not in df_new.columns:
                    st.warning(f"⚠️ ไม่พบคอลัมน์ `{kpi_col}` — ระบบจะใช้คอลัมน์ `status` แทน")
                else:
                    st.success(f"✅ พบคอลัมน์ KPI `{kpi_col}` — พร้อมบันทึก")

            st.divider()
            st.markdown("### 4️⃣ บันทึกข้อมูล")

            col_save, col_cancel = st.columns([2, 1])
            with col_save:
                if st.button(
                    f"💾 บันทึกข้อมูล {cfg['icon']} {cfg['name_th']} → Google Drive",
                    type="primary",
                    use_container_width=True
                ):
                    file_bytes = uploaded_file.getvalue()
                    filename = uploaded_file.name

                    with st.spinner("กำลังบันทึกลง Google Drive..."):
                        saved = False

                        # บันทึกลง Google Drive (ถ้าเชื่อมต่อได้)
                        if gdrive_ok:
                            file_id = upload_file_to_drive(
                                gdrive, file_bytes, filename, selected_dept, root_id
                            )
                            if file_id:
                                saved = True
                                st.success(f"✅ บันทึกลง Google Drive สำเร็จ!\n📁 {selected_dept}/{filename}")
                            else:
                                st.error("❌ บันทึกลง Drive ไม่สำเร็จ — ตรวจสอบ Service Account")
                        else:
                            # บันทึก local fallback
                            from config import LOCAL_DATA_DIR
                            save_dir = LOCAL_DATA_DIR / selected_dept
                            save_dir.mkdir(parents=True, exist_ok=True)
                            df_new.to_csv(save_dir / filename, index=False, encoding="utf-8-sig")
                            saved = True
                            st.success(f"✅ บันทึก Local สำเร็จ (ยังไม่ได้เชื่อม Drive)")

                        if saved:
                            # อัปเดต session state ทันที
                            st.session_state.uploaded_override[selected_dept] = df_new
                            # เก็บ HTML raw content + extract KPI
                            if uploaded_file.name.lower().endswith((".html", ".htm")):
                                try:
                                    from html_renderer import extract_html_kpi
                                    raw_html = file_bytes.decode("utf-8-sig", errors="replace")
                                    st.session_state.html_content[selected_dept] = raw_html
                                    _kpi_val = extract_html_kpi(raw_html)
                                    if _kpi_val is not None:
                                        st.session_state.html_kpi_scores[selected_dept] = _kpi_val
                                        st.info(f"📊 ระบบอ่านค่า KPI จากไฟล์ HTML: **{_kpi_val:.1f}%**")
                                except Exception:
                                    pass
                            else:
                                # CSV/Excel → ล้าง HTML เก่าออก
                                st.session_state.html_content.pop(selected_dept, None)
                                st.session_state.html_kpi_scores.pop(selected_dept, None)
                            st.cache_data.clear()
                            st.rerun()

            with col_cancel:
                if st.button("❌ ยกเลิก", use_container_width=True):
                    st.rerun()

        else:
            st.error("❌ ไม่สามารถอ่านไฟล์ได้ — ตรวจสอบรูปแบบไฟล์")

    # ─── สถานะไฟล์ใน Drive ──────────────────────────────────
    if gdrive_ok:
        st.divider()
        st.markdown("### 📁 ไฟล์ใน Google Drive (ทุกหน่วยงาน)")
        from gdrive_handler import list_subfolders, list_files_in_folder
        try:
            subfolders = list_subfolders(gdrive, root_id)
            rows = []
            for dk, dc in DEPARTMENTS.items():
                fid = subfolders.get(dk)
                if fid:
                    files = list_files_in_folder(gdrive, fid)
                    for f in files:
                        rows.append({
                            "หน่วยงาน": f"{dc['icon']} {dc['name_th']}",
                            "ชื่อไฟล์": f["name"],
                            "อัปเดตล่าสุด": f.get("modifiedTime","")[:10],
                            "สถานะ": "✅ มีข้อมูล"
                        })
                else:
                    rows.append({
                        "หน่วยงาน": f"{dc['icon']} {dc['name_th']}",
                        "ชื่อไฟล์": "-",
                        "อัปเดตล่าสุด": "-",
                        "สถานะ": "⬜ ยังไม่มีไฟล์"
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        except Exception as e:
            st.caption(f"ไม่สามารถดึงรายการไฟล์: {e}")


# ════════════════════════════════════════════════════════════
# TAB 2 — EXECUTIVE OVERVIEW (HTML Dashboard — Chemical Lab Style)
# ════════════════════════════════════════════════════════════

with tab_exec:
    exec_html = build_exec_html(
        factory_kpi  = factory_kpi,
        export_kpi   = export_kpi,
        domestic_kpi = domestic_kpi,
        dept_kpis    = dept_kpis,
        alerts       = alerts,
        dept_rsi     = dept_rsi,
    )
    components.html(exec_html, height=1150, scrolling=True)


# ════════════════════════════════════════════════════════════
# TAB 3 — ข้อมูลรายหน่วยงาน
# ════════════════════════════════════════════════════════════

with tab_dept:
    st.subheader("🏭 ข้อมูลรายละเอียดรายหน่วยงาน")
    dept_select = st.selectbox(
        "เลือกหน่วยงาน", list(DEPARTMENTS.keys()),
        format_func=lambda k: f"{DEPARTMENTS[k]['icon']} {DEPARTMENTS[k]['name_th']}")
    df_dept = data.get(dept_select, pd.DataFrame())
    kpi = dept_kpis.get(dept_select, {})
    cfg = DEPARTMENTS[dept_select]

    st.info(f"ℹ️ {cfg['description']}")

    # ── ถ้ามี HTML content → ใช้ HTML renderer เฉพาะทาง ───
    html_raw = st.session_state.html_content.get(dept_select)

    if html_raw:
        # แสดง badge ว่าข้อมูลมาจาก HTML
        st.markdown(
            '<div style="display:inline-block;background:#e3f2fd;border:1px solid #1976D2;'
            'border-radius:20px;padding:4px 14px;font-size:0.85rem;color:#1976D2;margin-bottom:8px">'
            '📄 วิเคราะห์จากไฟล์ HTML</div>',
            unsafe_allow_html=True
        )
        render_html_dashboard(dept_select, html_raw)

    else:
        # ── ไม่มี HTML → แสดงแบบเดิม (CSV/Excel หรือ Demo data) ──
        src_label = "📊 ข้อมูลตัวอย่าง (Demo)" if dept_select not in st.session_state.uploaded_override else "📁 ข้อมูลที่อัปโหลด (CSV/Excel)"
        st.markdown(
            f'<div style="display:inline-block;background:#f5f5f5;border:1px solid #ccc;'
            f'border-radius:20px;padding:4px 14px;font-size:0.85rem;color:#555;margin-bottom:8px">'
            f'{src_label}</div>',
            unsafe_allow_html=True
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("📊 คะแนน KPI", f"{kpi.get('score', 'N/A')}%")
        k2.metric("📋 จำนวนรายการ", kpi.get("record_count", 0))
        k3.metric("⏳ Pending", kpi.get("pending", 0))
        k4.metric("สถานะ",
                  TRAFFIC.get(kpi.get("traffic", "red"), {}).get("emoji", "") + " " +
                  TRAFFIC.get(kpi.get("traffic", "red"), {}).get("label", ""))

        if not df_dept.empty:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                if "status" in df_dept.columns:
                    sc = df_dept["status"].value_counts().reset_index()
                    sc.columns = ["Status", "จำนวน"]
                    cm = {"PASS": "#00C853", "FAIL": "#D50000", "OK": "#00C853", "REJECT": "#D50000",
                          "VALID": "#00C853", "EXPIRED": "#D50000", "EXPIRING_SOON": "#FFD600",
                          "WARNING": "#FFD600", "ALERT": "#FF6D00"}
                    fig_b = px.bar(sc, x="Status", y="จำนวน", color="Status",
                                   color_discrete_map=cm, title=f"สรุปสถานะ — {cfg['name_th']}")
                    fig_b.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
                    st.plotly_chart(fig_b, use_container_width=True)

            with col_chart2:
                date_cols = [c for c in df_dept.columns if "date" in c.lower() or "time" in c.lower()]
                kpi_col = cfg.get("kpi_column")
                if date_cols and kpi_col and kpi_col in df_dept.columns:
                    try:
                        df_t = df_dept.copy()
                        df_t[date_cols[0]] = pd.to_datetime(df_t[date_cols[0]], errors="coerce")
                        df_t = df_t.dropna(subset=[date_cols[0], kpi_col])
                        df_t = df_t.groupby(df_t[date_cols[0]].dt.date)[kpi_col].mean().reset_index()
                        df_t.columns = ["วันที่", "ค่าเฉลี่ย KPI"]
                        fig_l = px.line(df_t, x="วันที่", y="ค่าเฉลี่ย KPI",
                                        title=f"Trend — {cfg['name_th']}", markers=True)
                        fig_l.add_hline(y=cfg["threshold_green"], line_dash="dot",
                                        line_color="green", annotation_text="Green")
                        fig_l.add_hline(y=cfg["threshold_yellow"], line_dash="dot",
                                        line_color="orange", annotation_text="Yellow")
                        fig_l.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig_l, use_container_width=True)
                    except Exception:
                        pass

            # ── RSI Section ──────────────────────────────────────
            st.divider()
            st.subheader("📈 RSI Momentum Indicator")
            rsi_data = dept_rsi.get(dept_select, {})
            rsi_val  = rsi_data.get("rsi")
            signal   = rsi_data.get("signal", "no_data")
            rsi_series = rsi_data.get("series", pd.DataFrame())

            SIGNAL_INFO = {
                "overbought": ("🔴 Overbought", "#D50000", "KPI วิ่งแรงต่อเนื่อง — เฝ้าระวังการกลับตัว"),
                "oversold":   ("🔵 Oversold",   "#1565c0", "KPI ตกต่ำต่อเนื่อง — ต้องดำเนินการแก้ไข"),
                "neutral":    ("🟢 Neutral",     "#00C853", "KPI อยู่ในช่วงปกติ สมดุลดี"),
                "no_data":    ("⬜ ไม่มีข้อมูล","#9e9e9e", "ข้อมูลไม่เพียงพอสำหรับคำนวณ RSI"),
            }
            lbl, sig_color, sig_desc = SIGNAL_INFO.get(signal, SIGNAL_INFO["no_data"])

            rsi_c1, rsi_c2 = st.columns([1, 3])
            with rsi_c1:
                st.markdown(
                    f'<div style="background:{sig_color}18;border:2px solid {sig_color};border-radius:12px;'
                    f'padding:14px;text-align:center;">'
                    f'<div style="font-size:2rem;font-weight:700;color:{sig_color};">'
                    f'{f"{rsi_val:.1f}" if rsi_val is not None else "N/A"}</div>'
                    f'<div style="font-size:0.8rem;color:{sig_color};font-weight:600;">RSI ({rsi_data.get("period",14)}d)</div>'
                    f'<div style="font-size:1.2rem;margin-top:6px;">{lbl}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                st.caption(sig_desc)

            with rsi_c2:
                if not rsi_series.empty and "rsi" in rsi_series.columns and rsi_series["rsi"].notna().any():
                    fig_rsi = go.Figure()
                    fig_rsi.add_hrect(y0=70, y1=100, fillcolor="rgba(213,0,0,0.07)",
                                      line_width=0, annotation_text="Overbought ≥70",
                                      annotation_position="top left",
                                      annotation_font_size=10, annotation_font_color="#D50000")
                    fig_rsi.add_hrect(y0=0, y1=30, fillcolor="rgba(21,101,192,0.07)",
                                      line_width=0, annotation_text="Oversold ≤30",
                                      annotation_position="bottom left",
                                      annotation_font_size=10, annotation_font_color="#1565c0")
                    fig_rsi.add_hline(y=70, line_dash="dash", line_color="#D50000", line_width=1.2)
                    fig_rsi.add_hline(y=30, line_dash="dash", line_color="#1565c0", line_width=1.2)
                    fig_rsi.add_hline(y=50, line_dash="dot",  line_color="#bbb",    line_width=0.8)
                    fig_rsi.add_trace(go.Scatter(
                        x=rsi_series["date"].astype(str),
                        y=rsi_series["rsi"],
                        mode="lines+markers",
                        name="RSI",
                        line=dict(color="#7b1fa2", width=2.5),
                        marker=dict(size=5, color="#7b1fa2"),
                    ))
                    fig_rsi.update_layout(
                        height=220,
                        margin=dict(l=20, r=20, t=10, b=20),
                        yaxis=dict(range=[0, 100], title="RSI", tickvals=[0,30,50,70,100]),
                        xaxis=dict(title=""),
                        showlegend=False,
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                    )
                    st.plotly_chart(fig_rsi, use_container_width=True)
                else:
                    st.info("ข้อมูลไม่เพียงพอสำหรับคำนวณ RSI (ต้องการอย่างน้อย 3 วันที่ต่างกัน)")

            st.divider()
            st.subheader("📋 ตารางข้อมูล")
            st.dataframe(df_dept, use_container_width=True, height=350)
            st.download_button(
                "⬇️ ดาวน์โหลด CSV",
                df_dept.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                f"{dept_select}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.warning("ไม่มีข้อมูล — กรุณาอัปโหลดไฟล์ HTML ในแท็บ 📤 อัปโหลดข้อมูล")


# ════════════════════════════════════════════════════════════
# TAB 4 — CROSS-DEPARTMENT ALERTS
# ════════════════════════════════════════════════════════════

with tab_links:
    st.subheader("🔗 Cross-Department Linkage Alerts")
    if alerts:
        crits = [a for a in alerts if a["severity"] == "critical"]
        highs = [a for a in alerts if a["severity"] == "high"]
        infos = [a for a in alerts if a["severity"] == "info"]
        if crits: st.error(f"🔴 Critical: {len(crits)} รายการ — ต้องดำเนินการทันที")
        if highs: st.warning(f"🟡 High: {len(highs)} รายการ — ต้องติดตาม")
        if infos: st.info(f"🔵 Info: {len(infos)} รายการ")
        for a in alerts:
            cls  = {"critical":"alert-critical","high":"alert-high","info":"alert-info"}.get(a["severity"],"alert-info")
            icon = {"critical":"🔴","high":"🟡","info":"🔵"}.get(a["severity"],"🔵")
            lots = ", ".join(str(x) for x in a["lot_numbers"][:3]) or "-"
            st.markdown(
                f'<div class="{cls}"><b>{icon} {a["message"]}</b><br>'
                f'<small>📤 {a["trigger"]} → 📥 {a["target"]} | '
                f'จำนวน: {a["count"]} | Lot: {lots} | {a["ts"]}</small></div>',
                unsafe_allow_html=True)
        if not alerts_df.empty:
            st.divider()
            st.dataframe(alerts_df, use_container_width=True)
    else:
        st.success("✅ ไม่พบ Alert ข้ามหน่วยงาน")

    st.divider()
    st.subheader("🗺️ Linkage Flow (Sankey)")
    from config import LINKAGE_RULES as LR
    dept_list = list(DEPARTMENTS.keys())
    idx_map = {k: i for i, k in enumerate(dept_list)}
    node_labels = [f"{DEPARTMENTS[k]['icon']} {DEPARTMENTS[k]['name_th']}" for k in dept_list]
    src_l, tgt_l, val_l, col_l = [], [], [], []
    for rule in LR:
        s, t_ = rule["trigger_dept"], rule["target_dept"]
        if s in idx_map and t_ in idx_map:
            has_alert = any(a["rule_id"] == rule["id"] for a in alerts)
            src_l.append(idx_map[s]); tgt_l.append(idx_map[t_])
            val_l.append(5 if has_alert else 1)
            col_l.append("rgba(213,0,0,0.5)" if has_alert else "rgba(150,150,150,0.2)")
    fig_s = go.Figure(go.Sankey(
        node=dict(pad=15, thickness=20, label=node_labels, color=["#1a237e"]*len(dept_list)),
        link=dict(source=src_l, target=tgt_l, value=val_l, color=col_l)))
    fig_s.update_layout(title_text="การไหลของข้อมูล (สีแดง = มี Alert)", height=420)
    st.plotly_chart(fig_s, use_container_width=True)


# ════════════════════════════════════════════════════════════
# TAB 5 — ข้อมูลดิบ
# ════════════════════════════════════════════════════════════

with tab_raw:
    st.subheader("📋 ข้อมูลดิบ")
    raw_dept = st.selectbox(
        "เลือกหน่วยงาน", list(DEPARTMENTS.keys()),
        format_func=lambda k: f"{DEPARTMENTS[k]['icon']} {DEPARTMENTS[k]['name_th']}",
        key="raw_sel")
    df_raw = data.get(raw_dept, pd.DataFrame()).copy()

    if not df_raw.empty:
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            search = st.text_input("🔍 ค้นหา", "")
        with c2:
            if "status" in df_raw.columns:
                sf = st.multiselect("สถานะ", df_raw["status"].unique().tolist(),
                                    default=df_raw["status"].unique().tolist())
                df_raw = df_raw[df_raw["status"].isin(sf)]
        with c3:
            if st.checkbox("เฉพาะ FAIL/REJECT") and "status" in df_raw.columns:
                df_raw = df_raw[df_raw["status"].isin(["FAIL","REJECT","EXPIRED","ALERT"])]

        if search:
            mask = df_raw.astype(str).apply(lambda col: col.str.contains(search, case=False)).any(axis=1)
            df_raw = df_raw[mask]

        st.caption(f"แสดง {len(df_raw)} รายการ")
        st.dataframe(df_raw, use_container_width=True, height=500)
        with st.expander("📊 สถิติสรุป"):
            st.dataframe(df_raw.describe(include="all"), use_container_width=True)
    else:
        st.info("ไม่มีข้อมูล")


st.divider()
st.caption(f"🏭 QA CPRAM Dashboard v2.0 | ลาดหลุมแก้ว | © {pd.Timestamp.now().year} CPRAM Co., Ltd.")
