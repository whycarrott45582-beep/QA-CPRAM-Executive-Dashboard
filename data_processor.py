# data_processor.py — โหลดและประมวลผลข้อมูลจาก Local / Google Drive
from __future__ import annotations
import io, os, sqlite3, json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from config import DEPARTMENTS, LOCAL_DATA_DIR, DB_PATH

# ─── Google Drive helpers ───────────────────────────────────

def get_gdrive_service(service_account_json: str):
    """
    สร้าง Google Drive service จาก Service Account JSON
    service_account_json = path ไฟล์ .json หรือ JSON string
    """
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account as sa

        SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

        # รองรับทั้ง path ไฟล์และ JSON string
        if os.path.isfile(service_account_json):
            creds = sa.Credentials.from_service_account_file(service_account_json, scopes=SCOPES)
        else:
            info = json.loads(service_account_json)
            creds = sa.Credentials.from_service_account_info(info, scopes=SCOPES)

        return build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"[GDrive] เชื่อมต่อไม่ได้: {e}")
        return None


def list_gdrive_files(service, folder_id: str) -> list[dict]:
    """รายการไฟล์ CSV/Excel ใน Google Drive folder"""
    try:
        query = (f"'{folder_id}' in parents and trashed=false and "
                 "(mimeType='text/csv' or "
                 "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
                 "mimeType='application/vnd.ms-excel')")
        result = service.files().list(q=query, fields="files(id,name,mimeType)").execute()
        return result.get("files", [])
    except Exception as e:
        print(f"[GDrive] list files error: {e}")
        return []


def list_gdrive_subfolders(service, parent_folder_id: str) -> dict[str, str]:
    """หา subfolder ชื่อ 01_Audit_Supplier, 02_Raw_Material ฯลฯ → {name: id}"""
    try:
        query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        result = service.files().list(q=query, fields="files(id,name)").execute()
        return {f["name"]: f["id"] for f in result.get("files", [])}
    except Exception as e:
        print(f"[GDrive] list subfolders error: {e}")
        return {}


def download_gdrive_file(service, file_id: str, mime_type: str) -> pd.DataFrame | None:
    """ดาวน์โหลดไฟล์จาก Google Drive → DataFrame"""
    try:
        from googleapiclient.http import MediaIoBaseDownload

        # Google Sheets → export เป็น CSV
        if "google-apps.spreadsheet" in mime_type:
            content = service.files().export(
                fileId=file_id,
                mimeType="text/csv"
            ).execute()
            return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")

        # ไฟล์ปกติ
        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)

        if "csv" in mime_type or "text" in mime_type:
            return pd.read_csv(buf, encoding="utf-8-sig")
        else:
            return pd.read_excel(buf)
    except Exception as e:
        print(f"[GDrive] download error: {e}")
        return None


def load_from_gdrive(service, root_folder_id: str) -> dict[str, pd.DataFrame]:
    """โหลดข้อมูลทุกหน่วยงานจาก Google Drive"""
    subfolders = list_gdrive_subfolders(service, root_folder_id)
    data = {}
    for dept_key in DEPARTMENTS:
        folder_id = subfolders.get(dept_key)
        if not folder_id:
            continue
        files = list_gdrive_files(service, folder_id)
        frames = []
        for f in files:
            df = download_gdrive_file(service, f["id"], f["mimeType"])
            if df is not None:
                frames.append(df)
        if frames:
            data[dept_key] = pd.concat(frames, ignore_index=True)
    return data


# ─── Local file helpers ─────────────────────────────────────

def load_local_dept(dept_key: str) -> pd.DataFrame | None:
    folder = LOCAL_DATA_DIR / dept_key
    if not folder.exists():
        return None
    frames = []
    for f in folder.glob("*"):
        try:
            if f.suffix.lower() == ".csv":
                frames.append(pd.read_csv(f, encoding="utf-8-sig"))
            elif f.suffix.lower() in (".xlsx", ".xls"):
                frames.append(pd.read_excel(f))
            elif f.suffix.lower() in (".html", ".htm"):
                # HTML → ลองอ่านตาราง ถ้าไม่มีตาราง → สร้าง placeholder
                try:
                    tbls = pd.read_html(f, encoding="utf-8")
                    if tbls:
                        frames.append(max(tbls, key=len))
                except Exception:
                    # HTML ไม่มีตาราง (Chart.js dashboard) → สร้าง row เพื่อให้ KPI รู้ว่ามีข้อมูล
                    frames.append(pd.DataFrame([{"source": str(f.name), "status": "OK", "html_dashboard": True}]))
        except Exception:
            pass
    return pd.concat(frames, ignore_index=True) if frames else None


def load_local_html_raw(dept_key: str) -> str | None:
    """โหลด raw HTML จาก local_data — ใช้สำหรับ html_renderer"""
    folder = LOCAL_DATA_DIR / dept_key
    if not folder.exists():
        return None
    for f in folder.glob("*.htm*"):
        try:
            return f.read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            pass
    return None


def load_uploaded_file(uploaded_file) -> pd.DataFrame | None:
    if uploaded_file is None:
        return None
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file, encoding="utf-8-sig")
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file)
        elif name.endswith((".html", ".htm")):
            content = uploaded_file.read().decode("utf-8-sig", errors="replace")
            tables = pd.read_html(io.StringIO(content))
            if tables:
                # เลือกตารางที่ใหญ่ที่สุด (มีแถวมากสุด)
                return max(tables, key=len)
    except Exception as e:
        print(f"[Upload] Error reading file: {e}")
    return None


# ─── Master data loader ─────────────────────────────────────

