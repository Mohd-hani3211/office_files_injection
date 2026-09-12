# Advanced Office Files Injection & Staged Payload Tool

## 📌 نبذة عن المشروع
هذا المشروع هو أداة متقدمة مخصصة لأغراض أبحاث الأمن السيبراني واختبارات الاختراق (Red Teaming). تقوم الأداة بحقن ملفات حزمة مايكروسوفت أوفيس (Word, Excel, PowerPoint) بماكروهات برمجية (VBA) تعتمد على تقنية التحميل المسبق (Staged Payload) لتنفيذ اتصالات عكسية (Reverse Shell) بشكل خفي وآمن.

---

## ⚠️ تنويهات هامة قبل البدء
* **بيئة التشغيل:** المشروع يعمل **فقط** على بيئة **Windows**.
* **دعم الملفات:** ملفات الـ PowerPoint (`.pptm`) لا تعمل حالياً بشكل جيد ومستقر.

---

## 🛠️ مكونات المشروع
* `inject_the_file.py`: الملف الأساسي لحقن الملفات أو إنشاء ملفات ملغومة جديدة.
* `generator.py`: لتوليد الحمولة (Payload).
* `HTTP-Server.py`: خادم محلي لرفع وخدمة الحمولة.
* `listener.py`: استقبال الاتصال العكسي (Reverse Shell).
* `requirements.txt`: المكتبات المطلوبة لتشغيل السكريبتات.

---

## 🚀 طريقة الاستخدام

1. **تحميل الأداة:**
   قم بتحميل المشروع أو استنساخه من المستودع عبر الأمر:
   ```bash
   git clone [https://github.com/Mohd-hani3211/office_files_injection.git](https://github.com/Mohd-hani3211/office_files_injection.git)
   cd office_files_injection