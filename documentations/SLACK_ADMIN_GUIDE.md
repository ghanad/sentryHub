# راهنمای تست Template اسلک (Slack) در SentryHub

این راهنما توضیح می‌دهد چگونه در صفحه ادمین اسلک، Template پیام را با داده‌ی نمونه (Mock Alert) رندر کنید، پیش‌نمایش بگیرید و نتیجه را به کانال اسلک ارسال کنید.

## مسیر صفحه
- صفحه ادمین اسلک: `/integrations/slack/admin/`
- صفحه راهنما: `/integrations/slack/admin/guide/`

## امکانات صفحه ادمین
در این صفحه دو بخش وجود دارد:
1. ارسال پیام ساده: یک پیام متنی ساده به کانال اسلک ارسال می‌کند (بدون Template).
2. تست Template (Preview & Send): پیام را با استفاده از Template جنگو رندر می‌کند. می‌توانید پیش‌نمایش بگیرید و سپس پیام رندرشده را ارسال کنید.

## نحوه‌ی نوشتن Template
از دستورهای Template جنگو استفاده کنید:
- متغیرهای اصلی:
  - `{{ alertname }}`: نام هشدار
  - `{{ labels.instance }}`: نام/آدرس اینستنس
  - `{{ labels.severity }}`: شدت
  - `{{ annotations.summary }}`: خلاصه
  - `{{ annotations.description }}`: توضیحات
  - `{{ status }}`: وضعیت (برای Mock: `firing`)
  - `{{ generator_url }}`: لینک مرجع
- ایموجی‌ها:
  - از یونیکد مستقیم (مثل 🔥 ✅ ⚠️) یا شورت‌کدهای اسلک استفاده کنید (مثل `:fire:`، `:white_check_mark:`).
  - علاوه بر این، یک Map آماده در Context با نام `icons` وجود دارد:
    - `{{ icons.fire }}` → `:fire:`
    - `{{ icons.check }}` → `:white_check_mark:`
    - `{{ icons.warning }}` → `:warning:`
    - `{{ icons.bell }}` → `:bell:`
    - `{{ icons.x }}` → `:x:`
    - `{{ icons.info }}` → `:information_source:`
    - `{{ icons.rocket }}` → `:rocket:`
    - `{{ icons.boom }}` → `:boom:`

نمونه ساده:
```
{% verbatim %}{{ icons.fire }} هشدار {{ alertname }} روی {{ labels.instance }}
شدت: {{ labels.severity }}
خلاصه: {{ annotations.summary }}
{% endverbatim %}
```

## Extra Context (افزودن داده‌های سفارشی)
برای تست سناریوهای گوناگون می‌توانید JSON سفارشی وارد کنید تا به Context اضافه شود. ساختار پیشنهادی:
```json
{
  "labels": { "team": "ops", "environment": "prod" },
  "annotations": { "note": "check dashboards" },
  "vars": { "ticket_id": "OPS-123", "owner": "alice" }
}
```
- کلیدهای داخل `labels` و `annotations` روی مقادیر پایه Merge می‌شوند.
- مقادیر داخل `vars` به صورت `{{ vars.your_key }}` در Template قابل استفاده‌اند.

نمونه Template با extra_context:
```
{% verbatim %}{{ icons.warning }} تیم {{ labels.team }} | تیکت: {{ vars.ticket_id }}
{{ alertname }} روی {{ labels.instance }} | وضعیت: {{ status }}
یادداشت: {{ annotations.note }}
{% endverbatim %}
```

## پیش‌نمایش و ارسال
1. کانال را وارد کنید (مثلاً `#alerts` یا `C0123ABC`).
2. Template را بنویسید.
3. در صورت نیاز، `Extra Context (JSON)` را پر کنید.
4. روی «Preview» کلیک کنید تا خروجی رندر را ببینید.
5. اگر نتیجه مطلوب بود، «Send Rendered» را بزنید تا پیام به کانال ارسال شود.

## نکات تکمیلی
- قالب موتور Template، جنگو است؛ از فیلترها و حلقه‌ها نیز می‌توانید استفاده کنید:
  ```
  {% verbatim %}{% for k, v in labels.items %}{{ k }} = {{ v }}
  {% endfor %}{% endverbatim %}
  ```
