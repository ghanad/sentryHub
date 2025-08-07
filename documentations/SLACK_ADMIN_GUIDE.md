# راهنمای تست Template اسلک (Slack) در SentryHub

این راهنما توضیح می‌دهد چگونه در صفحه ادمین اسلک، Template پیام را با داده‌ی نمونه‌ی یک `AlertGroup` رندر کنید، پیش‌نمایش بگیرید و نتیجه را به کانال اسلک ارسال کنید.
توجه: منطق Match و ارسال در Slack اکنون کاملاً Group-centric است؛ تمام قوانین و قالب‌ها بر اساس AlertGroup ارزیابی و تولید می‌شوند.

## مسیر صفحه
- صفحه ادمین اسلک: `/integrations/slack/admin/`
- صفحه راهنما: `/integrations/slack/admin/guide/`

## امکانات صفحه ادمین
در این صفحه دو بخش وجود دارد:
1. ارسال پیام ساده: یک پیام متنی ساده به کانال اسلک ارسال می‌کند.
2. تست Template (Preview & Send): پیام را با استفاده از Template جنگو رندر می‌کند. می‌توانید پیش‌نمایش بگیرید و سپس پیام رندرشده را ارسال کنید.

## مدل داده مورد استفاده (AlertGroup)
شیء `AlertGroup` (منبع قالب‌ها و Match) دارای فیلدهای زیر است:

- `fingerprint` (string, unique)
- `name` (string)
- `labels` (JSON dict) — شامل کلیدهایی مانند `alertname`, `instance`, `job`, ...
- `severity` (one of: `critical`, `warning`, `info`)
- `instance` (string|null) — آدرس/نام میزبان استخراج‌شده از labels
- `source` (string|null) — شناسه منبع Alertmanager
- `first_occurrence` (datetime)
- `last_occurrence` (datetime)
- `current_status` (one of: `firing`, `resolved`)
- `total_firing_count` (int)
- `acknowledged` (bool)
- `acknowledged_by` (User|null)
- `acknowledgement_time` (datetime|null)
- `documentation` (docs.AlertDocumentation|null)
- `is_silenced` (bool)
- `silenced_until` (datetime|null)
- `jira_issue_key` (string|null)

توجه: AlertInstance در منطق Slack استفاده نمی‌شود و بهتر است به آن در قالب‌ها/قوانین اشاره‌ای نشود.

## نحوه‌ی نوشتن Template
در قالب‌ها تنها یک متغیر اصلی در دسترس است:

- `{{ alert_group }}`: شیء کامل AlertGroup که به تمام فیلدهای آن دسترسی دارید:
  - `{{ alert_group.name }}`
  - `{{ alert_group.labels.instance }}`
  - `{{ alert_group.labels.alertname }}`
  - `{{ alert_group.current_status }}`
  - `{{ alert_group.source }}`
  - `{{ alert_group.severity }}`
  - `{{ alert_group.jira_issue_key }}` و سایر فیلدها

برای درج ایموجی می‌توانید مستقیماً از یونیکد (مثل 🔥) یا شورت‌کدهای اسلک (`:fire:`) استفاده کنید.

نمونه ساده:
```
{{ alert_group.labels.alertname }} روی {{ alert_group.labels.instance }}
وضعیت: {{ alert_group.current_status }}
شدت: {{ alert_group.severity }}
```

## Extra Context (افزودن داده‌های سفارشی)
می‌توانید JSON سفارشی وارد کنید تا مقادیر داخل نمونه‌ی `alert_group` را تغییر دهید.

ساختار پیشنهادی:
```json
{
  "labels": { "team": "ops", "environment": "prod" },
  "alert_group": { "source": "custom_source", "severity": "critical" }
}
```
- کلیدهای داخل `labels` روی `alert_group.labels` ادغام می‌شوند.
- کلیدهای داخل `alert_group` به صورت مستقیم روی ویژگی‌های شیء `alert_group` اعمال می‌شوند.

نمونه Template با extra_context:
```
تیم: {{ alert_group.labels.team }}
هشدار {{ alert_group.labels.alertname }} در {{ alert_group.labels.instance }}
منبع: {{ alert_group.source }} | شدت: {{ alert_group.severity }}
```

## پیش‌نمایش و ارسال
1. کانال را وارد کنید (مثلاً `#alerts` یا `C0123ABC`).
2. Template را بنویسید.
3. در صورت نیاز، `Extra Context (JSON)` را پر کنید.
4. روی «Preview» کلیک کنید تا خروجی رندر را ببینید.
5. اگر نتیجه مطلوب بود، «Send Rendered» را بزنید تا پیام به کانال ارسال شود.

## مثال آماده
Template:
```
{{ alert_group.labels.alertname }} | {{ alert_group.labels.instance }}
وضعیت: {{ alert_group.current_status }} | شدت: {{ alert_group.severity }}
منبع: {{ alert_group.source }}
```
Extra Context:
```json
{
  "labels": { "service": "payments" },
  "alert_group": { "source": "prometheus", "severity": "critical" }
}
```
Rendered (نمونه):
```
HighCPUUsage | server1:9100
وضعیت: firing | شدت: critical
منبع: prometheus
```

## منطق Match قوانین Slack (Group-centric)
- قوانین Slack در مدل [integrations/models.py](integrations/models.py:80) در کلاس `SlackIntegrationRule` تعریف می‌شوند.
- فیلد `match_criteria` یک JSON Object است که تنها بر اساس `AlertGroup` ارزیابی می‌شود:
  - کلیدهایی با پیشوند `labels__` برای مقایسه با `alert_group.labels` (مثلاً `labels__team`, `labels__severity`).
  - سایر کلیدها، فیلدهای مستقیم `AlertGroup` هستند و می‌توانند Lookup هم داشته باشند (مثل `source`, `jira_issue_key__isnull`).
- اولویت‌بندی: در صورت تعدد تطبیق، انتخاب نهایی بر اساس بیشترین تعداد کلیدهای معیار (specificity)، سپس `priority` و سپس نام قانون انجام می‌شود؛ پیاده‌سازی در [integrations/services/slack_matcher.py](integrations/services/slack_matcher.py:11).

نمونه `match_criteria`:
```json
{
  "labels__team": "ops",
  "labels__environment": "prod",
  "source": "prometheus",
  "jira_issue_key__isnull": true
}
```

## قالب‌های پیام (Message Templates)
در قوانین اسلک می‌توانید دو نوع قالب پیام تعریف کنید:
- `message_template` برای وضعیت `firing`
- `resolved_message_template` برای وضعیت `resolved` (اگر خالی باشد برای resolved پیامی ارسال نمی‌شود)

نمونه Template:
```
{{ alert_group.labels.alertname }} روی {{ alert_group.labels.instance }}
منبع: {{ alert_group.source }} | وضعیت: {{ alert_group.current_status }}
```

## مشکلات رایج
- TemplateSyntaxError: سینتکس قالب را بررسی کنید.
- JSON نامعتبر در Extra Context: ساختار JSON را اعتبارسنجی کنید.
- ارسال به اسلک ناموفق: مقدار `SLACK_INTERNAL_ENDPOINT` را در تنظیمات بررسی کنید و لاگ‌ها را ببینید.
