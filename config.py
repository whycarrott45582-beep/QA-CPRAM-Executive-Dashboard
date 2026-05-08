# config.py — ตั้งค่าระบบ QA CPRAM Dashboard
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv ไม่จำเป็น — ตั้งค่า token ใน Sidebar แทนได้

# ─── Google Drive ──────────────────────────────────────────
# GDRIVE_ROOT_FOLDER_ID = ID ของโฟลเดอร์หลักใน Google Drive
# หาได้จาก URL: drive.google.com/drive/folders/<ID อยู่ตรงนี้>
GDRIVE_ROOT_FOLDER_ID    = os.getenv("GDRIVE_ROOT_FOLDER_ID", "")
GDRIVE_SERVICE_ACCOUNT   = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON", "")  # path ไฟล์ .json

BASE_DIR        = Path(__file__).parent
LOCAL_DATA_DIR  = BASE_DIR / "local_data"
DB_PATH         = BASE_DIR / "qa_cpram.db"

DEPARTMENTS = {
    "01_Audit_Supplier": {
        "name_th": "Audit Supplier", "name_en": "Audit Supplier",
        "group": "upstream", "icon": "🏭", "kpi_column": "audit_score",
        "threshold_green": 85, "threshold_yellow": 70,
        "description": "ตรวจสอบและรับรองแหล่งที่มาของวัตถุดิบ"
    },
    "02_Raw_Material": {
        "name_th": "วัตถุดิบ (RM)", "name_en": "Raw Material",
        "group": "upstream", "icon": "🐟", "kpi_column": "pass_rate",
        "threshold_green": 95, "threshold_yellow": 85,
        "description": "ตรวจรับและคัดกรองวัตถุดิบหน้าโรงงาน"
    },
    "03_Technical": {
        "name_th": "Technical", "name_en": "Technical (International)",
        "group": "external", "icon": "🌐", "kpi_column": "spec_compliance_rate",
        "threshold_green": 100, "threshold_yellow": 90,
        "description": "ที่ปรึกษาเทคนิคลูกค้าต่างประเทศ"
    },
    "04_Hygiene": {
        "name_th": "Hygiene", "name_en": "Hygiene",
        "group": "midstream", "icon": "🧼", "kpi_column": "hygiene_score",
        "threshold_green": 90, "threshold_yellow": 75,
        "description": "ควบคุมสุขลักษณะการผลิต"
    },
    "05_Pest_Control": {
        "name_th": "Pest Control", "name_en": "Pest Control",
        "group": "midstream", "icon": "🐀", "kpi_column": "pest_free_rate",
        "threshold_green": 98, "threshold_yellow": 90,
        "description": "จัดการระบบป้องกันสัตว์พาหะ"
    },
    "06_Monitor": {
        "name_th": "Monitor (CCP/NCR)", "name_en": "Monitor",
        "group": "midstream", "icon": "📋", "kpi_column": "ccp_pass_rate",
        "threshold_green": 100, "threshold_yellow": 95,
        "description": "เฝ้าระวังจุดวิกฤต CCP ในไลน์ผลิต"
    },
    "07_Lab_Micro": {
        "name_th": "Lab จุลชีววิทยา", "name_en": "Lab Microbiology",
        "group": "midstream", "icon": "🔬", "kpi_column": "pass_rate",
        "threshold_green": 90, "threshold_yellow": 80,
        "description": "ตรวจสอบความปลอดภัยทางจุลชีววิทยา"
    },
    "08_Lab_Chem": {
        "name_th": "Lab เคมี", "name_en": "Lab Chemical",
        "group": "midstream", "icon": "⚗️", "kpi_column": "pass_rate",
        "threshold_green": 100, "threshold_yellow": 95,
        "description": "ตรวจสอบองค์ประกอบทางเคมีและสารตกค้าง"
    },
    "09_Sensory": {
        "name_th": "Sensory", "name_en": "Sensory Evaluation",
        "group": "downstream", "icon": "👅", "kpi_column": "pass_rate",
        "threshold_green": 95, "threshold_yellow": 80,
        "description": "ประเมินคุณภาพด้วยประสาทสัมผัส"
    },
    "10_Load": {
        "name_th": "คลัง/ขนส่ง (Load)", "name_en": "Load & Transport",
        "group": "downstream", "icon": "🚛", "kpi_column": "temp_compliance_rate",
        "threshold_green": 100, "threshold_yellow": 95,
        "description": "ตรวจสอบการโหลดสินค้าและอุณหภูมิขนส่ง"
    },
    "11_Data_Regulatory": {
        "name_th": "Data / ระเบียบการ", "name_en": "Export & Regulatory",
        "group": "external", "icon": "📜", "kpi_column": "cert_valid_rate",
        "threshold_green": 100, "threshold_yellow": 90,
        "description": "เอกสารส่งออกและใบรับรองสุขอนามัย"
    },
}