- در صورت خطای Template (مثلاً سینتکس اشتباه)، پیغام خطا نمایش داده می‌شود.
- برای کانال‌ها، هم نام با `#` و هم ID کانال مورد قبول است. سرویس ارسال، نام کانال را نرمال‌سازی می‌کند.
- ایموجی‌ها در اسلک هم به صورت یونیکد و هم به صورت `:shortcode:` پشتیبانی می‌شوند.

## مثال‌های آماده
Template:
```
{% verbatim %}{{ icons.fire }} {{ alertname }} | {{ labels.instance }}
شدت: {{ labels.severity }}
{{ annotations.summary }}
{{ generator_url }}{% endverbatim %}
```
Extra Context:
```json
{
  "labels": { "service": "payments" },
  "annotations": { "note": "Page latency high" },
  "vars": { "ticket_id": "OPS-987" }
}
```

Rendered (نمونه):
```
:fire: HighCPUUsage | server1:9100
شدت: critical
CPU usage is above 90% for the last 5 minutes.
http://prometheus.example.local/graph?g0.expr=cpu_usage
```

## مشکلات رایج
- TemplateSyntaxError: از بلاک‌های {% verbatim %} برای نمایش نمونه کد با {{ }} در خود راهنما استفاده کنید یا سینتکس را بررسی کنید.
- JSON نامعتبر در Extra Context: ساختار JSON را اعتبارسنجی کنید (آکولاد، کوتیشن‌ها و …).
- ارسال به اسلک ناموفق: مقدار `SLACK_INTERNAL_ENDPOINT` را در تنظیمات بررسی کنید و لاگ‌ها را ببینید.

## قالب‌های پیام (Message Templates)
در قوانین اسلک می‌توانید دو نوع قالب پیام تعریف کنید: یکی برای زمانی که هشدار در وضعیت firing قرار دارد و دیگری برای زمانی که resolved می‌شود. این قالب‌ها از زبان قالب جنگو (Django Template Language) پشتیبانی می‌کنند.

- Message Template: برای هشدارهای firing.
- Resolved Message Template: برای هشدارهای resolved. اگر خالی باشد، برای این وضعیت پیامی ارسال نمی‌شود.

### متغیرهای قابل استفاده در قالب‌ها
- `{{ alert_group }}`: آبجکت کامل AlertGroup که به تمام فیلدهای آن دسترسی دارید:
  - `{{ alert_group.name }}`
  - `{{ alert_group.source }}`
  - `{{ alert_group.jira_issue_key }}`
  - `{{ alert_group.acknowledged }}`
  - `{{ alert_group.total_firing_count }}`
  - `{{ alert_group.first_occurrence }}` (آبجکت datetime)
- `{{ labels }}`: دیکشنری کامل labels هشدار.
  - مثال: `{{ labels.instance }}`, `{{ labels.severity }}`, ...
- `{{ annotations }}`: دیکشنری کامل annotations از آخرین نمونه هشدار.
  - مثال: `{{ annotations.summary }}`, `{{ annotations.description }}`, ...
- `{{ alertname }}`: میانبری برای `labels.alertname`.
- `{{ status }}`: وضعیت هشدار (`firing` یا `resolved`).
- `icons`: یک دیکشنری آماده برای استفاده از ایموجی‌های اسلک:
  - `{{ icons.fire }}` → `:fire:`
  - `{{ icons.check }}` → `:white_check_mark:`
  - `{{ icons.warning }}` → `:warning:`
  - `{{ icons.bell }}` → `:bell:`
  - ...

### مثال Template
Generated django
```
{% verbatim %}{{ icons.fire }} *{{ alertname }}* on `{{ labels.instance }}`
> Severity: `{{ labels.severity }}` | Source: `{{ alert_group.source }}`
> Summary: {{ annotations.summary }}
{% if alert_group.jira_issue_key %}
> Jira Ticket: <https://jira.tsetmc.com/browse/{{ alert_group.jira_issue_key }}|{{ alert_group.jira_issue_key }}>
{% endif %}{% endverbatim %}
```
