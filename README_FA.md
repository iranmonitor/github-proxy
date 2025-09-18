# پروکسی گیت‌هاب برای سی‌پنل

یک پروکسی سبک **Flask** برای `raw.githubusercontent.com`، مناسب هاست اشتراکی cPanel.
✅ لینک‌های `raw.githubusercontent.com` به دامنه پروکسی شما تغییر می‌کنند تا اسکریپت‌ها در مناطق مسدود شده کار کنند.

> تست / دمو: [https://github.iranmonitor.net](https://github.iranmonitor.net)

### ویژگی‌ها
- Flask + requests، قابل نصب روی cPanel
- جایگزینی raw.githubusercontent.com با github.iranmonitor.net
- پشتیبانی از اسکریپت‌ها، JSON، فایل‌های کانفیگ؛ فایل‌های باینری بدون تغییر عبور می‌کنند
- مناسب توسعه‌دهندگان در مناطق مسدود شده

### نصب
1. آپلود `proxy.py` و `requirements.txt` در **Application root** (مثلاً `github-prox/`)
2. در cPanel → Setup Python App:
   - نسخه پایتون: 3.9+
   - فایل شروع: `proxy.py`
   - نقطه ورود: `app`
   - نصب پکیج‌ها از `requirements.txt`
3. ری‌استارت برنامه و اختصاص ساب‌دامنه (مثلاً `github.iranmonitor.net`)
4. فعال‌سازی SSL برای HTTPS در صورت امکان

### نحوه استفاده
لینک اصلی GitHub:
```
https://raw.githubusercontent.com/user/repo/branch/file.sh
```
لینک پروکسی:
```
https://github.iranmonitor.net/user/repo/branch/file.sh
```
تمام لینک‌های `raw.githubusercontent.com` داخل فایل‌های متنی به صورت خودکار جایگزین می‌شوند.

### نکات
- برای ترافیک بالا، کش کردن فایل‌ها پیشنهاد می‌شود
- مناسب میزبانی فایل‌های حجیم نیست
