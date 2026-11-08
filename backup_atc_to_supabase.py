#!/usr/bin/env python3
"""
ThaiUNII — WHO ATC Full Database Importer to Supabase
ดึงฐานข้อมูลรหัสยาและกลุ่มยาทั้งหมดจาก WHO Collaborating Centre for Drug Statistics Methodology (WHOCC)
(https://atcddd.fhi.no/atc_ddd_index/) แล้วจับคู่ชื่อยากับตาราง substances เพื่อบันทึกลงในตารางแยก public.substance_atc
"""

import os
import sys
import csv
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any

# แหล่งข้อมูลเปิดบัญชีรหัสยา WHO ATC ทั้งหมดจาก WHOCC (ครอบคลุมรหัส ATC ทุกตัวทั่วโลก)
WHO_ATC_CSV_URL = "https://raw.githubusercontent.com/fabkury/atcd/master/WHO%20ATC-DDD%202026-04-25.csv"

def insert_atc_batch(supabase_url: str, service_key: str, batch: List[Dict[str, Any]]):
    """ส่งข้อมูลแบบ Batch Insert เข้าตาราง substance_atc"""
    if not batch:
        return
    url = f"{supabase_url.rstrip('/')}/rest/v1/substance_atc"
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
        print(f"[!] Error inserting ATC batch: {e}")

def get_substances_map(supabase_url: str, service_key: str) -> Dict[str, str]:
    """ดึงคู่ {preferred_name: unii} จากตาราง substances ใน Supabase เพื่อนำมาจับคู่"""
    print("[*] กำลังโหลดรายชื่อสารจาก Supabase เพื่อเตรียมจับคู่...")
    name_to_unii = {}
    limit = 1000
    offset = 0

    while True:
        url = f"{supabase_url.rstrip('/')}/rest/v1/substances?select=unii,preferred_name&limit={limit}&offset={offset}"
        req = urllib.request.Request(url, headers={"apikey": service_key})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if not data:
                    break
                for row in data:
                    name = row.get("preferred_name", "").strip().upper()
                    if name:
                        name_to_unii[name] = row.get("unii")
                offset += limit
                if len(data) < limit:
                    break
        except Exception as e:
            print(f"[!] Error fetching substances: {e}")
            break

    print(f"[✔] โหลดรายชื่อสารจาก Supabase พร้อมจับคู่แล้ว {len(name_to_unii)} รายการ")
    return name_to_unii

def download_and_import_who_atc(supabase_url: str, service_key: str):
    print(f"[*] กำลังดาวน์โหลดฐานข้อมูลรหัสยา WHO ATC ล่าสุดจากเว็บ WHOCC: {WHO_ATC_CSV_URL}")
    
    req = urllib.request.Request(WHO_ATC_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[!] ไม่สามารถดาวน์โหลดไฟล์จาก WHO ได้: {e}")
        return

    reader = csv.reader(content.splitlines(), delimiter=',')
    headers = None
    atc_code_idx = 0
    atc_name_idx = 1

    substances_map = get_substances_map(supabase_url, service_key)

    # พจนานุกรมชื่อกลุ่มยาสำหรับรหัสระดับ 4 (เพื่อนำมาแสดงเป็นชื่อกลุ่ม เช่น Anilides, Proton pump inhibitors)
    atc_group_names = {}
    atc_rows = []

    for row in reader:
        if not row:
            continue
        if headers is None:
            headers = [h.strip().lower() for h in row]
            for idx, h in enumerate(headers):
                if "code" in h:
                    atc_code_idx = idx
                elif "name" in h:
                    atc_name_idx = idx
            continue

        if len(row) > max(atc_code_idx, atc_name_idx):
            code = row[atc_code_idx].strip()
            name = row[atc_name_idx].strip()

            if len(code) <= 5:
                # เก็บชื่อกลุ่มยาระดับ 1-4 ไว้
                atc_group_names[code] = name
            elif len(code) == 7:
                # รหัสระดับ 5 (ตัวยาสำคัญ)
                atc_rows.append((code, name))

    print(f"[*] พบรหัสยากลุ่มและตัวยาของ WHO ATC ทั้งหมด {len(atc_rows)} รายการ")

    batch = []
    matched_count = 0

    for code, drug_name in atc_rows:
        drug_upper = drug_name.upper()
        # หาชื่อกลุ่มยาจากรหัส 5 ตัวแรก เช่น N02BE01 ➔ กลุ่ม N02BE (Anilides)
        group_code = code[:5]
        group_name = atc_group_names.get(group_code, drug_name.title())
        display_atc_name = f"{group_name} / {drug_name.title()}" if group_name != drug_name.title() else drug_name.title()

        # ตรวจสอบว่าชื่อยาใน WHO ตรงกับ preferred_name ตัวไหนใน FDA UNII บ้าง
        unii = substances_map.get(drug_upper)
        if not unii:
            # ตรวจสอบกรณีชื่อมีเกลือ เช่น ACETAMINOPHEN / PARACETAMOL
            if drug_upper == "PARACETAMOL":
                unii = substances_map.get("ACETAMINOPHEN")
            elif drug_upper == "ACETAMINOPHEN":
                unii = substances_map.get("PARACETAMOL")

        if unii:
            batch.append({
                "unii": unii,
                "atc_code": code,
                "atc_name": display_atc_name
            })
            matched_count += 1

            if len(batch) >= 200:
                insert_atc_batch(supabase_url, service_key, batch)
                print(f"[+] บันทึกรหัส WHO ATC เข้าตาราง substance_atc แล้ว {matched_count} รายการ...")
                batch = []

    if batch:
        insert_atc_batch(supabase_url, service_key, batch)

    print(f"[✔] ดึงและจับคู่รหัสยาจาก WHO ATC เข้าสู่ Supabase สำเร็จครบถ้วน {matched_count} รายการ!")

def main():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("[!] ไม่พบ SUPABASE_URL หรือ SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    download_and_import_who_atc(supabase_url, service_key)

if __name__ == "__main__":
    main()
