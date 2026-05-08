# sample_data_generator.py — สร้างข้อมูลตัวอย่าง 11 หน่วยงาน QA CPRAM
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

BASE_DIR   = Path(__file__).parent
LOCAL_DIR  = BASE_DIR / "local_data"

SUPPLIERS  = ["บ.ไทยฟิช จก.", "บ.ซีฟู้ด พลาส จก.", "บ.แม่กลองทะเล จก.", "บ.ปศุสัตว์ไทย จก.", "ฟาร์มไก่สยาม"]
PRODUCTS   = ["ปลาทูน่า", "ปลาแซลมอน", "กุ้งแวนนาไม", "ไก่ชิ้น", "ปลาหมึก"]
LINES      = ["Line A", "Line B", "Line C", "Line D"]
COUNTRIES  = ["EU", "Japan", "USA", "Australia", "Middle East"]
CUSTOMERS  = ["Tri Marine", "Chicken of the Sea", "John West", "MW Brands", "Pan Pacific"]
AREAS      = ["พื้นที่ผลิต A", "พื้นที่ผลิต B", "ห้องเย็น", "ห้องบรรจุ", "ทางเดิน", "โรงเปลือย"]
CERT_TYPES = ["Health Certificate (กรมประมง)", "Health Certificate (ปศุสัตว์)", "HACCP Certificate", "BRC Certificate", "EU Approval"]
PEST_LOCS  = ["คลังวัตถุดิบ", "ห้องผลิต", "โรงเปลือย", "ห้องบรรจุ", "ลานจอดรถ"]


def make_dates(days_back=30, n=1):
    today = datetime.today()
    dates = [today - timedelta(days=i) for i in range(days_back)]
    return [random.choice(dates) for _ in range(n)]


def gen_01_audit_supplier(n=20):
    rows = []
    for i in range(n):
        score = random.randint(55, 100)
        rows.append({"audit_id": f"AUD-{2025000+i}", "supplier_name": random.choice(SUPPLIERS),
            "audit_date": make_dates(90)[0].strftime("%Y-%m-%d"), "audit_type": random.choice(["Routine","Pre-approval","Follow-up"]),
            "product_type": random.choice(["ประมง","ปศุสัตว์","พืช"]), "audit_score": score,
            "status": "PASS" if score >= 70 else "FAIL", "major_nc": random.randint(0,3 if score<80 else 0),
            "minor_nc": random.randint(0,5), "next_audit_date": (datetime.today()+timedelta(days=random.randint(30,180))).strftime("%Y-%m-%d"),
            "remarks": random.choice(["ผ่านเกณฑ์","ต้องติดตาม","ปรับปรุงด้านสุขลักษณะ",""])})
    return pd.DataFrame(rows)


def gen_02_raw_material(n=50):
    rows = []
    for i in range(n):
        temp = round(random.uniform(-2, 6), 1)
        passed = temp <= 4 and random.random() > 0.08
        rows.append({"rm_id": f"RM-{20250000+i}", "rm_name": random.choice(PRODUCTS),
            "supplier_name": random.choice(SUPPLIERS), "received_date": make_dates(30)[0].strftime("%Y-%m-%d"),
            "lot_number": f"LOT-{random.randint(1000,9999)}", "quantity_kg": round(random.uniform(100,5000),1),
            "received_temp_c": temp, "visual_check": random.choice(["PASS","PASS","PASS","FAIL"]),
            "status": "PASS" if passed else "REJECT",
            "rejection_reason": "" if passed else random.choice(["อุณหภูมิเกิน","ลักษณะไม่ผ่าน","เอกสารไม่ครบ"]),
            "pass_rate": 100.0 if passed else 0.0, "inspector": random.choice(["สมชาย ก.","สุดา ข.","ประยุทธ์ ค."])})
    return pd.DataFrame(rows)


