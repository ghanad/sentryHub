# راهنمای تنظیم قوانین یکپارچه‌سازی Jira در SentryHub

## مقدمه

این صفحه راهنما به شما در ایجاد و مدیریت "Jira Integration Rules" در SentryHub کمک می‌کند. این قوانین به شما اجازه می‌دهند تا به صورت خودکار بر اساس هشدارهای دریافتی از Alertmanager، تیکت‌هایی را در Jira ایجاد کرده یا به‌روزرسانی کنید. تنظیم صحیح این قوانین می‌تواند به طور قابل توجهی فرآیند پیگیری و رفع مشکلات را بهبود بخشد.

## هدف قوانین

هدف اصلی این قوانین، تعریف **شرایطی** است که تحت آن یک هشدار خاص باید منجر به یک **اقدام** در Jira شود (ایجاد تیکت جدید یا افزودن کامنت به تیکت موجود).

## ایجاد/ویرایش یک قانون

برای ایجاد یا ویرایش قانون، به بخش "Integrations" -> "Jira Rules" در منوی SentryHub بروید. فرم شامل بخش‌های زیر است:

### ۱. تنظیمات عمومی (General Settings)

* **Name:** یک نام منحصر به فرد و توصیفی برای قانون خود انتخاب کنید (مثلاً `Create Critical DB Incidents`, `Comment on Resolved Infra Alerts`).
* **Is Active:** این چک‌باکس مشخص می‌کند که آیا قانون فعال است و باید برای هشدارهای ورودی اعمال شود یا خیر. قوانین غیرفعال نادیده گرفته می‌شوند.
* **Priority:** یک عدد صحیح که اولویت این قانون را نسبت به سایر قوانین مشخص می‌کند. **عدد بالاتر به معنای اولویت بیشتر است.** زمانی که یک هشدار با معیارهای چند قانون مطابقت دارد، قانونی با بالاترین اولویت انتخاب می‌شود (جزئیات بیشتر در بخش "منطق تطبیق قوانین").

### ۲. تنظیمات Jira (Jira Configuration)

* **Jira Project Key:** کلید پروژه‌ای در Jira که تیکت‌ها باید در آن ایجاد شوند (مثلاً `OPS`, `SAM`, `INFRA`). این مقدار معمولاً توسط ادمین سیستم در تنظیمات SentryHub (`settings.py`) مشخص شده و ممکن است قابل ویرایش نباشد.
* **Jira Issue Type:** نوع تیکتی که باید ایجاد شود (مثلاً `Incident`, `Task`, `Bug`). لیست انواع موجود معمولاً توسط ادمین سیستم در تنظیمات SentryHub (`settings.py`) تعریف می‌شود.
* **Assignee:** (اختیاری) **نام کاربری (Username)** دقیق کاربری در Jira که تیکت ایجاد شده باید به او اختصاص یابد. اگر خالی بماند، تیکت بدون Assignee ایجاد می‌شود. اگر نام کاربری نامعتبر باشد، SentryHub سعی می‌کند تیکت را بدون Assignee ایجاد کند.
* **Watchers:** (اختیاری) لیستی از **نام‌های کاربری (Username)** دقیق کاربران Jira که باید به عنوان Watcher به تیکت اضافه شوند. نام‌های کاربری را با **کاما (,)** از هم جدا کنید (مثلاً `user1,user2,another.user`).

### ۳. معیارهای تطبیق (Match Criteria)

این بخش **مهم‌ترین** قسمت برای تعیین **کدام هشدارها** باید این قانون را فعال کنند.

* **فرمت:** باید یک **آبجکت JSON معتبر** باشد (با `{}` شروع و تمام شود).
* **منطق:** تطابق **دقیق** انجام می‌شود. تمام جفت‌های **کلید: مقدار** که در این JSON تعریف می‌کنید، **باید** دقیقاً با همان کلید و مقدار در بخش `labels` هشدار دریافتی وجود داشته باشند تا قانون مطابقت پیدا کند.
* **مثال‌ها:**
    * `{"severity": "critical"}`: فقط هشدارهایی که دارای لیبل `severity` با مقدار دقیق `critical` هستند، مطابقت پیدا می‌کنند.
    * `{"job": "node_exporter", "instance": "server1.example.com"}`: فقط هشدارهایی که **هم** لیبل `job` با مقدار `node_exporter` و **هم** لیبل `instance` با مقدار `server1.example.com` دارند، مطابقت پیدا می‌کنند.
    * `{}`: (توصیه نمی‌شود) یک آبجکت خالی با تمام هشدارها مطابقت پیدا می‌کند، اما به دلیل عدم وجود معیار خاص، احتمالاً توسط قوانین با اولویت بالاتر یا معیارهای بیشتر نادیده گرفته می‌شود (به بخش "منطق تطبیق قوانین" مراجعه کنید). بهتر است همیشه معیارهای مشخصی تعریف کنید.

