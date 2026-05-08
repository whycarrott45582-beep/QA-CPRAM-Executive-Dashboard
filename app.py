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
    load_uploaded_file, save_snapshot
)
from linkage_engine import run_linkage_checks, alerts_to_dataframe
from gdrive_handler import (
    get_gdrive_service, get_root_folder_id,
    upload_file_to_drive, load_all_from_drive
)

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
    st.caption("📌 วิธีใช้งาน\n1. ไปที่ Tab **📤 อัปโหลดข้อมูล**\n2. เลือกหน่วยงาน\n3. ลากวางไฟล์ CSV/Excel\n4. กดบันทึก → Dashboard อัปเดตอัตโนมัติ")


# ════════════════════════════════════════════════════════════
# คำนวณ KPI
# ════════════════════════════════════════════════════════════

factory_kpi  = compute_factory_kpi(data)
export_kpi   = compute_export_readiness(data)
domestic_kpi = compute_domestic_quality(data)
alerts       = run_linkage_checks(data)
alerts_df    = alerts_to_dataframe(alerts)
dept_kpis    = factory_kpi["dept_kpis"]
TC = {"green": "#00C853", "yellow": "#FFD600", "red": "#D50000"}


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
        '<div style="color:#888;font-size:0.9rem;margin-top:6px">รองรับ CSV, Excel (.xlsx, .xls) — ขนาดไม่เกิน 200MB</div>'
        '</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        f"เลือกไฟล์สำหรับ {cfg['icon']} {cfg['name_th']}",
        type=["csv", "xlsx", "xls"],
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
        df_new = load_uploaded_file(uploaded_file)
        if df_new is not None and not df_new.empty:
            st.divider()
            st.markdown("### 3️⃣ ตรวจสอบข้อมูลก่อนบันทึก")

            # Preview
            st.dataframe(df_new.head(10), use_container_width=True)
            st.caption(f"พบ {len(df_new)} แถว × {len(df_new.columns)} คอลัมน์")

            # ตรวจสอบ column สำคัญ
            kpi_col = cfg["kpi_column"]
            missing_kpi = kpi_col not in df_new.columns
            if missing_kpi:
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
# TAB 2 — EXECUTIVE OVERVIEW
# ════════════════════════════════════════════════════════════

