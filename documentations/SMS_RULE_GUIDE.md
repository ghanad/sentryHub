# راهنمای تنظیم قوانین یکپارچه‌سازی پیامک (SMS) در SentryHub

## مقدمه

این صفحه راهنما به شما در ایجاد و مدیریت "SMS Integration Rules" در SentryHub کمک می‌کند. این قوانین به شما اجازه می‌دهند تا به صورت خودکار بر اساس هشدارهای دریافتی از Alertmanager، پیامک‌هایی را به شماره‌های از پیش تعریف‌شده ارسال کنید. تنظیم صحیح این قوانین می‌تواند به طور قابل توجهی فرآیند اطلاع‌رسانی و پاسخ به حوادث را بهبود بخشد.

## هدف قوانین

هدف اصلی این قوانین، تعریف **شرایطی** است که تحت آن یک هشدار خاص باید منجر به **ارسال پیامک** به یک یا چند گیرنده مشخص شود.

## ایجاد/ویرایش یک قانون

برای ایجاد یا ویرایش قانون، به بخش "Integrations" -> "SMS Rules" در منوی SentryHub بروید. فرم شامل بخش‌های زیر است:

### ۱. تنظیمات عمومی (General Settings)

*   **Name:** یک نام منحصر به فرد و توصیفی برای قانون خود انتخاب کنید (مثلاً `Send Critical SMS for DB Alerts`, `SMS for Resolved Infra Issues`).
*   **Is Active:** این چک‌باکس مشخص می‌کند که آیا قانون فعال است و باید برای هشدارهای ورودی اعمال شود یا خیر. قوانین غیرفعال نادیده گرفته می‌شوند.
*   **Priority:** یک عدد صحیح که اولویت این قانون را نسبت به سایر قوانین مشخص می‌کند. **عدد بالاتر به معنای اولویت بیشتر است.** زمانی که یک هشدار با معیارهای چند قانون مطابقت دارد، قانونی با بالاترین اولویت انتخاب می‌شود (جزئیات بیشتر در بخش "منطق تطبیق قوانین").

### ۲. تنظیمات گیرندگان (Recipient Settings)

*   **Recipients:** لیستی از **نام‌های گیرندگان** که در بخش "PhoneBook" SentryHub تعریف شده‌اند. نام‌ها را با **کاما (,)** از هم جدا کنید (مثلاً `admin,oncall_team,manager`). پیامک به شماره تلفن‌های مرتبط با این نام‌ها ارسال خواهد شد.
*   **Use SMS Annotation:** اگر این گزینه فعال باشد، SentryHub به جای استفاده از لیست `Recipients` تعریف‌شده در این قانون، سعی می‌کند گیرندگان را از `annotations['sms']` آخرین `AlertInstance` استخراج کند. مقدار `annotations['sms']` باید یک رشته با نام‌های گیرندگان جدا شده با کاما باشد (مثلاً `{"sms": "user1,user2"}`). این قابلیت برای ارسال پویا به گیرندگان مختلف بر اساس محتوای هشدار مفید است.

### ۳. معیارهای تطبیق (Match Criteria)

این بخش **مهم‌ترین** قسمت برای تعیین **کدام هشدارها** باید این قانون را فعال کنند.

*   **فرمت:** باید یک **آبجکت JSON معتبر** باشد (با `{}` شروع و تمام شود).
*   **منطق:** تطابق **دقیق** انجام می‌شود. تمام جفت‌های **کلید: مقدار** که در این JSON تعریف می‌کنید، **باید** دقیقاً با همان کلید و مقدار در بخش `labels` هشدار دریافتی وجود داشته باشند تا قانون مطابقت پیدا کند.
*   **مثال‌ها:**
    *   `{"severity": "critical"}`: فقط هشدارهایی که دارای لیبل `severity` با مقدار دقیق `critical` هستند، مطابقت پیدا می‌کنند.
    *   `{"job": "node_exporter", "instance": "server1.example.com"}`: فقط هشدارهایی که **هم** لیبل `job` با مقدار `node_exporter` و **هم** لیبل `instance` با مقدار `server1.example.com` دارند، مطابقت پیدا می‌کنند.
    *   `{}`: (توصیه نمی‌شود) یک آبجکت خالی با تمام هشدارها مطابقت پیدا می‌کند، اما به دلیل عدم وجود معیار خاص، احتمالاً توسط قوانین با اولویت بالاتر یا معیارهای بیشتر نادیده گرفته می‌شود (به بخش "منطق تطبیق قوانین" مراجعه کنید). بهتر است همیشه معیارهای مشخصی تعریف کنید.

