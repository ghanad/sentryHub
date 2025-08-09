# راهنمای Template اسلک (Slack) در SentryHub

این راهنما توضیح می‌دهد چگونه در صفحه ادمین اسلک، Template پیام را با داده‌ی نمونه‌ی یک `AlertGroup` رندر کنید، پیش‌نمایش بگیرید و نتیجه را به کانال اسلک ارسال کنید.
توجه: منطق Match و ارسال در Slack اکنون کاملاً Group-centric است؛ تمام قوانین و قالب‌ها بر اساس AlertGroup ارزیابی و تولید می‌شوند.

نکته جدید: پشتیبانی از لیبل channel

- از این پس، اگر قانون اسلک کانالی تعیین نکرده باشد، مقدار labels.channel در AlertGroup برای تعیین کانال استفاده می‌شود.
- اولویت نهایی انتخاب کانال:

  1. slack_channel تعریف‌شده در Rule
  2. لیبل alert_group.labels.channel (با نرمال‌سازی خودکار)
  3. مقدار پیش‌فرض SLACK_DEFAULT_CHANNEL (پیش‌فرض: #general)

قوانین UI:

- برای بهره‌گیری از لیبل channel، کافی است Rule عمومی بسازید که slack_channel مشخص نکند و صرفاً match_criteria آن را تعیین کنید. در این حالت، کانال از labels.channel گرفته می‌شود.
- اگر می‌خواهید همیشه به یک کانال خاص ارسال شود، در Rule مقدار slack_channel را تعیین کنید؛ این مقدار بر لیبل غلبه می‌کند.

نرمال‌سازی مقدار channel:
- ورودی‌های مانند "#ops" یا "@ops" یا " ops " پشتیبانی می‌شوند و قبل از ارسال نرمال‌سازی می‌گردند.

## مسیر صفحه
- صفحه ادمین اسلک: `/integrations/slack/admin/`
- صفحه راهنما: `/integrations/slack/admin/guide/`

## امکانات صفحه ادمین
در این صفحه دو بخش وجود دارد:
1. ارسال پیام ساده: یک پیام متنی ساده به کانال اسلک ارسال می‌کند.
2. تست Template (Preview & Send): پیام را با استفاده از Template جنگو رندر می‌کند. می‌توانید پیش‌نمایش بگیرید و سپس پیام رندرشده را ارسال کنید.

نکته: فرم ادمین برای تست، همچنان نیاز به وارد کردن کانال دارد و مستقل از منطق Rule/Label کار می‌کند. این صفحه صرفاً برای تست ارسال/قالب است.

## مدل داده مورد استفاده (AlertGroup)
شیء `AlertGroup` (منبع قالب‌ها و Match) دارای فیلدهای زیر است:

- `fingerprint` (string, unique)
- `name` (string)
- `labels` (JSON dict) — شامل کلیدهایی مانند `alertname`, `instance`, `job`, ... و در صورت نیاز `channel`
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

توجه: سیستم اسلک اکنون کاملاً بر اساس AlertGroup کار می‌کند. AlertInstance در منطق Slack استفاده نمی‌شود و بهتر است به آن در قالب‌ها/قوانین اشاره‌ای نشود.

## نحوه‌ی نوشتن Template
> **⚠️ مهم:** سیستم جدید فقط و فقط با `AlertGroup` کار می‌کند. هیچ دسترسی مستقیم به `alertname` یا متغیرهای سطح بالا وجود ندارد. تمام داده‌ها باید از طریق شیء `alert_group` دسترسی پیدا کنند.

در قالب‌ها تنها یک متغیر اصلی در دسترس است:

- `{{ alert_group }}`: شیء کامل AlertGroup که به تمام فیلدهای آن دسترسی دارید:
  - `{{ alert_group.name }}`
  - `{{ alert_group.labels.instance }}`
  - `{{ alert_group.labels.alertname }}`  ← برای دسترسی به نام هشدار از labels
  - `{{ alert_group.labels.channel }}`  ← اگر قصد دارید کانال مقصد را هم داخل پیام نشان دهید
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
کانال: {{ alert_group.labels.channel }}
```

## Extra Context (افزودن داده‌های سفارشی)
می‌توانید JSON سفارشی وارد کنید تا مقادیر داخل نمونه‌ی `alert_group` را تغییر دهید.

ساختار پیشنهادی:
```json
{
  "labels": { "team": "ops", "environment": "prod", "channel": "ops-alerts" },
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
کانال مقصد: {{ alert_group.labels.channel|default:"(بر اساس Rule یا مقدار پیش‌فرض)" }}
```

## پیش‌نمایش و ارسال
1. کانال را وارد کنید (مثلاً `#alerts` یا `C0123ABC`). توجه: این فقط برای تست دستی در صفحه ادمین است و ربطی به منطق Rule/Label ندارد.
2. Template را بنویسید.
3. در صورت نیاز، `Extra Context (JSON)` را پر کنید.
4. روی «Preview» کلیک کنید تا خروجی رندر را ببینید.
5. اگر نتیجه مطلوب بود، «Send Rendered» را بزنید تا پیام به کانال ارسال شود.

## مثال آماده
Template:
```
{{ alert_group.labels.alertname }} | {{ alert_group.labels.instance }}
وضعیت: {{ alert_group.current_status }} | شدت: {{ alert_group.severity }}
منبع: {{ alert_group.source }} | کانال: {{ alert_group.labels.channel|default:"#general" }}
```
Extra Context:
```json
{
  "labels": { "service": "payments", "channel": "backend-alerts" },
  "alert_group": { "source": "prometheus", "severity": "critical" }
}
```
Rendered (نمونه):
```
HighCPUUsage | server1:9100
وضعیت: firing | شدت: critical
منبع: prometheus | کانال: backend-alerts
```

## منطق Match و انتخاب کانال Slack (Group-centric)
- قوانین Slack در مدل [integrations/models.py](integrations/models.py:80) در کلاس `SlackIntegrationRule` تعریف می‌شوند.
- فیلد `match_criteria` یک JSON Object است که تنها بر اساس `AlertGroup` ارزیابی می‌شود:
  - کلیدهایی با پیشوند `labels__` برای مقایسه با `alert_group.labels` (مثلاً `labels__team`, `labels__severity`).
  - سایر کلیدها، فیلدهای مستقیم `AlertGroup` هستند و می‌توانند Lookup هم داشته باشند (مثل `source`, `jira_issue_key__isnull`).
- اولویت‌بندی انتخاب Rule: بیشترین تعداد معیار تطبیق، سپس `priority` و سپس نام قانون؛ پیاده‌سازی در [integrations/services/slack_matcher.py](integrations/services/slack_matcher.py:11).
- انتخاب کانال (Channel Resolution) در زمان ارسال انجام می‌شود: [python.process_slack_for_alert_group()](integrations/tasks.py:279) با استفاده از [python.SlackRuleMatcherService.resolve_channel()](integrations/services/slack_matcher.py:45)
  - اول Rule.slack_channel
  - بعد labels.channel
  - در نهایت تنظیمات `SLACK_DEFAULT_CHANNEL` (پیش‌فرض: #general، قابل تغییر در [python.settings](sentryHub/settings.py:288))

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