GROUPS = {
    "upstream":   {"label": "กลุ่มต้นน้ำ (Input Control)",       "color": "#1f77b4"},
    "midstream":  {"label": "กลุ่มกลางน้ำ (Production)",         "color": "#ff7f0e"},
    "downstream": {"label": "กลุ่มปลายน้ำ (Output & Logistics)",  "color": "#2ca02c"},
    "external":   {"label": "กลุ่มหน้าด่าน (External/Export)",    "color": "#9467bd"},
}

TRAFFIC = {
    "green":  {"emoji": "🟢", "label": "ปกติ",      "color": "#00C853"},
    "yellow": {"emoji": "🟡", "label": "เฝ้าระวัง",  "color": "#FFD600"},
    "red":    {"emoji": "🔴", "label": "วิกฤต",      "color": "#D50000"},
}

LINKAGE_RULES = [
    {"id": "LINK_01", "trigger_dept": "07_Lab_Micro",  "trigger_condition": "status == 'FAIL'",
     "target_dept": "11_Data_Regulatory", "alert_message": "⚠️ พบเชื้อจุลินทรีย์ → ตรวจสอบเอกสารส่งออกล็อตนี้ทันที", "severity": "critical"},
    {"id": "LINK_02", "trigger_dept": "06_Monitor",    "trigger_condition": "status == 'FAIL'",
     "target_dept": "11_Data_Regulatory", "alert_message": "⚠️ CCP เกินเกณฑ์ → อาจส่งผลต่อเอกสารส่งออก", "severity": "high"},
    {"id": "LINK_03", "trigger_dept": "03_Technical",  "trigger_condition": "spec_status == 'NEW'",
     "target_dept": "09_Sensory", "alert_message": "📌 มี Spec ใหม่จากลูกค้า → อัปเดตเกณฑ์ Sensory", "severity": "info"},
    {"id": "LINK_04", "trigger_dept": "03_Technical",  "trigger_condition": "spec_status == 'NEW'",
     "target_dept": "07_Lab_Micro", "alert_message": "📌 มี Spec ใหม่จากลูกค้า → อัปเดตเกณฑ์ Lab", "severity": "info"},
    {"id": "LINK_05", "trigger_dept": "02_Raw_Material","trigger_condition": "rejection_count >= 3",
     "target_dept": "01_Audit_Supplier", "alert_message": "🔄 RM ถูกปฏิเสธซ้ำ ≥3 ครั้ง → ควรเพิ่มความเข้มข้นในการ Audit Supplier", "severity": "high"},
    {"id": "LINK_06", "trigger_dept": "08_Lab_Chem",   "trigger_condition": "status == 'FAIL'",
     "target_dept": "11_Data_Regulatory", "alert_message": "⚠️ ผลเคมีเกินเกณฑ์ → ตรวจสอบเอกสารส่งออกล็อตนี้", "severity": "critical"},
    {"id": "LINK_07", "trigger_dept": "10_Load",       "trigger_condition": "temp_deviation == True",
     "target_dept": "11_Data_Regulatory", "alert_message": "🌡️ อุณหภูมิขนส่งเบี่ยงเบน → ตรวจสอบ Health Certificate", "severity": "high"},
]

APP_TITLE    = "QA CPRAM — ลาดหลุมแก้ว Executive Dashboard"
APP_ICON     = "🏭"
REFRESH_SECS = 300
