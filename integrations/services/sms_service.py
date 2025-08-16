import logging
from typing import List, Optional, Dict, Any

from django.conf import settings
import requests

from integrations.exceptions import SmsNotificationError

logger = logging.getLogger(__name__)


class SmsService:
    """Service responsible for sending SMS messages via external provider."""

    # Provider status codes mapped to human-readable Persian messages.
    STATUS_MESSAGES = {
        0: "ارسال موفق",
        1: "شماره گیرنده نادرست است",
        2: "شماره فرستنده نادرست است",
        3: "پارامتر encoding نامعتبراست. (بررسی صحت و هم‌خوانی متن پيامک با encoding انتخابی)",
        4: "پارامتر mclass نامعتبر است",
        6: "پارامتر UDH نامعتبر است",
        8: "زمان ارسال پيامک، خارج از باره‌ی مجاز ارسال پيامک تبليغاتی (۷ الی ۲۲) است",
        13: "محتويات پيامک (تركيب UDH و متن) خالی است. (بررسی دوباره‌ی متن پيامک و پارامتر UDH)",
        14: "مانده اعتبار ريالی مورد نياز برای ارسال پیامک کافی نيست",
        15: "سرور در هنگام ارسال پيام مشغول برطرف نمودن ايراد داخلی بوده است. (ارسال مجدد درخواست)",
        16: "حساب غيرفعال است. (تماس با واحد فروش سيستم‌های ارتباطی)",
        17: "حساب منقضی شده است. (تماس با واحد فروش سيستم‌های ارتباطی)",
        18: "نام كاربری و يا كلمه عبور نامعتبر است. (بررسی مجدد نام كاربری و كلمه عبور)",
        19: "درخواست معتبر نيست. (تركيب نام كاربری، رمز عبور و دامنه اشتباه است. تماس با واحد فروش برای دريافت كلمه عبور جديد)",
        20: "شماره فرستنده به حساب تعلق ندارد",
        22: "اين سرويس برای حساب فعال نشده است",
        23: "در حال حاضر امکان پردازش درخواست جديد وجود ندارد، لطفا دوباره سعی كنيد. (ارسال مجدد درخواست)",
        24: "شناسه پيامک معتبر نيست. (ممكن است شناسه پيامک اشتباه و يا متعلق به پيامكی باشد كه بيش از يک روز از ارسال آن گذشته)",
        25: "نام متد درخواستی معتبر نيست. (بررسی نگارش نام متد با توجه به بخش متدها در اين راهنما)",
        27: "شماره گيرنده در ليست سياه اپراتور قرار دارد. (ارسال پيامک‌های تبليغاتی برای اين شماره امكان‌پذير نيست)",
        28: "شماره گیرنده، بر اساس پیش‌شماره در حال حاضر در مگفا مسدود است",
        29: "آدرس IP مبدا، اجازه دسترسی به این سرویس را ندارد",
        30: "تعداد بخش‌های پیامک بیش از حد مجاز استاندارد (۲۶۵ عدد) است",
        31: "فرمت JSON‌ ارسالی صحيح نیست",
        33: "مشترک، دريافت پيامک از اين سرشماره را مسدود نموده است (لغو ۱۱)",
        34: "اطلاعات تایید‌شده برای اين شماره وجود ندارد",
        35: "وجود کاراکتر نامعتبر در متن پیامک",
        101: "طول آرايه پارامتر messageBodies با طول آرايه گيرندگان تطابق ندارد",
        102: "طول آرايه پارامتر messageClass با طول آرايه گيرندگان تطابق ندارد",
        103: "طول آرايه پارامتر senderNumbers با طول آرايه گيرندگان تطابق ندارد",
        104: "طول آرايه پارامتر udhs با طول آرايه گيرندگان تطابق ندارد",
        105: "طول آرايه پارامتر priorities با طول آرايه گيرندگان تطابق ندارد",
        106: "آرايه‌ی گيرندگان خالی است",
        107: "طول آرايه پارامتر گيرندگان بيشتر از طول مجاز است",
        108: "آرايه‌ی فرستندگان خالی است",
        109: "طول آرايه پارامتر encoding با طول آرايه گيرندگان تطابق ندارد",
        110: "طول آرايه پارامتر checkingMessageIds با طول آرايه گيرندگان تطابق ندارد",
    }

    def __init__(self):
        self.send_url = getattr(settings, "SMS_PROVIDER_SEND_URL", "")
        self.balance_url = getattr(settings, "SMS_PROVIDER_BALANCE_URL", "")
        self.username = getattr(settings, "SMS_PROVIDER_USERNAME", "")
        self.password = getattr(settings, "SMS_PROVIDER_PASSWORD", "")
        self.domain = getattr(settings, "SMS_PROVIDER_DOMAIN", "")
        self.sender = getattr(settings, "SMS_PROVIDER_SENDER", "")

    def send_sms(self, phone_number: str, message: str, fingerprint: str = "N/A") -> Optional[Dict[str, Any]]:
        """Convenience wrapper for sending a single SMS."""
        return self.send_bulk([phone_number], message, fingerprint)

    def send_bulk(
        self, phone_numbers: List[str], message: str, fingerprint: str = "N/A"
    ) -> Optional[Dict[str, Any]]:
        """Send the same message to multiple recipients in a single request."""
        if not all([self.send_url, self.username, self.password, self.domain, self.sender]):
            logger.error(
                "SmsService (FP: %s): SMS provider send URL or credentials not configured.",
                fingerprint,
            )
            return None

        headers = {"accept": "application/json", "cache-control": "no-cache"}
        payload_json = {
            "senders": [self.sender] * len(phone_numbers),
            "messages": [message] * len(phone_numbers),
            "recipients": phone_numbers,
        }
        try:
            resp = requests.post(
                self.send_url,
                headers=headers,
                auth=(f"{self.username}/{self.domain}", self.password),
                json=payload_json,
                timeout=10,
            )
            resp.raise_for_status()
            try:
                resp_data = resp.json()
            except ValueError:
                resp_data = resp.text
            logger.info(
                "SmsService (FP: %s): provider response: %s",
                fingerprint,
                resp_data,
            )
            return resp_data
        except requests.exceptions.RequestException as exc:
            logger.warning(
                "SmsService (FP: %s): network error sending SMS: %s", fingerprint, exc
            )
            raise SmsNotificationError("Network error during SMS send") from exc

    def get_balance(self):
        if not all([self.balance_url, self.username, self.password, self.domain]):
            logger.error("SmsService: balance endpoint or credentials not configured.")
            return None

        headers = {"accept": "application/json", "cache-control": "no-cache"}
        try:
            resp = requests.get(
                self.balance_url,
                headers=headers,
                auth=(f"{self.username}/{self.domain}", self.password),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("credit", data)
            return data
        except requests.exceptions.RequestException as exc:
            logger.warning("SmsService: error fetching balance: %s", exc)
            return None
