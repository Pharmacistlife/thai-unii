#!/usr/bin/env python3
"""
ThaiUNII — WHO ATC Code Backup to Supabase
ดึงรหัส ATC และกลุ่มยาจาก NIH NLM RxClass API มาบันทึกสำรอง (Backup) ไว้ใน Supabase
เพื่อให้ค้นหาด้วยรหัส ATC ได้โดยตรง (เช่น N02BE01, A02BC)
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import time
from typing import Dict, List, Any

# พจนานุกรมรหัส ATC สำหรับยากลุ่มยอดนิยม เพื่อนำเข้าสำรองทันทีโดยไม่ต้องรอยิง API ครบทุกตัว
SEED_ATC_DATA = {
    "PARACETAMOL": ("N02BE01", "Anilides / Analgesics"),
    "ACETAMINOPHEN": ("N02BE01", "Anilides / Analgesics"),
    "CHLORPHENIRAMINE": ("R06AB04", "Substituted alkylamines / Antihistamines"),
    "PREDNISONE": ("H02AB07", "Glucocorticoids / Corticosteroids"),
    "ASPIRIN": ("B01AC06", "Platelet aggregation inhibitors"),
    "IBUPROFEN": ("M01AE01", "Propionic acid derivatives / Antiinflammatory"),
    "AMOXICILLIN": ("J01CA04", "Penicillins with extended spectrum"),
    "OMEPRAZOLE": ("A02BC01", "Proton pump inhibitors / Acid-related disorders"),
    "METFORMIN": ("A10BA02", "Biguanides / Blood glucose lowering"),
    "DIAZEPAM": ("N05BA01", "Benzodiazepine derivatives / Anxiolytics"),
    "SIMVASTATIN": ("C10AA01", "HMG CoA reductase inhibitors / Lipid modifying"),
    "AMLODIPINE": ("C08CA01", "Dihydropyridine derivatives / Calcium channel blockers"),
    "LOSARTAN": ("C09CA01", "Angiotensin II receptor blockers (ARBs)"),
    "ATENOLOL": ("C07AB03", "Beta blocking agents, selective"),
    "CETIRIZINE": ("R06AE07", "Piperazine derivatives / Antihistamines"),
    "LORATADINE": ("R06AX13", "Other antihistamines for systemic use"),
    "DEXAMETHASONE": ("H02AB02", "Glucocorticoids / Corticosteroids"),
    "HYDROCHLOROTHIAZIDE": ("C03AA03", "Thiazides, low-ceiling diuretics"),
    "CIPROFLOXACIN": ("J01MA02", "Fluoroquinolones / Antibacterials"),
    "AZITHROMYCIN": ("J01FA10", "Macrolides / Antibacterials")
}

def update_substance_atc(supabase_url: str, service_key: str, preferred_name: str, atc_code: str, atc_name: str):
    """ส่งคำสั่ง PATCH อัปเดต atc_code และ atc_name ใน Supabase"""
    if not preferred_name or not atc_code:
        return
    url = f"{supabase_url.rstrip('/')}/rest/v1/substances?preferred_name=ilike.{urllib.parse.quote(preferred_name)}"
    payload = json.dumps({"atc_code": atc_code, "atc_name": atc_name}).encode('utf-8')
    headers = {
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as resp:
            pass
    except Exception as e:
        print(f"[!] Error updating {preferred_name}: {e}")

def fetch_live_atc_from_nlm(drug_name: str):
    """ยิงถาม NLM RxClass API เพื่อดึงรหัส ATC ของยาตัวนั้นๆ"""
    clean_name = re.sub(r' (WHOLE|SALT|HYDROCHLORIDE|SODIUM|POTASSIUM)$', '', drug_name, flags=re.I).strip()
    url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json?drugName={urllib.parse.quote(clean_name)}&relaSource=ATC"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            concepts = data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
            if concepts:
                item = concepts[0].get("rxclassMinConceptItem", {})
                return item.get("classId"), item.get("className")
    except Exception:
        pass
    return None, None

def backup_atc_data(supabase_url: str, service_key: str):
    print("[*] กำลังสำรองรหัส WHO ATC เข้าสู่ฐานข้อมูล Supabase...")
    
    # 1. สำรองข้อมูลกลุ่มยาสามัญยอดนิยมเข้าก่อนทันที
    for name, (code, desc) in SEED_ATC_DATA.items():
        update_substance_atc(supabase_url, service_key, name, code, desc)
        print(f"[✔] บันทึกสำรอง ATC: {name} ➔ {code} ({desc})")

    print("[*] สำรองรหัสยาสามัญพื้นฐานเรียบร้อยแล้ว!")

def main():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("[!] ไม่พบ SUPABASE_URL หรือ SUPABASE_SERVICE_ROLE_KEY")
        print("วิธีใช้: SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python3 backup_atc_to_supabase.py")
        sys.exit(1)

    backup_atc_data(supabase_url, service_key)

if __name__ == "__main__":
    main()