def gen_03_technical(n=15):
    rows = []
    for i in range(n):
        spec_status = random.choice(["ACTIVE","ACTIVE","NEW","REVISION","EXPIRED"])
        rows.append({"spec_id": f"SPEC-{2025000+i}", "customer": random.choice(CUSTOMERS),
            "country": random.choice(COUNTRIES), "product": random.choice(PRODUCTS),
            "spec_type": random.choice(["Product Spec","Packaging Spec","Process Spec","Micro Limit"]),
            "received_date": make_dates(60)[0].strftime("%Y-%m-%d"), "effective_date": make_dates(30)[0].strftime("%Y-%m-%d"),
            "spec_status": spec_status, "spec_compliance_rate": round(random.uniform(85,100),1),
            "standard_reference": random.choice(["BRC v9","IFS v7","EU 2073/2005","Japan Food Sanitation Law"]),
            "linked_departments": "07_Lab_Micro, 08_Lab_Chem, 09_Sensory",
            "remarks": random.choice(["","ลูกค้าขอ micro limit เพิ่มเติม","แก้ไข label requirement"])})
    return pd.DataFrame(rows)


def gen_04_hygiene(n=40):
    rows = []
    for i in range(n):
        score = random.randint(60, 100)
        rows.append({"inspection_id": f"HYG-{2025000+i}", "area": random.choice(AREAS),
            "inspection_date": make_dates(14)[0].strftime("%Y-%m-%d"), "shift": random.choice(["เช้า","บ่าย","ดึก"]),
            "hygiene_score": score, "status": "PASS" if score >= 75 else "FAIL",
            "issue_found": random.choice(["ไม่พบปัญหา","พื้นมีน้ำขัง","พนักงานไม่ล้างมือ","อุปกรณ์สกปรก",""]) if score < 85 else "ไม่พบปัญหา",
            "corrective_action": "" if score >= 85 else random.choice(["ล้างทำความสะอาดทันที","อบรมพนักงาน","ส่งซ่อม"]),
            "inspector": random.choice(["สมชาย ก.","สุดา ข."])})
    return pd.DataFrame(rows)


def gen_05_pest_control(n=30):
    rows = []
    for i in range(n):
        count = random.choices([0,0,0,1,2,5], weights=[50,20,15,8,5,2])[0]
        rows.append({"record_id": f"PEST-{2025000+i}", "location": random.choice(PEST_LOCS),
            "inspection_date": make_dates(30)[0].strftime("%Y-%m-%d"),
            "pest_type": random.choice(["แมลงวัน","แมลงสาบ","หนู","มด","-"]) if count > 0 else "-",
            "pest_count": count, "pest_free_rate": round((1-count/10)*100,1) if count < 10 else 0,
            "trap_id": f"TRAP-{random.randint(1,50)}",
            "action_taken": "ไม่พบ" if count==0 else random.choice(["วางยา","ปิดช่องทาง","พ่นยา","แจ้งผู้รับเหมา"]),
            "status": "OK" if count==0 else ("WARNING" if count<=2 else "ALERT"),
            "inspector": random.choice(["บริษัท Pest Pro","ทีมภายใน"])})
    return pd.DataFrame(rows)


def gen_06_monitor(n=60):
    rows = []
    ccp_types = [("อุณหภูมิปรุงสุก",85,100,"°C"),("อุณหภูมิแช่เย็น",-2,4,"°C"),
                 ("ค่า pH น้ำเกลือ",4.0,4.5,"pH"),("น้ำหนักบรรจุ",185,200,"g"),("Metal Detector",0,0,"pass/fail")]
    for i in range(n):
        ccp_name,lo,hi,unit = random.choice(ccp_types)
        if unit in ("°C","pH","g"):
            value = round(random.uniform(lo-(hi-lo)*0.15, hi+(hi-lo)*0.15),2)
            passed = lo <= value <= hi
        else:
            value = random.choices([1,0], weights=[97,3])[0]
            passed = value == 1
        rows.append({"ncr_id": f"NCR-{2025000+i}" if not passed else "", "line": random.choice(LINES),
            "monitor_time": make_dates(7)[0].strftime("%Y-%m-%d %H:%M"), "ccp_type": ccp_name,
            "unit": unit, "measured_value": value, "lower_limit": lo, "upper_limit": hi,
            "ccp_pass_rate": 100.0 if passed else 0.0, "status": "PASS" if passed else "FAIL",
            "lot_number": f"LOT-{random.randint(1000,9999)}", "operator": random.choice(["ประมวล ก.","วิภา ข.","อรรถ ค."]),
            "supervisor": random.choice(["จันทร์ ก.","อาทิตย์ ข."])})
    return pd.DataFrame(rows)


