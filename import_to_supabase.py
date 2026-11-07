#!/usr/bin/env python3
"""
ThaiUNII — Data Importer & Background Sync to Supabase
ดึงข้อมูล FDA UNII จาก precisionFDA Archive หรือไฟล์ในเครื่อง แล้วนำเข้า Supabase แบบ Batch
รองรับ Supabase New API Keys (sb_secret_...) และ Legacy Keys
"""

import os
import sys
import json
import gzip
import zipfile
import urllib.request
import re
from typing import List, Dict, Any

THAI_NAME_DICT = {
    "POVIDONE K30": ("โพวิโดน เค30 (สารช่วยยึดเกาะเม็ดยา)", "พอลิเมอร์สังเคราะห์ละลายน้ำได้ดี นิยมใช้เป็นสารยึดเกาะ (Binder) ในการตอกเม็ดยา"),
    "CHLORPHENIRAMINE": ("คลอร์เฟนิรามีน (ยาแก้แพ้ ลดน้ำมูก)", "สารต้านฮิสตามีนรุ่นที่ 1 (Antihistamine) บรรเทาอาการแพ้ จาม และลมพิษ"),
    "PREDNISONE": ("เพรดนิโซน (ยาลดการอักเสบกลุ่มสเตียรอยด์)", "ตัวยาสำคัญกลุ่มคอร์ติโคสเตียรอยด์ ใช้ต้านการอักเสบและกดภูมิคุ้มกัน"),
    "CURCUMA AROMATICA WHOLE": ("ว่านทางคำ / ขมิ้นป่า (ทั้งต้น)", "พืชสมุนไพรตระกูลขมิ้น (Zingiberaceae) ในตำรับยาแผนโบราณและเวชสำอาง"),
    "MATRICARIA CHAMOMILLA WHOLE": ("คาโมมายล์เยอรมัน (ทั้งต้น)", "สารสกัดจากดอกคาโมมายล์ ใช้ในเครื่องสำอางและสกินแคร์ลดการระคายเคือง"),
    "LYSOZYME": ("ไลโซไซม์ (เอนไซม์ต้านเชื้อแบคทีเรีย)", "เอนไซม์ธรรมชาติที่มีฤทธิ์ย่อยผนังเซลล์ของแบคทีเรียแกรมบวก"),
    "MAGNOLOL": ("แมกโนลอล (สารสำคัญจากเปลือกแมกโนเลีย)", "สารกลุ่มลิกแนนต้านอนุมูลอิสระและต้านเชื้อแบคทีเรีย"),
    "SODIUM PROPIONATE": ("โซเดียมโพรพิโอเนต (สารกันเสีย)", "วัตถุกันเสียป้องกันเชื้อราและแบคทีเรียในอาหารและยา (E281)"),
    "ZAVEGEPANT HYDROCHLORIDE": ("ซาเวจีแพนท์ ไฮโดรคลอไรด์ (ยารักษาไมเกรน)", "ตัวยาออกฤทธิ์ยับยั้งตัวรับ CGRP สำหรับรักษาอาการปวดไมเกรนเฉียบพลัน"),
    "PARACETAMOL": ("พาราเซตามอล (ยาลดไข้ บรรเทาปวด)", "ยาสามัญประจำบ้านสำหรับลดไข้และบรรเทาอาการปวด (หรือ Acetaminophen)"),
    "ACETAMINOPHEN": ("พาราเซตามอล (ยาลดไข้ บรรเทาปวด)", "ยาสามัญประจำบ้านสำหรับลดไข้และบรรเทาอาการปวด (หรือ Paracetamol)"),
    "IBUPROFEN": ("ไอบูโพรเฟน (ยาแก้ปวด ต้านการอักเสบ)", "ยาต้านการอักเสบที่ไม่ใช่สเตียรอยด์ (NSAIDs)"),
    "ASPIRIN": ("แอสไพริน (ยาต้านการเกาะกลุ่มของเกล็ดเลือด)", "ยาบรรเทาปวด ลดไข้ และต้านการแข็งตัวของเลือด"),
    "CURCUMIN": ("เคอร์คูมิน (สารสำคัญในขมิ้นชัน)", "สารออกฤทธิ์หลักสีเหลืองในขมิ้นชัน มีฤทธิ์ต้านการอักเสบและต้านอนุมูลอิสระ"),
    "ANDROGRAPHIS PANICULATA WHOLE": ("ฟ้าทะลายโจร (ทั้งต้น)", "สมุนไพรไทยบรรเทาอาการหวัด เจ็บคอ และแก้ไข้"),
    "CENTELLA ASIATICA WHOLE": ("บัวบก (ทั้งต้น)", "สมุนไพรช่วยสมานแผล ลดการอักเสบ และบำรุงสมอง"),
    "ZINGIBER OFFICINALE WHOLE": ("ขิง (ทั้งต้น)", "สมุนไพรขับลม บรรเทาอาการคลื่นไส้ อาเจียน และช่วยย่อย"),
}