### ۴. قالب‌های پیامک (SMS Templates)

این بخش‌ها محتوای پیامکی که ارسال می‌شود را با استفاده از **زبان قالب جنگو (Django Template Language - DTL)** تعریف می‌کنند. شما می‌توانید از متغیرهای مربوط به هشدار در این قالب‌ها استفاده کنید.

*   **Firing Template:** قالبی برای متن پیامک که هنگام فعال شدن (Firing) هشدار ارسال می‌شود.
    *   مثال: `Alert: {{ alertname }} on {{ labels.instance }} is {{ alert_group.current_status|upper }}. Severity: {{ severity }}`
*   **Resolved Template:** (اختیاری) قالبی برای متن پیامک که هنگام رفع شدن (Resolved) هشدار ارسال می‌شود. اگر این فیلد خالی بماند، هیچ پیامکی برای وضعیت Resolved ارسال نخواهد شد.
    *   مثال: `Alert: {{ alertname }} on {{ labels.instance }} is now RESOLVED.`

### ۵. متغیرهای قابل استفاده در قالب‌ها (Available Template Variables)

هنگام رندر کردن قالب‌های پیامک، متغیرهای زیر در دسترس هستند:

*   `{{ alert_group }}`: آبجکت مدل `AlertGroup` جنگو. می‌توانید به فیلدهای آن دسترسی پیدا کنید:
    *   `{{ alert_group.name }}`
    *   `{{ alert_group.fingerprint }}`
    *   `{{ alert_group.labels }}` (دیکشنری لیبل‌ها)
    *   `{{ alert_group.severity }}`
    *   `{{ alert_group.instance }}`
    *   `{{ alert_group.first_occurrence }}` (آبجکت datetime)
    *   `{{ alert_group.last_occurrence }}` (آبجکت datetime)
    *   `{{ alert_group.current_status }}` (مثلاً `firing` یا `resolved`)
    *   ...
*   `{{ latest_instance }}`: آبجکت مدل `AlertInstance` مربوط به آخرین وضعیت هشدار (ممکن است `None` باشد). می‌توانید به فیلدهای آن دسترسی پیدا کنید:
    *   `{{ latest_instance.started_at }}` (آبجکت datetime)
    *   `{{ latest_instance.ended_at }}` (آبجکت datetime یا `None`)
    *   `{{ latest_instance.annotations }}` (دیکشنری)
    *   ...
*   `{{ annotations }}`: دیکشنری کامل `annotations` مربوط به **آخرین** `AlertInstance` هشدار (میانبر برای `latest_instance.annotations`).
*   `{{ labels }}`: دیکشنری کامل `labels` مربوط به هشدار (میانبر برای `alert_group.labels`).
*   `{{ alertname }}`: مقدار لیبل `alertname` (میانبر برای `labels.alertname`).
*   `{{ fingerprint }}`: مقدار `fingerprint` هشدار (همان `alert_group.fingerprint`).
*   `{{ severity }}`: مقدار لیبل `severity` (مثلاً `Critical`, `Warning`).
*   `{{ now }}`: آبجکت datetime زمان اجرای تسک.

### ۶. استفاده از منطق در قالب‌ها (Using Template Logic)

می‌توانید از تگ‌های استاندارد Django Template Language استفاده کنید:

*   **شرط‌ها (If/Else):**

    ```django
{% if labels.severity == 'critical' %}
  CRITICAL ALERT!
{% elif labels.severity == 'warning' %}
  Warning
{% else %}
  Info
{% endif %}

{% if alert_group.current_status == 'resolved' %}
  Alert has been resolved.
{% endif %}
    ```

*   **حلقه‌ها (For Loops):**
    ```django
All Labels:
{% for key, value in labels.items() %}
  - {{ key }}: {{ value }}
{% empty %}
  No labels found.
{% endfor %}
    ```

*   **فیلترها (Filters):**
    *   `|title`: `{{ alert_group.current_status|title }}` -> `Firing` یا `Resolved`
    *   `|upper`: `{{ labels.dc|upper }}`
    *   `|default:"-"`: `{{ labels.optional_label|default:"N/A" }}`
    *   `|date:"Y-m-d H:i"`: `{{ latest_instance.started_at|date:"Y-m-d H:i" }}` (برای آبجکت‌های datetime)

## منطق تطبیق قوانین (Rule Matching Logic)

زمانی که یک هشدار دریافت می‌شود و نیاز به بررسی قوانین SMS دارد (یعنی `firing` است و `silenced` نیست، یا `resolved` است)، SentryHub به ترتیب زیر بهترین قانون مطابق را پیدا می‌کند:

1.  **فیلتر اولیه:** فقط قوانین `is_active=True` در نظر گرفته می‌شوند.
2.  **تطابق معیارها:** تمام قوانینی که `match_criteria` آن‌ها **به طور کامل** توسط `labels` هشدار برآورده می‌شود، پیدا می‌شوند.
3.  **انتخاب خاص‌ترین قانون:** از بین قوانین مطابق، قانونی انتخاب می‌شود که **بیشترین تعداد کلید** را در `match_criteria` خود دارد (یعنی دقیق‌تر و خاص‌تر است).
4.  **اولویت (Priority) به عنوان گره‌گشا:** اگر چند قانون با **تعداد معیارهای یکسان** مطابقت داشته باشند، قانونی با **بالاترین عدد** `priority` انتخاب می‌شود.
5.  **نام به عنوان گره‌گشای نهایی:** اگر اولویت‌ها نیز یکسان باشند، قانونی که نام آن از نظر الفبایی **زودتر** می‌آید، انتخاب می‌شود.

**مهم:** فقط **یک** قانون (بهترین تطابق) برای هر رویداد هشدار (firing یا resolved) اجرا می‌شود.

## مثال کامل یک قانون

*   **Name:** `Critical CPU SMS for Admins`
*   **Is Active:** `True`
*   **Priority:** `100`
*   **Recipients:** `admin,oncall_engineer`
*   **Use SMS Annotation:** `False`
*   **Match Criteria:**
    ```json
{
  "alertname": "HighCPUUsage",
  "severity": "critical",
  "environment": "production"
}
    ```

*   **Firing Template:**
    ```django
🔥 CRITICAL ALERT: {{ alertname }} on {{ labels.instance }} ({{ severity|upper }}).
Details: {{ annotations.summary|default:"N/A" }}.
Check SentryHub: {{ sentryhub_url }}
    ```

*   **Resolved Template:**
    ```django
✅ RESOLVED: {{ alertname }} on {{ labels.instance }}.
Issue cleared.
    ```

## مشکلات رایج

*   **TemplateSyntaxError:** سینتکس قالب را بررسی کنید.
*   **JSON نامعتبر در Match Criteria:** ساختار JSON را اعتبارسنجی کنید.
*   **گیرنده یافت نشد:** اطمینان حاصل کنید که نام‌های گیرنده در `PhoneBook` تعریف شده‌اند و املای آن‌ها صحیح است.
*   **ارسال پیامک ناموفق:** تنظیمات ارائه‌دهنده پیامک در `settings.py` (مانند `SMS_PROVIDER_SEND_URL`, `USERNAME`, `PASSWORD`, `DOMAIN`, `SENDER`) را بررسی کنید و لاگ‌های سیستم را ببینید.