with tab_exec:
    c_score, c_export, c_domestic, c_pending = st.columns([2, 1.5, 1.5, 1])
    t = factory_kpi["factory_traffic"]

    with c_score:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=factory_kpi["factory_score"],
            number={"suffix": "%", "font": {"size": 40}},
            title={"text": "🏭 Factory QA Health Score", "font": {"size": 14}},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": TC[t]},
                   "steps": [{"range": [0,70], "color": "#ffcdd2"},
                              {"range": [70,85], "color": "#fff9c4"},
                              {"range": [85,100], "color": "#c8e6c9"}],
                   "threshold": {"line": {"color":"black","width":3}, "thickness":0.75, "value":85}}))
        fig.update_layout(height=230, margin=dict(l=20,r=20,t=40,b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            f'<div class="tl-card tl-{t}">'
            f'{TRAFFIC[t]["emoji"]} สถานะโรงงานวันนี้: <b>{TRAFFIC[t]["label"]}</b></div>',
            unsafe_allow_html=True)

    for col, kpi_d, title, thr in [
        (c_export,   export_kpi,   "🌐 Export Readiness (5%)",  [80, 95]),
        (c_domestic, domestic_kpi, "🏠 Domestic Quality (95%)", [75, 90])]:
        with col:
            et = kpi_d["status"]
            fig2 = go.Figure(go.Indicator(
                mode="gauge+number", value=kpi_d["score"],
                number={"suffix": "%", "font": {"size": 32}},
                title={"text": title, "font": {"size": 13}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": TC[et]},
                       "steps": [{"range": [0,thr[0]], "color": "#ffcdd2"},
                                  {"range": [thr[0],thr[1]], "color": "#fff9c4"},
                                  {"range": [thr[1],100], "color": "#c8e6c9"}]}))
            fig2.update_layout(height=200, margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown(f'<div class="tl-card tl-{et}">{kpi_d["label"]}</div>', unsafe_allow_html=True)
            for iss in kpi_d.get("issues", [])[:2]:
                st.caption(f"⚠️ {iss}")

    with c_pending:
        for num, lbl in [
            (f'🔴 {factory_kpi["red_count"]}',    "หน่วยงานวิกฤต"),
            (f'🟡 {factory_kpi["yellow_count"]}',  "หน่วยงานเฝ้าระวัง"),
            (f'📋 {factory_kpi["total_pending"]}', "งานค้าง (Pending)"),
            (f'🔔 {len(alerts)}',                  "Cross-Dept Alerts")]:
            st.markdown(
                f'<div class="metric-box">'
                f'<div class="metric-num">{num}</div>'
                f'<div class="metric-lbl">{lbl}</div></div>',
                unsafe_allow_html=True)

    st.divider()
    st.subheader("🏭 สถานะ 11 หน่วยงาน QA")

    for group_key, group_cfg in GROUPS.items():
        group_depts = {k: v for k, v in DEPARTMENTS.items() if v["group"] == group_key}
        if not group_depts:
            continue
        st.markdown(f"**{group_cfg['label']}**")
        cols = st.columns(len(group_depts))
        for idx, (dk, dc) in enumerate(group_depts.items()):
            kpi = dept_kpis.get(dk, {})
            score = kpi.get("score")
            traffic = kpi.get("traffic", "red")
            score_str = f"{score:.1f}%" if score is not None else "N/A"
            bc = TC[traffic]
            pending_val = kpi.get("pending", 0)
            pending_html = f'<div style="font-size:0.75rem;color:#888">⏳ {pending_val} pending</div>' if pending_val else ""
            with cols[idx]:
                st.markdown(
                    f'<div style="border:2px solid {bc};border-radius:10px;padding:10px;'
                    f'text-align:center;background:#fafafa;min-height:140px">'
                    f'<div style="font-size:1.8rem">{dc["icon"]}</div>'
                    f'<div style="font-weight:700;font-size:0.82rem;color:#333">{dc["name_th"]}</div>'
                    f'<div style="font-size:1.5rem;font-weight:800;color:{bc}">{score_str}</div>'
                    f'<div style="font-size:1.1rem">{TRAFFIC[traffic]["emoji"]} {TRAFFIC[traffic]["label"]}</div>'
                    f'{pending_html}</div>',
                    unsafe_allow_html=True)
                if kpi.get("issues"):
                    with st.popover("📌 ปัญหา", use_container_width=True):
                        for iss in kpi["issues"][:5]:
                            st.warning(iss)
        st.write("")

    st.divider()
    c_issues, c_radar = st.columns(2)

    with c_issues:
        st.subheader("🚨 ปัญหาสำคัญวันนี้")
        if factory_kpi["top_issues"]:
            for i, issue in enumerate(factory_kpi["top_issues"][:5], 1):
                cls = "alert-critical" if i <= 2 else "alert-high"
                st.markdown(f'<div class="{cls}">{i}. {issue}</div>', unsafe_allow_html=True)
        else:
            st.success("✅ ไม่พบปัญหา — ทุกหน่วยงานอยู่ในเกณฑ์")
        for a in [x for x in alerts if x["severity"] == "critical"][:3]:
            st.markdown(
                f'<div class="alert-critical">🔴 <b>{a["message"]}</b><br>'
                f'<small>{a["trigger"]} → {a["target"]} | {a["count"]} รายการ</small></div>',
                unsafe_allow_html=True)

    with c_radar:
        st.subheader("📡 Radar Chart")
        dept_names = [DEPARTMENTS[k]["name_th"] for k in DEPARTMENTS]
        scores_all = [dept_kpis[k]["score"] or 0 for k in DEPARTMENTS]
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(
            r=scores_all + [scores_all[0]], theta=dept_names + [dept_names[0]],
            fill="toself", fillcolor="rgba(26,35,126,0.15)",
            line=dict(color="#1a237e", width=2), name="KPI ปัจจุบัน"))
        fig_r.add_trace(go.Scatterpolar(
            r=[85]*len(dept_names) + [85], theta=dept_names + [dept_names[0]],
            mode="lines", line=dict(color="green", width=1, dash="dot"),
            name="เกณฑ์มาตรฐาน (85%)"))
        fig_r.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True, height=380, margin=dict(l=40,r=40,t=20,b=20))
        st.plotly_chart(fig_r, use_container_width=True)


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

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📊 คะแนน KPI", f"{kpi.get('score','N/A')}%")
    k2.metric("📋 จำนวนรายการ", kpi.get("record_count", 0))
    k3.metric("⏳ Pending", kpi.get("pending", 0))
    k4.metric("สถานะ",
              TRAFFIC.get(kpi.get("traffic","red"),{}).get("emoji","") + " " +
              TRAFFIC.get(kpi.get("traffic","red"),{}).get("label",""))
    st.info(f"ℹ️ {cfg['description']}")

    if not df_dept.empty:
        if "status" in df_dept.columns:
            sc = df_dept["status"].value_counts().reset_index()
            sc.columns = ["Status", "จำนวน"]
            cm = {"PASS":"#00C853","FAIL":"#D50000","OK":"#00C853","REJECT":"#D50000",
                  "VALID":"#00C853","EXPIRED":"#D50000","EXPIRING_SOON":"#FFD600",
                  "WARNING":"#FFD600","ALERT":"#FF6D00"}
            fig_b = px.bar(sc, x="Status", y="จำนวน", color="Status",
                           color_discrete_map=cm, title=f"สรุปสถานะ — {cfg['name_th']}")
            fig_b.update_layout(height=280, margin=dict(l=20,r=20,t=40,b=20), showlegend=False)
            st.plotly_chart(fig_b, use_container_width=True)

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
                fig_l.update_layout(height=280, margin=dict(l=20,r=20,t=40,b=20))
                st.plotly_chart(fig_l, use_container_width=True)
            except Exception:
                pass

        st.subheader("📋 ตารางข้อมูล")
        st.dataframe(df_dept, use_container_width=True, height=350)
        st.download_button(
            "⬇️ ดาวน์โหลด CSV",
            df_dept.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
            f"{dept_select}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.warning("ไม่มีข้อมูล")


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
