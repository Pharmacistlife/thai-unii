#!/usr/bin/env python3
"""
ThaiUNII — openFDA Full Drug Label Bulk Backup to Supabase
ดึงข้อมูลเอกสารกำกับยาทางการจาก openFDA API (Indications, Warnings, Adverse Reactions, Contraindications)
แบบ Bulk Paging เข้าสู่ตาราง public.substance_drug_labels ใน Supabase โดยตรง
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
    except urllib.error.HTTPError as e:
        # หากมีตัวใดไม่ผ่าน foreign key ให้แยก insert ทีละตัวเพื่อไม่ให้กระทบทั้ง batch
        for item in batch:
            try:
                single_payload = json.dumps([item]).encode('utf-8')
                s_req = urllib.request.Request(url, data=single_payload, headers=headers, method="POST")
                with urllib.request.urlopen(s_req):
                    pass
            except Exception:
                pass
    except Exception as e:
        print(f"[!] Error: {e}")

def get_already_saved_uniis(supabase_url: str, service_key: str) -> set:
    """ดึงรหัส unii ที่มีข้อมูลใน substance_drug_labels อยู่แล้วเพื่อไม่ต้องดึงซ้ำ"""
    saved_set = set()
    url = f"{supabase_url.rstrip('/')}/rest/v1/substance_drug_labels?select=unii&limit=5000"
    req = urllib.request.Request(url, headers={"apikey": service_key})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for row in data:
                u = row.get("unii")
                if u:
                    saved_set.add(u.strip())
    except Exception:
        pass
    return saved_set

def fetch_and_backup_openfda_labels(supabase_url: str, service_key: str, target_count: int = 100000):
    print(f"[*] เริ่มต้นดาวน์โหลดเอกสารกำกับยาจาก openFDA API (เป้าหมาย {target_count} รายการ)...")
    
    already_saved = get_already_saved_uniis(supabase_url, service_key)
    print(f"[*] มีข้อมูลฉลากยาเดิมในตารางอยู่แล้ว {len(already_saved)} รายการ (จะข้ามเพื่อไม่ให้ซ้ำ)")

    processed_uniis = set(already_saved)
    batch = []
    total_saved = 0
    skip = 0
    limit = 100

    while total_saved < target_count and skip < 20000:
        # ดึงเฉพาะฉลากยาที่มีรหัส UNII แน่ชัดจาก openFDA
        url = f"https://api.fda.gov/drug/label.json?search=_exists_:openfda.unii&limit={limit}&skip={skip}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get("results", [])
                if not results:
                    break

                for label in results:
                    openfda = label.get("openfda", {})
                    uniis = openfda.get("unii", [])
                    if not uniis:
                        continue

                    # ใช้รหัส UNII ตัวแรกของฉลากยานั้นๆ
                    unii = uniis[0].strip()
                    if unii in processed_uniis:
                        continue
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

                    if len(batch) >= 50:
                        insert_label_batch(supabase_url, service_key, batch)
                        print(f"[+] บันทึกเอกสารกำกับยาลง Supabase แล้ว {total_saved} ตัว...")
                        batch = []

                    if total_saved >= target_count:
                        break

                skip += limit
                time.sleep(0.25) # ให้เกียรติ openFDA API rate limit
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("[*] สิ้นสุดข้อมูลใน openFDA")
                break
            print(f"[!] HTTP Error {e.code} จาก openFDA, พัก 2 วินาทีแล้วลองต่อ...")
            time.sleep(2)
            skip += limit
        except Exception as e:
            print(f"[!] Error: {e}")
            break

    if batch:
        insert_label_batch(supabase_url, service_key, batch)

    print(f"[✔] สำรองเอกสารกำกับยา openFDA เข้าสู่ Supabase สำเร็จครบถ้วนรวม {total_saved} รายการใหม่!")

def main():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("[!] ไม่พบ SUPABASE_URL หรือ SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    fetch_and_backup_openfda_labels(supabase_url, service_key, target_count=1000)

if __name__ == "__main__":
    main()