TYPE_MAP_THAI = {
    "chemical": "สารเคมีเดี่ยว (Chemical)",
    "structurallyDiverse": "สมุนไพร / พืช (Botanical)",
    "polymer": "พอลิเมอร์ / สารช่วย (Polymer)",
    "protein": "โปรตีน / เอนไซม์ (Protein)",
    "nucleicAcid": "กรดนิวคลีอิก (Nucleic Acid)",
    "mixture": "สารผสม (Mixture)"
}

def supabase_upsert_batch(supabase_url: str, service_key: str, table: str, records: List[Dict[str, Any]]):
    """ส่งข้อมูลแบบ Batch Upsert เข้า Supabase REST API (สำหรับคีย์ใหม่ sb_secret_)"""
    if not records:
        return
    url = f"{supabase_url.rstrip('/')}/rest/v1/{table}?on_conflict=unii"
    data_bytes = json.dumps(records).encode('utf-8')
    
    # ส่งเฉพาะ apikey header เท่านั้นสำหรับ sb_secret_ key
    headers = {
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            pass
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8', errors='ignore')
        print(f"[!] Error upserting to {table}: HTTP {e.code} - {err_msg}")
        raise RuntimeError(f"Supabase upsert failed: {err_msg}")

def process_unii_records_file(filepath: str, supabase_url: str, service_key: str, limit: int = 0):
    """อ่านไฟล์ UNII_Records (TSV) แล้วแปลงข้อมูลส่งเข้า Supabase"""
    print(f"[*] เริ่มอ่านไฟล์ข้อมูลสาร: {filepath}")
    batch = []
    count = 0

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        header = f.readline().rstrip('\r\n').split('\t')
        col_map = {name.strip(): idx for idx, name in enumerate(header)}

        for line in f:
            if not line.strip():
                continue
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) <= col_map.get("UNII", 0):
                continue

            unii = parts[col_map.get("UNII", 0)].strip()
            pref_name = parts[col_map.get("DISPLAY_NAME", 1)].strip() if "DISPLAY_NAME" in col_map else ""
            cas = parts[col_map.get("RN", -1)].strip() if "RN" in col_map and col_map["RN"] < len(parts) else None
            formula = parts[col_map.get("MF", -1)].strip() if "MF" in col_map and col_map["MF"] < len(parts) else None
            pubchem = parts[col_map.get("PUBCHEM", -1)].strip() if "PUBCHEM" in col_map and col_map["PUBCHEM"] < len(parts) else None
            sub_type = parts[col_map.get("SUBSTANCE_TYPE", -1)].strip() if "SUBSTANCE_TYPE" in col_map and col_map["SUBSTANCE_TYPE"] < len(parts) else "chemical"
            inchikey = parts[col_map.get("INCHIKEY", -1)].strip() if "INCHIKEY" in col_map and col_map["INCHIKEY"] < len(parts) else None
            smiles = parts[col_map.get("SMILES", -1)].strip() if "SMILES" in col_map and col_map["SMILES"] < len(parts) else None

            # แมปชื่อไทยและคำอธิบาย (รองรับทั้ง Paracetamol และ Acetaminophen)
            thai_info = THAI_NAME_DICT.get(pref_name.upper())
            thai_name = thai_info[0] if thai_info else None
            thai_desc = thai_info[1] if thai_info else None

            item = {
                "unii": unii,
                "preferred_name": pref_name,
                "thai_name": thai_name,
                "cas_rn": cas if cas else None,
                "molecular_formula": formula if formula else None,
                "pubchem_cid": f"CID {pubchem}" if pubchem else None,
                "substance_type": sub_type,
                "type_label_th": TYPE_MAP_THAI.get(sub_type, "สารเคมี/ชีวภาพ"),
                "inchikey": inchikey if inchikey else None,
                "smiles": smiles if smiles else None,
                "thai_desc": thai_desc
            }

            batch.append(item)
            count += 1

            if len(batch) >= 500:
                supabase_upsert_batch(supabase_url, service_key, "substances", batch)
                print(f"[+] ซิงค์ข้อมูลเข้า Supabase แล้ว {count} รายการ...")
                batch = []

            if limit and count >= limit:
                break

        if batch:
            supabase_upsert_batch(supabase_url, service_key, "substances", batch)
            print(f"[✔] ซิงค์ข้อมูลเข้า Supabase สำเร็จครบทั้งหมด {count} รายการ!")

def main():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("[!] ไม่พบ SUPABASE_URL หรือ SUPABASE_SERVICE_ROLE_KEY ใน Environment Variables")
        sys.exit(1)

    filepath = sys.argv[1] if len(sys.argv) > 1 else "UNII_Records_4Aug2026.txt"
    if not os.path.exists(filepath):
        print(f"[!] ไม่พบไฟล์: {filepath}")
        sys.exit(1)

    process_unii_records_file(filepath, supabase_url, service_key)

if __name__ == "__main__":
    main()
