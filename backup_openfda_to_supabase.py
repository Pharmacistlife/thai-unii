#!/usr/bin/env python3
"""
ThaiUNII — openFDA Full Drug Label Bulk Backup to Supabase
ดึงข้อมูลเอกสารกำกับยาทางการจาก openFDA API (Indications, Warnings, Adverse Reactions, Contraindications)
แบบ Paging ละ 100 ฉบับ แล้วจับคู่ด้วย openfda.unii เพื่อนำเข้าตาราง public.substance_drug_labels ใน Supabase
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import time
from typing import Dict, List, Any

def clean_text_snippet(arr: Any, max_len: int = 500) -> str:
    """ทำความสะอาดและตัดข้อความให้อ่านง่าย กระชับ เหมาะแก่การแสดงผล"""
    if not arr:
        return ""
    if isinstance(arr, list):
        text = " ".join(str(x) for x in arr)
    else:
        text = str(arr)
    text = " ".join(text.split()).strip()
    return text[:max_len] + "..." if len(text) > max_len else text

def insert_label_batch(supabase_url: str, service_key: str, batch: List[Dict[str, Any]]):
    """ส่งข้อมูลแบบ Batch Insert เข้าตาราง substance_drug_labels"""
    if not batch:
        return
    url = f"{supabase_url.rstrip('/')}/rest/v1/substance_drug_labels"
    payload = json.dumps(batch).encode('utf-8')
    headers = {
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            pass
    except Exception as e:
        print(f"[!] Error inserting drug label batch: {e}")

def get_existing_substances_set(supabase_url: str, service_key: str) -> set:
    """ดึงรหัส unii ทั้งหมดที่มีในตาราง substances เพื่อตรวจสอบความสัมพันธ์"""
    print("[*] กำลังตรวจสอบรหัส UNII ในฐานข้อมูล Supabase...")
    unii_set = set()
    limit = 2000
    offset = 0

    while True:
        url = f"{supabase_url.rstrip('/')}/rest/v1/substances?select=unii&limit={limit}&offset={offset}"
        req = urllib.request.Request(url, headers={"apikey": service_key})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if not data:
                    break
                for row in data:
                    u = row.get("unii")
                    if u:
                        unii_set.add(u.strip())
                offset += limit
                if len(data) < limit:
                    break
        except Exception as e:
            print(f"[!] Error reading substances: {e}")
            break

    print(f"[✔] พบรหัส UNII ในฐานข้อมูล Supabase พร้อมรับข้อมูลฉลากยา {len(unii_set)} ตัว")
    return unii_set

def fetch_and_backup_openfda_labels(supabase_url: str, service_key: str, target_count: int = 1000):
    """ดึงข้อมูลเอกสารกำกับยาจาก openFDA ทีละ 100 ฉบับ จนครบตามเป้าหมาย"""
    print(f"[*] เริ่มต้นดาวน์โหลดเอกสารกำกับยาจาก openFDA API (เป้าหมาย {target_count} รายการ)...")
    
    existing_uniis = get_existing_substances_set(supabase_url, service_key)
    processed_uniis = set()
    batch = []
    total_saved = 0
    skip = 0
    limit = 100

    while total_saved < target_count and skip < 10000:
        url = f"https://api.fda.gov/drug/label.json?limit={limit}&skip={skip}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get("results", [])
                if not results:
                    break

                for label in results:
                    openfda = label.get("openfda", {})
                    uniis = openfda.get("unii", [])
                    if not uniis:
                        continue

                    for unii in uniis:
                        unii = unii.strip()
                        if unii in existing_uniis and unii not in processed_uniis:
                            processed_uniis.add(unii)

                            ind = clean_text_snippet(label.get("indications_and_usage"))
                            warn = clean_text_snippet(label.get("boxed_warning") or label.get("warnings_and_cautions") or label.get("warnings"))
                            react = clean_text_snippet(label.get("adverse_reactions"))
                            contra = clean_text_snippet(label.get("contraindications"))

                            if ind or warn or react or contra:
                                batch.append({
                                    "unii": unii,
                                    "indications": ind if ind else None,
                                    "warnings": warn if warn else None,
                                    "adverse_reactions": react if react else None,
                                    "contraindications": contra if contra else None
                                })
                                total_saved += 1

                            if len(batch) >= 100:
                                insert_label_batch(supabase_url, service_key, batch)
                                print(f"[+] บันทึกเอกสารกำกับยาลง Supabase แล้ว {total_saved} ตัว...")
                                batch = []

                            if total_saved >= target_count:
                                break

                skip += limit
                time.sleep(0.3) # ให้เกียรติ rate limit ของ openFDA
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("[*] สิ้นสุดข้อมูลใน openFDA")
                break
            print(f"[!] HTTP Error {e.code} จาก openFDA: {e}")
            break
        except Exception as e:
            print(f"[!] เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
            break

    if batch:
        insert_label_batch(supabase_url, service_key, batch)

    print(f"[✔] สำรองเอกสารกำกับยา openFDA เข้าสู่ Supabase สำเร็จครบถ้วน {total_saved} รายการ!")

def main():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("[!] ไม่พบ SUPABASE_URL หรือ SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    fetch_and_backup_openfda_labels(supabase_url, service_key, target_count=1000)

if __name__ == "__main__":
    main()