### ۴. قالب‌های تیکت Jira (Jira Issue Templates)

این بخش‌ها محتوای تیکت یا کامنتی که در Jira ایجاد می‌شود را با استفاده از **زبان قالب جنگو (Django Template Language - DTL)** تعریف می‌کنند. شما می‌توانید از متغیرهای مربوط به هشدار در این قالب‌ها استفاده کنید.

* **Jira Title Template:** قالبی برای عنوان (Summary) تیکت Jira.
    * مثال: `[SentryHub Alert] {{ alertname }} firing on {{ labels.instance }}`
* **Jira Description Template:** قالبی برای توضیحات (Description) تیکت Jira. می‌توانید از تگ‌های قالب جنگو مانند `{% if %}` یا `{% for %}` و همچنین markup مخصوص Jira (مانند `{code}`, `*bold*`, `h2.`) استفاده کنید.
    * مثال در بخش "مثال کامل یک قانون" آورده شده است.
* **Jira Update Comment Template:** قالبی برای کامنتی که هنگام تغییر وضعیت هشدار (مثلاً Firing -> Resolved یا Resolved -> Firing) به تیکت موجود اضافه می‌شود. متغیر `{{ alert_status }}` در اینجا بسیار مفید است.
    * مثال: `Alert status changed to *{{ alert_status|title }}* at {{ now|date:"Y-m-d H:i" }}. {% if alert_status == 'resolved' %}Problem seems to be resolved.{% endif %}`

### ۵. متغیرهای قابل استفاده در قالب‌ها (Available Template Variables)

هنگام رندر کردن قالب‌های عنوان، توضیحات و کامنت، متغیرهای زیر در دسترس هستند:

* `{{ alert_group }}`: آبجکت مدل `AlertGroup` جنگو. می‌توانید به فیلدهای آن دسترسی پیدا کنید:
    * `{{ alert_group.name }}`
    * `{{ alert_group.fingerprint }}`
    * `{{ alert_group.labels }}` (دیکشنری لیبل‌ها)
    * `{{ alert_group.severity }}`
    * `{{ alert_group.instance }}`
    * `{{ alert_group.first_occurrence }}` (آبجکت datetime)
    * `{{ alert_group.last_occurrence }}` (آبجکت datetime)
    * ...
* `{{ rule }}`: آبجکت مدل `JiraIntegrationRule` مربوط به همین قانون.
* `{{ alert_status }}`: رشته وضعیت فعلی که باعث اجرای تسک شده (`'firing'` یا `'resolved'`).
* `{{ labels }}`: دیکشنری کامل `labels` مربوط به هشدار.
* `{{ annotations }}`: دیکشنری کامل `annotations` مربوط به **آخرین** `AlertInstance` هشدار.
* `{{ alertname }}`: مقدار لیبل `alertname` (میانبر برای `labels.alertname`).
* `{{ fingerprint }}`: مقدار `fingerprint` هشدار (همان `alert_group.fingerprint`).
* `{{ latest_instance }}`: آبجکت مدل `AlertInstance` مربوط به آخرین وضعیت هشدار (ممکن است `None` باشد). می‌توانید به فیلدهای آن دسترسی پیدا کنید:
    * `{{ latest_instance.started_at }}` (آبجکت datetime)
    * `{{ latest_instance.ended_at }}` (آبجکت datetime یا `None`)
    * `{{ latest_instance.annotations }}` (دیکشنری)
    * ...
* `{{ occurred_at }}`: آبجکت datetime زمان شروع آخرین `AlertInstance` (یا `last_occurrence` گروه اگر نمونه‌ای یافت نشد).
* `{{ occurred_at_str }}`: رشته فرمت شده زمان وقوع به وقت تهران (مثلاً `2023-10-27 15:30:00`).
* `{{ resolved_time }}`: آبجکت datetime زمان دقیق Resolve شدن هشدار (زمان اجرای تسک). این معمولاً در UTC است و برای نمایش در منطقه زمانی دیگر نیاز به فیلتر `timezone` دارد.
* `{{ resolved_time_iso }}`: رشته فرمت شده ISO زمان دقیق Resolve شدن هشدار (زمان اجرای تسک).
* `{{ sentryhub_url }}`: لینک به صفحه جزئیات هشدار در SentryHub.
* `{{ severity }}`: مقدار لیبل `severity` (مثلاً `Critical`, `Warning`).
* `{{ summary_annotation }}`: مقدار انوتیشن `summary` (یا `alertname` اگر `summary` نباشد).
* `{{ description_annotation }}`: مقدار انوتیشن `description` (یا متن پیش‌فرض اگر نباشد).
* `{{ now }}`: آبجکت datetime زمان اجرای تسک (همان `resolved_time` در زمان Resolve شدن).

### ۶. استفاده از منطق در قالب‌ها (Using Template Logic)

می‌توانید از تگ‌های استاندارد Django Template Language استفاده کنید:

* **شرط‌ها (If/Else):**

    ```django
    {% if labels.severity == 'critical' %}
      h1. CRITICAL ALERT!
    {% elif labels.severity == 'warning' %}
      h2. Warning
    {% else %}
      h3. Info
    {% endif %}

    {% if alert_status == 'resolved' %}
      Alert has been resolved.
    {% endif %}
    ```

* **حلقه‌ها (For Loops):**
    ```django
    h3. All Labels:
    {% for key, value in labels.items() %}
      * {{ key }}: {{ value }}
    {% empty %}
      No labels found.
    {% endfor %}
    ```

* **فیلترها (Filters):**
    * `|title`: `{{ alert_status|title }}` -> `Firing` یا `Resolved`
    * `|upper`: `{{ labels.dc|upper }}`
    * `|default:"-"`: `{{ labels.optional_label|default:"N/A" }}`
    * `|date:"Y-m-d H:i"`: `{{ occurred_at|date:"Y-m-d H:i" }}` (برای آبجکت‌های datetime)
    * `|jsonify`: (اگر تعریف شده باشد) برای نمایش دیکشنری به صورت JSON: `{code:json}{{ labels|jsonify }}{code}`

## منطق تطبیق قوانین (Rule Matching Logic)

زمانی که یک هشدار دریافت می‌شود و نیاز به بررسی قوانین Jira دارد (یعنی `firing` است و `silenced` نیست، یا `resolved` است و قبلاً کلید Jira داشته)، SentryHub به ترتیب زیر بهترین قانون مطابق را پیدا می‌کند:

1.  **فیلتر اولیه:** فقط قوانین `is_active=True` در نظر گرفته می‌شوند.
2.  **تطابق معیارها:** تمام قوانینی که `match_criteria` آن‌ها **به طور کامل** توسط `labels` هشدار برآورده می‌شود، پیدا می‌شوند.
3.  **انتخاب خاص‌ترین قانون:** از بین قوانین مطابق، قانونی انتخاب می‌شود که **بیشترین تعداد کلید** را در `match_criteria` خود دارد (یعنی دقیق‌تر و خاص‌تر است).
4.  **اولویت (Priority) به عنوان گره‌گشا:** اگر چند قانون با **تعداد معیارهای یکسان** مطابقت داشته باشند، قانونی با **بالاترین عدد** `priority` انتخاب می‌شود.
5.  **نام به عنوان گره‌گشای نهایی:** اگر اولویت‌ها نیز یکسان باشند، قانونی که نام آن از نظر الفبایی **زودتر** می‌آید، انتخاب می‌شود.

**مهم:** فقط **یک** قانون (بهترین تطابق) برای هر رویداد هشدار (firing یا resolved) اجرا می‌شود.

## مثال کامل یک قانون

* **Name:** `Create High CPU Incident for Prod Servers`
* **Is Active:** `True`
* **Priority:** `10`
* **Jira Project Key:** `OPS`
* **Jira Issue Type:** `Incident`
* **Assignee:** `oncall_admin`
* **Watchers:** `sysadmin1,manager1`
* **Match Criteria:**
    ```json
    {
      "alertname": "HighCPUUsage",
      "severity": "critical",
      "environment": "production"
    }
    ```

* **Jira Title Template:**
    ```django
    [CPU Alert] High CPU on {{ labels.instance }} ({{ severity }})
    ```

* **Jira Description Template:**
    ```django
    h2. High CPU Usage Detected!

    A critical CPU usage alert is firing.

    *Alert Details:*
    | Name | Value |
    |---|---|
    | Fingerprint | {noformat}{{ fingerprint }}{noformat} |
    | Severity | {{ severity }} |
    | Instance | {{ labels.instance }} |
    | Job | {{ labels.job|default:"N/A" }} |
    | Environment | {{ labels.environment }} |
    | Summary | {{ annotations.summary|default:"-" }} |
    | Occurred At | {{ occurred_at_str }} |

    h3. Full Labels
    {code:json}
    {{ labels|jsonify }}
    {code}

    h3. Full Annotations
    {code:json}
    {{ annotations|jsonify }}
    {code}

    Please investigate immediately.

    [Link to Alert in SentryHub|{{ sentryhub_url }}]
    ```

* **Jira Update Comment Template:**

    ```django
    {% load tz %}
    Alert status changed to *{{ alert_status|title }}* at {% if alert_status == 'resolved' %}{{ resolved_time|timezone:"Asia/Tehran"|date:"Y-m-d H:i:s" }}{% else %}{{ now|timezone:"Asia/Tehran"|date:"Y-m-d H:i:s" }}{% endif %}.

    {% if alert_status == 'resolved' %}
    The high CPU usage issue seems to be resolved.
    {% elif alert_status == 'firing' %}
    The high CPU usage issue is firing again. Please re-investigate.
    *Current Summary:* {{ annotations.summary|default:"-" }}
    {% endif %}

    [Link to Alert in SentryHub|{{ sentryhub_url }}]
    ```
