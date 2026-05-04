import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .base import BaseNotifier


class EmailNotifier(BaseNotifier):
    """
    Sends the digest as an HTML email via SMTP (e.g., Gmail).

    Required environment variables:
        SMTP_USER  — sender address (e.g. yourname@gmail.com)
        SMTP_PASS  — app password (not your main Google password)
        SMTP_TO    — recipient address
        SMTP_HOST  — optional, defaults to smtp.gmail.com
        SMTP_PORT  — optional, defaults to 587
    """

    def __init__(self, smtp_user: str = None, smtp_pass: str = None, smtp_to: str = None,
                 smtp_host: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_user = smtp_user or os.getenv("SMTP_USER", "")
        self.smtp_pass = smtp_pass or os.getenv("SMTP_PASS", "")
        self.smtp_to   = smtp_to   or os.getenv("SMTP_TO", "")
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    @property
    def name(self) -> str:
        return "email"

    def _to_html(self, plain_text: str) -> str:
        """Convert plain-text digest (with emoji) to a simple HTML email."""
        lines = plain_text.split("\n")
        html_lines = ["<html><body style='font-family:Arial,sans-serif;max-width:600px;margin:auto;'>",
                      "<h2 style='color:#2c3e50;'>💓 Founder Heartbeat Digest</h2>",
                      "<hr style='border:1px solid #ecf0f1;'>"]
        for line in lines:
            if not line.strip():
                html_lines.append("<br>")
            elif line.startswith("🟢"):
                html_lines.append(f"<p style='color:#27ae60'><strong>{line}</strong></p>")
            elif line.startswith("🔴"):
                html_lines.append(f"<p style='color:#e74c3c'><strong>{line}</strong></p>")
            elif line.startswith("📌"):
                html_lines.append(f"<p style='color:#2980b9'><strong>{line}</strong></p>")
            elif line.startswith("⏱️"):
                html_lines.append(f"<p style='color:#8e44ad'><em>{line}</em></p>")
            else:
                html_lines.append(f"<p>{line}</p>")
        html_lines.append("<hr><p style='color:#95a5a6;font-size:11px;'>Sent by Founder Heartbeat System</p>")
        html_lines.append("</body></html>")
        return "".join(html_lines)

    def send(self, message: str):
        if not all([self.smtp_user, self.smtp_pass, self.smtp_to]):
            print(f"[Email] SMTP credentials not configured. Digest preview:\n{message}")
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "💓 Founder Heartbeat Digest"
            msg["From"]    = self.smtp_user
            msg["To"]      = self.smtp_to

            msg.attach(MIMEText(message, "plain"))
            msg.attach(MIMEText(self._to_html(message), "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, self.smtp_to, msg.as_string())
            print(f"✅ Email digest sent to {self.smtp_to}")
        except Exception as e:
            print(f"⚠️  Email unavailable: {e}\nDigest:\n{message}")