def gen_07_lab_micro(n=30):
    tests = ["TPC (Total Plate Count)","E. coli","Salmonella spp.","Listeria monocytogenes","Coliforms","Staphylococcus aureus"]
    limits = {"TPC (Total Plate Count)":(None,100000,"CFU/g"),"E. coli":(None,10,"MPN/g"),
              "Salmonella spp.":(None,0,"ND/25g"),"Listeria monocytogenes":(None,0,"ND/25g"),
              "Coliforms":(None,100,"MPN/g"),"Staphylococcus aureus":(None,100,"CFU/g")}
    rows = []
    for i in range(n):
        test = random.choice(tests)
        lo,hi,unit = limits[test]
        if test in ("Salmonella spp.","Listeria monocytogenes"):
            value = random.choices(["ND","ND","ND","Detected"], weights=[90,5,3,2])[0]
            passed = value == "ND"
        else:
            value = int(random.choices([hi*0.1,hi*0.5,hi*0.9,hi*1.2], weights=[50,30,15,5])[0])
            passed = value <= hi
        rows.append({"sample_id": f"MICRO-{2025000+i}", "sample_type": random.choice(["สินค้าสำเร็จรูป","วัตถุดิบ","สิ่งแวดล้อม","ระหว่างผลิต"]),
            "product": random.choice(PRODUCTS), "lot_number": f"LOT-{random.randint(1000,9999)}",
            "test_date": make_dates(14)[0].strftime("%Y-%m-%d"), "test_type": test,
            "result_value": str(value), "unit": unit, "limit": str(hi),
            "pass_rate": 100.0 if passed else 0.0, "status": "PASS" if passed else "FAIL",
            "analyst": random.choice(["นักวิทย์ A","นักวิทย์ B"])})
    return pd.DataFrame(rows)


def gen_08_lab_chem(n=25):
    tests = [("ความชื้น (%)",None,80,"%"),("โปรตีน (%)",10,None,"%"),("โซเดียม (mg/100g)",None,600,"mg/100g"),
             ("สารกันบูด (ppm)",None,200,"ppm"),("ยาปฏิชีวนะ (ppb)",None,100,"ppb"),
             ("โลหะหนัก - Pb (ppm)",None,0.3,"ppm"),("ฮีสตามีน (ppm)",None,200,"ppm")]
    rows = []
    for i in range(n):
        test_name,lo,hi,unit = random.choice(tests)
        if hi:
            value = round(random.choices([hi*0.3,hi*0.7,hi*0.95,hi*1.1], weights=[40,35,20,5])[0],2)
            passed = value <= hi
        else:
            value = round(random.uniform(lo*0.8, lo*1.3),2)
            passed = value >= lo
        rows.append({"sample_id": f"CHEM-{2025000+i}", "product": random.choice(PRODUCTS),
            "lot_number": f"LOT-{random.randint(1000,9999)}", "test_date": make_dates(14)[0].strftime("%Y-%m-%d"),
            "test_type": test_name, "result_value": value, "unit": unit,
            "upper_limit": hi, "lower_limit": lo, "pass_rate": 100.0 if passed else 0.0,
            "status": "PASS" if passed else "FAIL", "analyst": random.choice(["นักเคมี A","นักเคมี B"])})
    return pd.DataFrame(rows)


def gen_09_sensory(n=30):
    rows = []
    for i in range(n):
        color=round(random.uniform(6.0,9.5),1); texture=round(random.uniform(6.0,9.5),1); taste=round(random.uniform(6.0,9.5),1)
        overall=round((color+texture+taste)/3,2); passed=overall>=7.0
        rows.append({"eval_id": f"SEN-{2025000+i}", "product": random.choice(PRODUCTS),
            "lot_number": f"LOT-{random.randint(1000,9999)}", "eval_date": make_dates(14)[0].strftime("%Y-%m-%d"),
            "color_score": color, "texture_score": texture, "taste_score": taste, "overall_score": overall,
            "pass_rate": 100.0 if passed else 0.0, "status": "PASS" if passed else "FAIL",
            "customer_ref": random.choice(CUSTOMERS+[""]), "panel_size": random.randint(5,10),
            "remarks": "" if passed else random.choice(["รสเค็มเกิน","เนื้อแข็งไป","สีคล้ำ"])})
    return pd.DataFrame(rows)


