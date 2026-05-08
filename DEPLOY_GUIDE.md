# 🚀 คู่มือ Deploy QA CPRAM Dashboard
## ขั้นตอนทำครั้งเดียว (~30 นาที) — ใช้งานได้ตลอด

---

## STEP 1 — เตรียม Google Drive

1. เปิด [Google Drive](https://drive.google.com)
2. สร้างโฟลเดอร์ใหม่ชื่อ **`QA_Root`**
3. คัดลอก **Folder ID** จาก URL:
   ```
   https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                           ID อยู่ตรงนี้ — จดเก็บไว้
   ```

---

## STEP 2 — สร้าง Google Service Account

1. ไปที่ [Google Cloud Console](https://console.cloud.google.com)
2. สร้าง Project ใหม่ (เช่น `qa-cpram-dashboard`)
3. **APIs & Services → Library** → ค้นหา **"Google Drive API"** → Enable
4. **IAM & Admin → Service Accounts → + Create Service Account**
   - ชื่อ: `qa-cpram`
5. คลิก Service Account → Tab **"Keys"** → **Add Key → JSON**
6. ไฟล์ `.json` โหลดอัตโนมัติ — **เก็บไว้อย่างปลอดภัย ห้ามแชร์!**

---

## STEP 3 — แชร์ Google Drive ให้ Service Account

1. คัดลอก email ของ Service Account
   (รูปแบบ: `qa-cpram@your-project.iam.gserviceaccount.com`)
2. Google Drive → คลิกขวาโฟลเดอร์ **QA_Root** → Share
3. วาง email → ตั้งสิทธิ์ **"Editor"** → Done

---

## STEP 4 — Push โค้ดขึ้น GitHub

```powershell
cd "C:\Users\January\Desktop\QA Dashboard"
git init
git add .
git commit -m "QA CPRAM Dashboard v2.0"
git remote add origin https://github.com/<username>/<repo>.git
git branch -M main
git push -u origin main
```

---

## STEP 5 — Deploy บน Streamlit Cloud (ฟรี)

1. ไปที่ [share.streamlit.io](https://share.streamlit.io) → Login GitHub
2. **New app** → เลือก repo, branch=main, file=app.py
3. **Advanced settings → Secrets** → วางค่าจากไฟล์ JSON:

```toml
[gdrive]
type = "service_account"
project_id = "your-project-id"
private_key_id = "ค่าจากไฟล์ JSON"
private_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n"
client_email = "qa-cpram@your-project.iam.gserviceaccount.com"
client_id = "ค่าจากไฟล์ JSON"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "ค่าจากไฟล์ JSON"

[gdrive_config]
root_folder_id = "ID โฟลเดอร์ QA_Root จาก STEP 1"
```

4. **Deploy!** → รอ 2-3 นาที → ได้ URL เช่น `https://qa-cpram.streamlit.app`

---

## STEP 6 — ส่ง Link ให้ทีมงาน

**วิธีใช้งาน (ทีมงานทุกคน ไม่ต้องติดตั้งอะไร):**
1. เปิด Link ใน Browser
2. ไปที่ Tab **"📤 อัปโหลดข้อมูล"**
3. เลือกหน่วยงาน → ลากไฟล์วาง → กด **"บันทึก"**
4. ไฟล์บันทึกลง Google Drive → Dashboard อัปเดตอัตโนมัติ ✅

---

## โครงสร้าง Google Drive (สร้างอัตโนมัติเมื่ออัปโหลดครั้งแรก)

```
📁 QA_Root/
├── 📁 01_Audit_Supplier/
├── 📁 02_Raw_Material/
├── 📁 03_Technical/
├── 📁 04_Hygiene/
├── 📁 05_Pest_Control/
├── 📁 06_Monitor/
├── 📁 07_Lab_Micro/
├── 📁 08_Lab_Chem/
├── 📁 09_Sensory/
├── 📁 10_Load/
└── 📁 11_Data_Regulatory/
```

*QA CPRAM Dashboard v2.0 | ลาดหลุมแก้ว สำนักงานใหญ่*