def load_all_data(
    gdrive_service=None,
    gdrive_root_id: str = "",
    use_sample: bool = False,
) -> dict[str, pd.DataFrame]:
    from sample_data_generator import GENERATORS

    data: dict[str, pd.DataFrame] = {}

    # 1. Google Drive (ถ้าเชื่อมต่อได้)
    gdrive_data = {}
    if gdrive_service and gdrive_root_id:
        gdrive_data = load_from_gdrive(gdrive_service, gdrive_root_id)

    for dept_key in DEPARTMENTS:
        df = gdrive_data.get(dept_key)
        if df is None:
            df = load_local_dept(dept_key)
        if df is None or use_sample:
            df = GENERATORS[dept_key]()
        data[dept_key] = df

    return data


# ─── KPI Calculators ───────────────────────────────────────

def compute_dept_kpi(dept_key: str, df: pd.DataFrame) -> dict:
    cfg = DEPARTMENTS[dept_key]
    kpi_col    = cfg["kpi_column"]
    thr_green  = cfg["threshold_green"]
    thr_yellow = cfg["threshold_yellow"]
    issues     = []

    if df is None or df.empty:
        return {"score": None, "traffic": "red", "record_count": 0, "issues": ["ไม่มีข้อมูล"], "pending": 0}

    if kpi_col in df.columns:
        score = df[kpi_col].mean()
    elif "status" in df.columns:
        score = (df["status"].isin(["PASS","VALID","OK"]).sum() / len(df)) * 100
    else:
        score = 100.0

    traffic = "green" if score >= thr_green else ("yellow" if score >= thr_yellow else "red")

    if "status" in df.columns:
        fail_rows = df[df["status"].isin(["FAIL","REJECT","EXPIRED","ALERT"])]
        if not fail_rows.empty:
            for col in ["remarks","issue_found","rejection_reason"]:
                if col in fail_rows.columns:
                    top = fail_rows[col].dropna().value_counts().head(3).index.tolist()
                    issues.extend([r for r in top if r])
                    break
            if not issues:
                issues.append(f"พบ {len(fail_rows)} รายการไม่ผ่านเกณฑ์")

    pending = int(df["status"].isin(["PENDING","EXPIRING_SOON","WARNING"]).sum()) if "status" in df.columns else 0

    return {"score": round(float(score),1), "traffic": traffic,
            "record_count": len(df), "issues": issues, "pending": pending}


def compute_factory_kpi(data: dict) -> dict:
    dept_kpis = {k: compute_dept_kpi(k, v) for k, v in data.items()}
    scores  = [v["score"] for v in dept_kpis.values() if v["score"] is not None]
    reds    = sum(1 for v in dept_kpis.values() if v["traffic"] == "red")
    yellows = sum(1 for v in dept_kpis.values() if v["traffic"] == "yellow")
    factory_score   = round(float(np.mean(scores)), 1) if scores else 0.0
    factory_traffic = "red" if (reds>=2 or factory_score<70) else ("yellow" if (reds==1 or yellows>=3 or factory_score<85) else "green")
    all_issues = []
    for dk, kpi in dept_kpis.items():
        for issue in kpi["issues"]:
            if issue:
                all_issues.append(f"{DEPARTMENTS[dk]['icon']} [{DEPARTMENTS[dk]['name_th']}] {issue}")
    return {"factory_score": factory_score, "factory_traffic": factory_traffic, "dept_kpis": dept_kpis,
            "top_issues": all_issues[:5], "red_count": reds, "yellow_count": yellows,
            "total_pending": sum(v["pending"] for v in dept_kpis.values())}


def compute_export_readiness(data: dict) -> dict:
    export_depts = ["03_Technical","10_Load","11_Data_Regulatory"]
    scores, issues = [], []
    for dk in export_depts:
        if dk in data:
            kpi = compute_dept_kpi(dk, data[dk])
            if kpi["score"] is not None: scores.append(kpi["score"])
            issues.extend(kpi["issues"])
    avg = round(float(np.mean(scores)),1) if scores else 0.0
    if avg >= 95:   status, label = "green",  "พร้อมส่งออก ✅"
    elif avg >= 80: status, label = "yellow", "ต้องตรวจสอบเพิ่ม ⚠️"
    else:           status, label = "red",    "ยังไม่พร้อม ❌"
    return {"score": avg, "status": status, "label": label, "issues": issues[:3]}


def compute_domestic_quality(data: dict) -> dict:
    domestic_depts = ["04_Hygiene","05_Pest_Control","06_Monitor","07_Lab_Micro","08_Lab_Chem"]
    scores, issues = [], []
    for dk in domestic_depts:
        if dk in data:
            kpi = compute_dept_kpi(dk, data[dk])
            if kpi["score"] is not None: scores.append(kpi["score"])
            issues.extend(kpi["issues"])
    avg = round(float(np.mean(scores)),1) if scores else 0.0
    if avg >= 90:   status, label = "green",  "มาตรฐานปลอดภัย ✅"
    elif avg >= 75: status, label = "yellow", "ต้องปรับปรุง ⚠️"
    else:           status, label = "red",    "ต่ำกว่าเกณฑ์ ❌"
    return {"score": avg, "status": status, "label": label, "issues": issues[:3]}


def save_snapshot(data: dict, db_path: Path = None):
    if db_path is None: db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    ts = datetime.now().isoformat()
    for dept_key, df in data.items():
        if df is not None and not df.empty:
            df_save = df.copy()
            df_save["_snapshot_ts"] = ts
            df_save["_dept"] = dept_key
            try:
                df_save.to_sql(dept_key.replace("-","_"), conn, if_exists="append", index=False)
            except Exception:
                pass
    conn.close()
