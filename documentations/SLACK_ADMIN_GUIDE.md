# راهنمای تست Template اسلک (Slack) در SentryHub

این راهنما توضیح می‌دهد چگونه در صفحه ادمین اسلک، Template پیام را با داده‌ی نمونه‌ی یک `AlertGroup` رندر کنید، پیش‌نمایش بگیرید و نتیجه را به کانال اسلک ارسال کنید.

## مسیر صفحه
- صفحه ادمین اسلک: `/integrations/slack/admin/`
- صفحه راهنما: `/integrations/slack/admin/guide/`

## امکانات صفحه ادمین
در این صفحه دو بخش وجود دارد:
1. ارسال پیام ساده: یک پیام متنی ساده به کانال اسلک ارسال می‌کند.
2. تست Template (Preview & Send): پیام را با استفاده از Template جنگو رندر می‌کند. می‌توانید پیش‌نمایش بگیرید و سپس پیام رندرشده را ارسال کنید.

## نحوه‌ی نوشتن Template
در قالب‌ها تنها یک متغیر اصلی در دسترس است:

- `{{ alert_group }}`: شیء کامل AlertGroup که به تمام فیلدهای آن دسترسی دارید:
  - `{{ alert_group.name }}`
  - `{{ alert_group.labels.instance }}`
  - `{{ alert_group.labels.alertname }}`
  - `{{ alert_group.current_status }}`
  - `{{ alert_group.source }}`
  - `{{ alert_group.jira_issue_key }}` و سایر فیلدها

برای درج ایموجی می‌توانید مستقیماً از یونیکد (مثل 🔥) یا شورت‌کدهای اسلک (`:fire:`) استفاده کنید.

نمونه ساده:
```
{{ alert_group.labels.alertname }} روی {{ alert_group.labels.instance }}
وضعیت: {{ alert_group.current_status }}
```

## Extra Context (افزودن داده‌های سفارشی)
می‌توانید JSON سفارشی وارد کنید تا مقادیر داخل نمونه‌ی `alert_group` را تغییر دهید.

ساختار پیشنهادی:
```json
{
  "labels": { "team": "ops", "environment": "prod" },
  "alert_group": { "source": "custom_source" }
}
```
- کلیدهای داخل `labels` روی `alert_group.labels` ادغام می‌شوند.
- کلیدهای داخل `alert_group` به صورت مستقیم روی ویژگی‌های شیء `alert_group` اعمال می‌شوند.

نمونه Template با extra_context:
```
تیم: {{ alert_group.labels.team }}
هشدار {{ alert_group.labels.alertname }} در {{ alert_group.labels.instance }}
منبع: {{ alert_group.source }}
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
وضعیت: {{ alert_group.current_status }}
```
Extra Context:
```json
{
  "labels": { "service": "payments" },
  "alert_group": { "source": "prometheus" }
}
```
Rendered (نمونه):
```
HighCPUUsage | server1:9100
وضعیت: firing
```

## مشکلات رایج
- TemplateSyntaxError: سینتکس قالب را بررسی کنید.
- JSON نامعتبر در Extra Context: ساختار JSON را اعتبارسنجی کنید.
- ارسال به اسلک ناموفق: مقدار `SLACK_INTERNAL_ENDPOINT` را در تنظیمات بررسی کنید و لاگ‌ها را ببینید.

## قالب‌های پیام (Message Templates)
در قوانین اسلک می‌توانید دو نوع قالب پیام تعریف کنید: یکی برای زمانی که هشدار در وضعیت firing قرار دارد و دیگری برای زمانی که resolved می‌شود. اگر قالب resolved خالی باشد، برای این وضعیت پیامی ارسال نمی‌شود.

### مثال Template
```
{{ alert_group.labels.alertname }} روی {{ alert_group.instance }}
منبع: {{ alert_group.source }}
```
