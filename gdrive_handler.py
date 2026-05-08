# gdrive_handler.py — จัดการ Google Drive (อ่าน + เขียน)
# ============================================================
# รองรับ 2 โหมด:
#   1. Streamlit Cloud → ดึง credentials จาก st.secrets
#   2. Local Dev       → ดึงจากไฟล์ service_account.json
# ============================================================
from __future__ import annotations
import io, json
from pathlib import Path
import pandas as pd

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
    from google.oauth2 import service_account
    HAS_GDRIVE = True
except ImportError:
    HAS_GDRIVE = False

SCOPES = ["https://www.googleapis.com/auth/drive"]  # อ่าน + เขียน


# ─── สร้าง Service ─────────────────────────────────────────

def get_service_from_secrets():
    """ดึง credentials จาก st.secrets (Streamlit Cloud)"""
    if not HAS_GDRIVE:
        return None
    try:
        import streamlit as st
        sa_info = dict(st.secrets["gdrive"])
        if "private_key" in sa_info:
            sa_info["private_key"] = sa_info["private_key"].replace("\\n", "\n")
        creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"[GDrive] secrets error: {e}")
        return None


def get_service_from_file(json_path: str = "service_account.json"):
    """ดึง credentials จากไฟล์ JSON (local dev)"""
    if not HAS_GDRIVE or not Path(json_path).exists():
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(json_path, scopes=SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"[GDrive] file error: {e}")
        return None


def get_gdrive_service():
    """Auto-detect: ลอง st.secrets ก่อน ถ้าไม่มีใช้ไฟล์ JSON local"""
    svc = get_service_from_secrets()
    if svc:
        return svc
    return get_service_from_file()


def get_root_folder_id() -> str:
    """ดึง root folder ID จาก st.secrets หรือ environment variable"""
    try:
        import streamlit as st
        fid = st.secrets.get("gdrive_config", {}).get("root_folder_id", "")
        if fid:
            return fid
    except Exception:
        pass
    import os
    return os.getenv("GDRIVE_ROOT_FOLDER_ID", "")


# ─── Folder Management ─────────────────────────────────────

def get_or_create_folder(service, name: str, parent_id: str) -> str:
    """หาหรือสร้าง subfolder ใน Google Drive"""
    query = (f"'{parent_id}' in parents and name='{name}' and "
             f"mimeType='application/vnd.google-apps.folder' and trashed=false")
    result = service.files().list(q=query, fields="files(id)").execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def list_subfolders(service, parent_id: str) -> dict[str, str]:
    """รายการ subfolders → {name: id}"""
    query = (f"'{parent_id}' in parents and "
             f"mimeType='application/vnd.google-apps.folder' and trashed=false")
    result = service.files().list(q=query, fields="files(id,name)").execute()
    return {f["name"]: f["id"] for f in result.get("files", [])}


# ─── Upload ────────────────────────────────────────────────

def _delete_old_file(service, filename: str, folder_id: str):
    """ลบไฟล์เก่าชื่อเดียวกันใน folder (ป้องกัน duplicate)"""
    try:
        query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
        result = service.files().list(q=query, fields="files(id)").execute()
        for f in result.get("files", []):
            service.files().delete(fileId=f["id"]).execute()
    except Exception:
        pass


def upload_file_to_drive(
    service,
    file_bytes: bytes,
    filename: str,
    dept_key: str,
    root_folder_id: str,
) -> str | None:
    """
    อัปโหลดไฟล์ → root_folder / dept_key / filename
    คืน file_id หรือ None ถ้าเกิด error
    """
    try:
        dept_folder_id = get_or_create_folder(service, dept_key, root_folder_id)
        _delete_old_file(service, filename, dept_folder_id)

        if filename.lower().endswith(".csv"):
            mime = "text/csv"
        elif filename.lower().endswith(".xlsx"):
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            mime = "application/octet-stream"

        file_meta = {"name": filename, "parents": [dept_folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime, resumable=True)
        uploaded = service.files().create(
            body=file_meta, media_body=media, fields="id,name"
        ).execute()
        return uploaded.get("id")
    except Exception as e:
        print(f"[GDrive] upload error: {e}")
        return None


# ─── Download / Read ───────────────────────────────────────

def list_files_in_folder(service, folder_id: str) -> list[dict]:
    """รายการไฟล์ CSV/Excel ใน folder"""
    query = (f"'{folder_id}' in parents and trashed=false and ("
             "mimeType='text/csv' or "
             "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
             "mimeType='application/vnd.ms-excel' or "
             "mimeType='application/vnd.google-apps.spreadsheet')")
    result = service.files().list(
        q=query, fields="files(id,name,mimeType,modifiedTime)",
        orderBy="modifiedTime desc"
    ).execute()
    return result.get("files", [])


def download_file(service, file_id: str, mime_type: str) -> pd.DataFrame | None:
    """ดาวน์โหลดไฟล์จาก Drive → DataFrame"""
    try:
        if "google-apps.spreadsheet" in mime_type:
            content = service.files().export(fileId=file_id, mimeType="text/csv").execute()
            return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
        buf = io.BytesIO()
        request = service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)
        if "csv" in mime_type or "text" in mime_type:
            return pd.read_csv(buf, encoding="utf-8-sig")
        return pd.read_excel(buf)
    except Exception as e:
        print(f"[GDrive] download error: {e}")
        return None


def load_dept_from_drive(service, dept_key: str, root_folder_id: str) -> pd.DataFrame | None:
    """โหลดข้อมูลหน่วยงานจาก Drive"""
    subfolders = list_subfolders(service, root_folder_id)
    folder_id = subfolders.get(dept_key)
    if not folder_id:
        return None
    files = list_files_in_folder(service, folder_id)
    frames = [download_file(service, f["id"], f["mimeType"]) for f in files]
    frames = [df for df in frames if df is not None]
    return pd.concat(frames, ignore_index=True) if frames else None


def load_all_from_drive(service, root_folder_id: str, dept_keys: list) -> dict:
    """โหลดข้อมูลทุกหน่วยงานจาก Google Drive"""
    return {
        dk: df for dk in dept_keys
        if (df := load_dept_from_drive(service, dk, root_folder_id)) is not None
    }
