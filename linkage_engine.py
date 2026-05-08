# linkage_engine.py — ระบบเชื่อมโยงข้อมูลระหว่างหน่วยงาน
from __future__ import annotations
from datetime import datetime
import pandas as pd
from config import DEPARTMENTS, LINKAGE_RULES

SEVERITY_ORDER = {"critical": 0, "high": 1, "info": 2}


def _check_fail(rule, data):
    alerts = []
    df = data.get(rule["trigger_dept"])
    if df is None or df.empty or "status" not in df.columns:
        return alerts
    fail_rows = df[df["status"] == "FAIL"]
    if not fail_rows.empty:
        lots = fail_rows["lot_number"].unique().tolist()[:5] if "lot_number" in fail_rows.columns else []
        alerts.append({"rule_id": rule["id"], "trigger": DEPARTMENTS[rule["trigger_dept"]]["name_th"],
            "target": DEPARTMENTS[rule["target_dept"]]["name_th"], "severity": rule["severity"],
            "message": rule["alert_message"], "lot_numbers": lots,
            "count": len(fail_rows), "ts": datetime.now().strftime("%Y-%m-%d %H:%M")})
    return alerts


def _check_new_spec(rule, data):
    alerts = []
    df = data.get("03_Technical")
    if df is None or df.empty or "spec_status" not in df.columns:
        return alerts
    new_specs = df[df["spec_status"] == "NEW"]
    if not new_specs.empty:
        specs = new_specs["spec_id"].tolist()[:5] if "spec_id" in new_specs.columns else []
        alerts.append({"rule_id": rule["id"], "trigger": DEPARTMENTS["03_Technical"]["name_th"],
            "target": DEPARTMENTS[rule["target_dept"]]["name_th"], "severity": rule["severity"],
            "message": rule["alert_message"], "lot_numbers": specs,
            "count": len(new_specs), "ts": datetime.now().strftime("%Y-%m-%d %H:%M")})
    return alerts


def _check_rm_reject(rule, data):
    alerts = []
    df = data.get("02_Raw_Material")
    if df is None or df.empty or "status" not in df.columns or "supplier_name" not in df.columns:
        return alerts
    reject_df = df[df["status"] == "REJECT"]
    supplier_counts = reject_df.groupby("supplier_name").size()
    bad_suppliers = supplier_counts[supplier_counts >= 3]
    if not bad_suppliers.empty:
        alerts.append({"rule_id": rule["id"], "trigger": DEPARTMENTS["02_Raw_Material"]["name_th"],
            "target": DEPARTMENTS["01_Audit_Supplier"]["name_th"], "severity": rule["severity"],
            "message": rule["alert_message"], "lot_numbers": bad_suppliers.index.tolist()[:5],
            "count": int(bad_suppliers.sum()), "ts": datetime.now().strftime("%Y-%m-%d %H:%M")})
    return alerts


def _check_temp(rule, data):
    alerts = []
    df = data.get("10_Load")
    if df is None or df.empty or "temp_deviation" not in df.columns:
        return alerts
    dev_rows = df[df["temp_deviation"] == True]
    if not dev_rows.empty:
        lots = dev_rows["lot_number"].unique().tolist()[:5] if "lot_number" in dev_rows.columns else []
        alerts.append({"rule_id": rule["id"], "trigger": DEPARTMENTS["10_Load"]["name_th"],
            "target": DEPARTMENTS["11_Data_Regulatory"]["name_th"], "severity": rule["severity"],
            "message": rule["alert_message"], "lot_numbers": lots,
            "count": len(dev_rows), "ts": datetime.now().strftime("%Y-%m-%d %H:%M")})
    return alerts


_HANDLERS = {"LINK_01": _check_fail, "LINK_02": _check_fail, "LINK_03": _check_new_spec,
             "LINK_04": _check_new_spec, "LINK_05": _check_rm_reject, "LINK_06": _check_fail, "LINK_07": _check_temp}


def run_linkage_checks(data):
    all_alerts = []
    for rule in LINKAGE_RULES:
        handler = _HANDLERS.get(rule["id"])
        if handler:
            try:
                all_alerts.extend(handler(rule, data))
            except Exception as e:
                print(f"[Linkage] Error {rule['id']}: {e}")
    all_alerts.sort(key=lambda a: SEVERITY_ORDER.get(a["severity"], 99))
    return all_alerts


def alerts_to_dataframe(alerts):
    if not alerts:
        return pd.DataFrame()
    rows = []
    sev_map = {"critical": "🔴 Critical", "high": "🟡 High", "info": "🔵 Info"}
    for a in alerts:
        rows.append({"ระดับ": sev_map.get(a["severity"], a["severity"]),
            "หน่วยงานต้นเหตุ": a["trigger"], "หน่วยงานที่ได้รับผล": a["target"],
            "ข้อความแจ้งเตือน": a["message"], "จำนวนรายการ": a["count"],
            "Lot/Spec": ", ".join(str(x) for x in a["lot_numbers"][:3]), "เวลา": a["ts"]})
    return pd.DataFrame(rows)
