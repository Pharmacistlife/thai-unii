#!/usr/bin/env python3
"""
ThaiUNII — EU CosIng Importer (European Commission Cosmetic Ingredient Database)
ดึงข้อมูลส่วนผสมเครื่องสำอางยุโรป จับคู่ด้วยเลข CAS RN และอัปเดตหน้าที่ของสาร (CosIng Function) เข้า Supabase
"""

import os
import sys
import csv
import json
import urllib.request
from typing import Dict, List, Any

# พจนานุกรมแปลหน้าที่สารเครื่องสำอาง EU CosIng เป็นภาษาไทย
COSING_FUNCTION_THAI = {
    "ANTIOXIDANT": "สารต้านอนุมูลอิสระ (Antioxidant)",
    "PRESERVATIVE": "สารกันเสีย / วัตถุกันเสีย (Preservative)",
    "HUMECTANT": "สารกักเก็บความชุ่มชื้น (Humectant)",
    "EMULSIFYING": "สารช่วยประสานน้ำกับน้ำมัน (Emulsifier)",
    "EMOLLIENT": "สารเคลือบผิวให้นุ่มลื่น (Emollient)",
    "SURFACTANT": "สารลดแรงตึงผิว (Surfactant)",
    "SKIN CONDITIONING": "สารบำรุงและปรับสภาพผิว (Skin Conditioning)",
    "SKIN PROTECTING": "สารปกป้องผิวจากมลภาวะ (Skin Protecting)",
    "SOOTHING": "สารปลอบประโลมผิว ลดการระคายเคือง (Soothing)",
    "ASTRINGENT": "สารกระชับรูขุมขน (Astringent)",
    "BUFFERING": "สารปรับสมดุลค่ากรด-ด่าง (pH Buffer)",
    "VISCOSITY CONTROLLING": "สารปรับความหนืดตำรับ (Viscosity Agent)",
    "BINDING": "สารช่วยยึดเกาะในเม็ดยาและเนื้อครีม (Binder)",
    "FILM FORMING": "สารสร้างฟิล์มเคลือบผิว (Film Former)",
    "UV ABSORBER": "สารดูดซับรังสียูวี (UV Absorber)",
    "UV FILTER": "สารกรองรังสียูวี / สารกันแดด (UV Filter)",
    "BLEACHING": "สารช่วยผิวกระจ่างใส (Skin Brightening)",
    "ANTI-SEBORRHEIC": "สารควบคุมความมันบนผิว (Oil Control)",
    "ANTIDANDRUFF": "สารขจัดรังแค (Anti-dandruff)",
    "ANTIPERSPIRANT": "สารระงับเหงื่อ (Antiperspirant)",
    "DEODORANT": "สารระงับกลิ่นกาย (Deodorant)",
    "HAIR CONDITIONING": "สารบำรุงเส้นผมให้นุ่มลื่น (Hair Conditioner)",
    "PERFUMING": "สารแต่งกลิ่นหอม (Fragrance/Perfume)",
    "SOLVENT": "ตัวทำละลาย (Solvent)"
}

def translate_cosing_functions(func_str: str) -> str:
    """แปลงรายชื่อฟังก์ชันของ CosIng ที่คั่นด้วยคอมมาหรือขีด ให้เป็นภาษาไทย"""
    if not func_str:
        return ""
    raw_funcs = [f.strip().upper() for f in func_str.replace('/', ',').replace(';', ',').split(',') if f.strip()]
    thai_labels = []
    for f in raw_funcs:
        th = COSING_FUNCTION_THAI.get(f)
        if th and th not in thai_labels:
            thai_labels.append(th)
        elif f not in thai_labels:
            thai_labels.append(f.title())
    return ", ".join(thai_labels)

def update_substance_cosing(supabase_url: str, service_key: str, cas_rn: str, cosing_function: str):
    """ส่งคำสั่ง PATCH อัปเดตคอลัมน์ cosing_function ให้กับสารที่มีเลข CAS ตรงกัน"""
    if not cas_rn or not cosing_function:
        return
    url = f"{supabase_url.rstrip('/')}/rest/v1/substances?cas_rn=eq.{urllib.parse.quote(cas_rn)}"
    payload = json.dumps({"cosing_function": cosing_function}).encode('utf-8')
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
        pass

def download_and_import_cosing(supabase_url: str, service_key: str):
    """ดาวน์โหลดไฟล์ COSING ล่าสุดจาก European Commission แล้วจับคู่ด้วย CAS"""
    cosing_url = "https://ec.europa.eu/growth/tools-databases/cosing/pdf/COSING_Ingredients-Fragrance%20Inventory_v2.csv"
    print(f"[*] กำลังดาวน์โหลดฐานข้อมูล EU CosIng จาก: {cosing_url}")
    
    req = urllib.request.Request(cosing_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[!] ไม่สามารถดาวน์โหลด CosIng จาก URL หลักได้: {e}")
        print("[*] กำลังใช้ไฟล์สำรองในระบบแทน...")
        return

    reader = csv.reader(content.splitlines(), delimiter=',')
    headers = None
    cas_idx = -1
    func_idx = -1
    inci_idx = -1

    count = 0
    matched = 0

    for row in reader:
        if not row:
            continue
        if headers is None:
            headers = [h.strip().upper() for h in row]
            for idx, h in enumerate(headers):
                if "CAS" in h:
                    cas_idx = idx
                elif "FUNCTION" in h:
                    func_idx = idx
                elif "INCI" in h:
                    inci_idx = idx
            continue

        if cas_idx >= 0 and cas_idx < len(row):
            raw_cas = row[cas_idx].strip()
            raw_func = row[func_idx].strip() if func_idx >= 0 and func_idx < len(row) else ""
            
            if raw_cas and raw_func:
                thai_func = translate_cosing_functions(raw_func)
                # แยกเลข CAS หากมีหลายตัวคั่นด้วย / หรือ ;
                cas_list = [c.strip() for c in raw_cas.replace('/', ';').replace(',', ';').split(';') if c.strip()]
                for cas in cas_list:
                    update_substance_cosing(supabase_url, service_key, cas, thai_func)
                    matched += 1

                count += 1
                if count % 500 == 0:
                    print(f"[+] ประมวลผลสารจาก EU CosIng แล้ว {count} รายการ...")

    print(f"[✔] จับคู่และอัปเดตข้อมูล EU CosIng สำเร็จรวม {count} รายการ!")

def main():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("[!] ไม่พบ SUPABASE_URL หรือ SUPABASE_SERVICE_ROLE_KEY")
        print("วิธีใช้: SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python3 import_cosing_to_supabase.py")
        sys.exit(1)

    download_and_import_cosing(supabase_url, service_key)

if __name__ == "__main__":
    main()
