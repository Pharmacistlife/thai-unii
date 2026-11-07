# 🌿 ThaiUNII — ระบบสืบค้นรหัสสารสำคัญและวัตถุดิบทางเภสัชกรรม (FDA UNII) ฉบับภาษาไทย

เว็บแอปพลิเคชันสืบค้นฐานข้อมูล **FDA UNII (Unique Ingredient Identifier)** และสารสำคัญทางเภสัชกรรม/เครื่องสำอาง/สมุนไพรไทย ดีไซน์ **Minimal Glassmorphism ** พร้อมระบบหลังบ้านจัดเก็บข้อมูลบน **Supabase (PostgreSQL + pg_trgm Full-Text Search)** และโฮสต์บน **GitHub Pages** ได้ฟรี 100%

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```text
thai-unii-project/
├── index.html                 # หน้าเว็บ UI กระจกใส เชื่อมต่อ Supabase Live Search
├── schema.sql                 # สคริปต์ SQL สร้างตาราง, Index และฟังก์ชันค้นหาใน Supabase
├── import_to_supabase.py      # สคริปต์ Python นำเข้าข้อมูลและแปลงชื่อไทยเข้า Supabase
├── .github/
│   └── workflows/
│       └── sync_fda_unii.yml  # ระบบอัปเดตอัตโนมัติจาก FDA Archive ทุกสัปดาห์
└── README.md                  # คู่มือการติดตั้งและเปิดใช้งานฉบับสมบูรณ์
```

---

## 🚀 ขั้นตอนการติดตั้งและเปิดใช้งานจริง (4 ขั้นตอนง่ายๆ)

### ขั้นตอนที่ 1: เตรียมฐานข้อมูลบน Supabase (ฟรี 100%)
1. เข้าไปที่ [supabase.com](https://supabase.com) แล้วสมัครสมาชิก/เข้าสู่ระบบ
2. กดปุ่ม **"New Project"** (ตั้งชื่อโปรเจกต์ เช่น `thai-unii` และกำหนดรหัสผ่านฐานข้อมูล)
3. เมื่อสร้างเสร็จแล้ว ให้คลิกที่เมนู **"SQL Editor"** (ไอคอนรูป `>_` ที่แถบด้านซ้าย)
4. เปิดไฟล์ `schema.sql` ในโฟลเดอร์นี้ คัดลอกโค้ดทั้งหมดไปวางในช่อง SQL Editor แล้วกดปุ่ม **"Run"**
   > *ตาราง `substances`, `substance_synonyms`, `legacy_uniis`, และฟังก์ชันสืบค้น `search_thai_unii` จะถูกสร้างขึ้นพร้อมข้อมูลตัวอย่างทันที*
5. ไปที่เมนู **Project Settings** (ไอคอนฟันเฟืองด้านล่างซ้าย) -> เลือกแท็บ **"API"**
6. คัดลอกค่า 2 ตัวนี้เก็บไว้:
   * **Project URL** (เช่น `https://abcdefghijklm.supabase.co`)
   * **anon public API Key** (เช่น `eyJhbGciOiJIUzI1NiIsIn...`)

---

### ขั้นตอนที่ 2: เชื่อมต่อหน้าเว็บกับ Supabase
1. เปิดไฟล์ `index.html` ด้วยโปรแกรมแก้ไขข้อความ (เช่น VS Code, Notepad)
2. เลื่อนลงมาที่บรรทัดประมาณ 380 ในแท็ก `<script>` จะพบตัวแปร:
   ```javascript
   const SUPABASE_CONFIG = {
     url: 'วาง_Project_URL_ที่นี่', 
     anonKey: 'วาง_anon_public_key_ที่นี่'
   };
   ```
3. นำค่าจากขั้นตอนที่ 1 มาวางแทนที่ แล้วกดบันทึกไฟล์ (Save)

---

### ขั้นตอนที่ 3: เอาขึ้น GitHub และเปิดเว็บสาธารณะ (GitHub Pages)
1. เข้าสู่ระบบ [github.com](https://github.com) แล้วสร้างคลังเก็บโค้ดใหม่ (**New Repository**) ตั้งชื่อว่า `thai-unii` (เลือกตั้งค่าเป็น Public)
2. อัปโหลดไฟล์ทั้งหมดในโฟลเดอร์นี้ขึ้นไปบน GitHub
3. ไปที่แท็บ **Settings** ของ Repository -> เลือกเมนู **Pages** ที่แถบซ้าย
4. ในหัวข้อ **Build and deployment**:
   * Source: เลือก **Deploy from a branch**
   * Branch: เลือก **main** และโฟลเดอร์ **/ (root)** แล้วกด **Save**
5. รอประมาณ 1 นาที คุณจะได้รับลิงก์เว็บไซต์พร้อมใช้งานทันที เช่น `https://<ชื่อผู้ใช้ของคุณ>.github.io/thai-unii/`

---

### ขั้นตอนที่ 4: ตั้งค่าระบบ Auto-Sync หลังบ้าน (ทำงานเงียบๆ 100%)
หากต้องการให้ GitHub Actions ดึงข้อมูลอัปเดตใหม่จาก [precisionFDA Archive](https://precision.fda.gov/uniisearch/archive) เข้า Supabase อัตโนมัติทุกสัปดาห์:
1. ไปที่แท็บ **Settings** ใน GitHub Repository -> เลือก **Secrets and variables** -> **Actions**
2. กดปุ่ม **"New repository secret"** เพื่อเพิ่มกุญแจ 2 ตัว:
   * **Name**: `SUPABASE_URL` | **Secret**: วาง Project URL ของคุณ
   * **Name**: `SUPABASE_SERVICE_ROLE_KEY` | **Secret**: วาง Service Role Key จากหน้า Supabase API Settings *(คีย์นี้สำหรับเขียนข้อมูลหลังบ้าน ห้ามเปิดเผยต่อสาธารณะ)*
3. เท่านี้ระบบจะรันอัปเดตอัตโนมัติทุกวันจันทร์ หรือคุณสามารถกดปุ่ม **"Run workflow"** ในแท็บ **Actions** เพื่อสั่งรันได้ทันที

---

## 💡 จุดเด่นของสถาปัตยกรรมนี้
* **ความเร็วสูง**: ใช้ Trigram Full-Text Search บน PostgreSQL ค้นหาแบบ Fuzzy ได้แม้ผู้ใช้จะพิมพ์ชื่อไม่ครบ
* **ประหยัดค่าใช้จ่าย**: ทำงานบน Free Tier ทั้ง GitHub Pages และ Supabase ไม่มีค่าใช้จ่ายรายเดือน
* **ความปลอดภัยสูง**: เปิดใช้ Row Level Security (RLS) ทำให้ผู้ใช้ทั่วไปอ่านข้อมูลได้อย่างเดียว ไม่สามารถแก้หรือลบข้อมูลในฐานข้อมูลได้
