"""Email. Real SMTP when SMTP_HOST is set; otherwise a dev outbox (log + dev_emails table).

Messages never carry disability or grievance content - only codes and "you have an update".
"""

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import DevEmail

log = logging.getLogger("samavesh.mail")

# Hindi strings are drafts - have a fluent reader review them before the demo.
TEMPLATES = {
    "verify": {
        "en": ("Your Samavesh verification code", "Your verification code is {code}. It expires in 10 minutes."),
        "hi": ("आपका समावेश सत्यापन कोड", "आपका सत्यापन कोड {code} है। यह 10 मिनट में समाप्त हो जाएगा।"),
    },
    "reset": {
        "en": ("Your Samavesh password code", "Your password code is {code}. It expires in 10 minutes."),
        "hi": ("आपका समावेश पासवर्ड कोड", "आपका पासवर्ड कोड {code} है। यह 10 मिनट में समाप्त हो जाएगा।"),
    },
    "invite": {
        "en": (
            "You have been invited to Samavesh",
            "An administrator created an account for you. "
            "Open {origin}/reset-password and request a code to set your password.",
        ),
        "hi": (
            "आपको समावेश में आमंत्रित किया गया है",
            "एक व्यवस्थापक ने आपके लिए खाता बनाया है। "
            "पासवर्ड सेट करने के लिए {origin}/reset-password खोलें और कोड का अनुरोध करें।",
        ),
    },
    "account_exists": {
        "en": (
            "Samavesh sign-up attempt",
            "Someone tried to register with this email, but you already have an account. "
            "Sign in at {origin}/login, or reset your password there if you have forgotten it.",
        ),
        "hi": (
            "समावेश पंजीकरण प्रयास",
            "किसी ने इस ईमेल से पंजीकरण करने का प्रयास किया, लेकिन आपका खाता पहले से मौजूद है। "
            "{origin}/login पर साइन इन करें, या पासवर्ड भूल गए हों तो वहीं रीसेट करें।",
        ),
    },
    "guardian_invite": {
        "en": (
            "You have been named as a parent or guardian on Samavesh",
            "{student} has named you as their parent or guardian. "
            "Create a guardian account with this email address at {origin}/register, "
            "or sign in at {origin}/login if you already have one.",
        ),
        "hi": (
            "आपको समावेश पर माता-पिता या अभिभावक के रूप में नामित किया गया है",
            "{student} ने आपको अपने माता-पिता या अभिभावक के रूप में नामित किया है। "
            "{origin}/register पर इसी ईमेल पते से अभिभावक खाता बनाएँ, "
            "या यदि खाता पहले से है तो {origin}/login पर साइन इन करें।",
        ),
    },
    "update": {
        "en": ("You have an update on Samavesh", "Sign in to see it: {origin}/login"),
        "hi": ("समावेश पर आपके लिए एक अपडेट है", "देखने के लिए साइन इन करें: {origin}/login"),
    },
}


def send_email(db: Session, to: str, locale: str, kind: str, **params) -> None:
    s = get_settings()
    subject, body = TEMPLATES[kind].get(locale, TEMPLATES[kind]["en"])
    body = body.format(origin=s.frontend_origin, **params)

    if not s.smtp_host:
        if s.is_prod:
            log.error("SMTP not configured; dropped %s email", kind)
            return
        log.info("dev email kind=%s to=%s params=%s", kind, to, params)
        db.add(DevEmail(to=to, subject=subject, body=body))
        return

    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.mail_from, to, subject
    msg.set_content(body)
    try:
        # ponytail: sent inline with a timeout; move to a queue if mail volume ever matters.
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException):
        log.exception("failed to send %s email", kind)
