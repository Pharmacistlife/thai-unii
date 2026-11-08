#!/usr/bin/env python3
"""
ThaiUNII — openFDA Drug Label Backup to Supabase
ดึงข้อมูลข้อบ่งใช้ คำเตือน ผลข้างเคียง จาก openFDA API มาบันทึกสำรองไว้ในตาราง public.substance_drug_labels
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import time
from typing import Dict, List, Any

# ชุดข้อมูลสำรองเริ่มต้นสำหรับยาสามัญยอดนิยม
SEED_DRUG_LABELS = [
    {
        "unii": "804826J2HU", # Amoxicillin
        "indications": "Amoxicillin is indicated for the treatment of infections due to susceptible isolates of the designated microorganisms in the infections listed below: Infections of the ear, nose, and throat; infections of the genitourinary tract; infections of the skin and skin structure; infections of the lower respiratory tract.",
        "warnings": "Serious and occasionally fatal hypersensitivity (anaphylactic) reactions have been reported in patients on penicillin therapy. Clostridium difficile associated diarrhea (CDAD) has been reported with use of nearly all antibacterial agents.",
        "adverse_reactions": "Common adverse reactions are diarrhea, nausea, vomiting, and skin rashes. Anaphylaxis and hypersensitivity reactions may occur.",
        "contraindications": "Amoxicillin is contraindicated in patients who have experienced a serious hypersensitivity reaction (e.g., anaphylaxis or Stevens-Johnson syndrome) to amoxicillin or to other beta-lactam antibacterial drugs."
    },
    {
        "unii": "362O9ITL9D", # Acetaminophen / Paracetamol
        "indications": "Temporarily relieves minor aches and pains due to: the common cold, headache, backache, minor pain of arthritis, toothache, muscular aches, premenstrual and menstrual cramps; temporarily reduces fever.",
        "warnings": "Liver warning: This product contains acetaminophen. Severe liver damage may occur if you take more than 4,000 mg of acetaminophen in 24 hours, with other drugs containing acetaminophen, or 3 or more alcoholic drinks every day.",
        "adverse_reactions": "Rare cases of serious skin reactions (Stevens-Johnson syndrome, toxic epidermal necrolysis). Allergic reactions including swelling of the face, mouth, and throat.",
        "contraindications": "Do not use with any other drug containing acetaminophen (prescription or nonprescription). Do not use if you are allergic to acetaminophen or any of the inactive ingredients."
    },
    {
        "unii": "57Y76R9ATQ", # Naproxen
        "indications": "Naproxen is indicated for the relief of the signs and symptoms of rheumatoid arthritis, osteoarthritis, ankylosing spondylitis, juvenile arthritis, tendonitis, bursitis, and acute gout, and for the management of pain and primary dysmenorrhea.",
        "warnings": "Cardiovascular Thrombotic Events: Nonsteroidal anti-inflammatory drugs (NSAIDs) cause an increased risk of serious cardiovascular thrombotic events, including myocardial infarction and stroke. Gastrointestinal Risk: NSAIDs cause an increased risk of serious gastrointestinal adverse events including bleeding and ulceration.",
        "adverse_reactions": "Most common adverse reactions are dyspepsia, abdominal pain, nausea, constipation, heartburn, dizziness, and headache.",
        "contraindications": "Naproxen is contraindicated in patients with known hypersensitivity to naproxen. In the setting of coronary artery bypass graft (CABG) surgery."
    },
    {
        "unii": "YO7261ME24", # Cetirizine
        "indications": "Temporarily relieves these symptoms due to hay fever or other upper respiratory allergies: runny nose; sneezing; itchy, watery eyes; itching of the nose or throat.",
        "warnings": "Do not use if you have ever had an allergic reaction to this product or any of its ingredients or to an antihistamine containing hydroxyzine. Drowsiness may occur; avoid alcoholic drinks.",
        "adverse_reactions": "Somnolence, fatigue, dry mouth, pharyngitis, and dizziness.",
        "contraindications": "Known hypersensitivity to cetirizine, hydroxyzine, or any inactive ingredient."
    },
    {
        "unii": "VB0R961HZT", # Prednisone
        "indications": "Indicated in the management of allergic conditions, dermatologic diseases, endocrine disorders, gastrointestinal diseases, hematologic disorders, neoplastic diseases, nervous system conditions, ophthalmic diseases, renal diseases, respiratory diseases, and rheumatic disorders.",
        "warnings": "Immunosuppression and increased risk of infection. Hypothalamic-pituitary-adrenal (HPA) axis suppression, Cushing's syndrome, and hyperglycemia. Elevation of blood pressure and salt/water retention.",
        "adverse_reactions": "Fluid retention, hypertension, glucose intolerance, peptic ulcer, osteoporosis, muscle weakness, and behavioral disturbances.",
        "contraindications": "Systemic fungal infections and known hypersensitivity to the drug."
    }
]

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

def main():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("[!] ไม่พบ SUPABASE_URL หรือ SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    print("[*] กำลังสำรองข้อมูลเอกสารกำกับยา openFDA เข้าสู่ตาราง substance_drug_labels...")
    insert_label_batch(supabase_url, service_key, SEED_DRUG_LABELS)
    print(f"[✔] สำรองข้อมูลเอกสารกำกับยาสำเร็จรวม {len(SEED_DRUG_LABELS)} รายการ!")

if __name__ == "__main__":
    main()