def gen_10_load(n=25):
    rows = []
    for i in range(n):
        load_temp=round(random.uniform(-22,-14),1); trans_temp=round(random.uniform(-22,-13),1)
        temp_ok=load_temp<=-18 and trans_temp<=-15
        rows.append({"load_id": f"LOAD-{2025000+i}", "lot_number": f"LOT-{random.randint(1000,9999)}",
            "product": random.choice(PRODUCTS), "destination_country": random.choice(COUNTRIES),
            "customer": random.choice(CUSTOMERS), "load_date": make_dates(14)[0].strftime("%Y-%m-%d"),
            "container_number": f"TEMU{random.randint(1000000,9999999)}",
            "load_temp_c": load_temp, "transport_temp_c": trans_temp, "temp_deviation": not temp_ok,
            "temp_compliance_rate": 100.0 if temp_ok else 0.0,
            "seal_number": f"SL-{random.randint(100000,999999)}",
            "status": "PASS" if temp_ok else "FAIL",
            "remarks": "" if temp_ok else "อุณหภูมิตู้ไม่ถึงเกณฑ์"})
    return pd.DataFrame(rows)


def gen_11_data_regulatory(n=20):
    today = datetime.today()
    rows = []
    for i in range(n):
        issue=today-timedelta(days=random.randint(10,365)); expiry=issue+timedelta(days=random.randint(60,365))
        status="VALID" if expiry>today else ("EXPIRED" if expiry<today-timedelta(days=7) else "EXPIRING_SOON")
        rows.append({"cert_id": f"CERT-{2025000+i}", "cert_type": random.choice(CERT_TYPES),
            "cert_number": f"กปม.{random.randint(1000,9999)}/{today.year}",
            "lot_number": f"LOT-{random.randint(1000,9999)}", "product": random.choice(PRODUCTS),
            "destination": random.choice(COUNTRIES), "issue_date": issue.strftime("%Y-%m-%d"),
            "expiry_date": expiry.strftime("%Y-%m-%d"), "days_to_expiry": (expiry-today).days,
            "cert_valid_rate": 100.0 if status=="VALID" else 0.0, "status": status,
            "issuing_authority": random.choice(["กรมประมง","กรมปศุสัตว์","สมอ.","Bureau Veritas"]),
            "remarks": "" if status=="VALID" else "⚠️ ต้องต่ออายุ"})
    return pd.DataFrame(rows)


GENERATORS = {
    "01_Audit_Supplier": gen_01_audit_supplier, "02_Raw_Material": gen_02_raw_material,
    "03_Technical": gen_03_technical, "04_Hygiene": gen_04_hygiene,
    "05_Pest_Control": gen_05_pest_control, "06_Monitor": gen_06_monitor,
    "07_Lab_Micro": gen_07_lab_micro, "08_Lab_Chem": gen_08_lab_chem,
    "09_Sensory": gen_09_sensory, "10_Load": gen_10_load,
    "11_Data_Regulatory": gen_11_data_regulatory,
}


def generate_all(output_dir=None, fmt="csv"):
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    dfs = {}
    for dept_key, gen_fn in GENERATORS.items():
        df = gen_fn()
        dfs[dept_key] = df
        if output_dir:
            path = Path(output_dir) / dept_key
            path.mkdir(exist_ok=True)
            if fmt == "csv":
                df.to_csv(path / f"{dept_key}_sample.csv", index=False, encoding="utf-8-sig")
            else:
                df.to_excel(path / f"{dept_key}_sample.xlsx", index=False)
    return dfs


if __name__ == "__main__":
    print("สร้างข้อมูลตัวอย่าง...")
    generate_all(output_dir=LOCAL_DIR, fmt="csv")
    print(f"✅ บันทึกที่: {LOCAL_DIR}")
