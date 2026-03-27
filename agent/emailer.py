"""
Email digest generator and SMTP sender.

Compresses raw findings into a ≤100-word, bullets-only daily brief via Claude,
then sends it via SMTP (supports Gmail, Outlook, SendGrid relay, etc.).
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anthropic

import config

logger = logging.getLogger(__name__)


# ── Digest generation ─────────────────────────────────────────────────────────

_DIGEST_SYSTEM = """\
You are an expert at writing ultra-concise executive intelligence briefs.
Your sole job: compress competitive intelligence findings into a ≤100-word \
bullet-point briefing for a Veeva (VEEV) investor/executive.

STRICT RULES — violating any rule makes the brief unusable:
1. Maximum 100 words TOTAL. Count every word. Hard limit.
2. Bullet points ONLY. No intro sentences, no closing sentences, no headings.
3. Each bullet: company name (bold in HTML) + 5–8 words of signal.
4. Lead with the most strategically significant finding.
5. Omit low-signal noise. If a finding doesn't matter to a GWRE investor, skip it.
6. Never repeat the same company twice unless two truly distinct events.
7. If no meaningful findings exist, output exactly one line:
   • No significant competitive updates today.
"""

_DIGEST_USER_TEMPLATE = """\
Today's findings ({date}) — compress into a ≤100-word bullet brief:

{findings_block}

Output ONLY the bullet points. Start immediately with the first bullet (•).
"""


def _format_findings_block(findings: list[dict]) -> str:
    if not findings:
        return "(no findings)"
    lines = []
    for f in findings:
        vc = f"[{f['vc_firm']}] " if f.get("vc_firm") and f["vc_firm"] != "N/A" else ""
        lines.append(f"- [{f['relevance']}] {f['company']} ({f['type']}): {vc}{f['description']}")
    return "\n".join(lines)


def generate_digest(findings: list[dict]) -> str:
    """
    Use Claude to compress findings into a ≤100-word bullet brief.
    Returns the plain-text bullet list.
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    user_content = _DIGEST_USER_TEMPLATE.format(
        date=datetime.now().strftime("%B %d, %Y"),
        findings_block=_format_findings_block(findings),
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=_DIGEST_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    text = response.content[0].text.strip()
    logger.debug("Generated digest (%d words):\n%s", len(text.split()), text)
    return text


# ── HTML formatting ───────────────────────────────────────────────────────────

def _to_html(subject: str, plain_bullets: str) -> str:
    """Wrap plain bullet text in a clean HTML email."""
    # Convert • bullets to styled HTML list items
    items_html = ""
    for line in plain_bullets.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading bullet char
        content = line.lstrip("•·-").strip()
        # Bold the company name (text before first colon)
        if ":" in content:
            company, rest = content.split(":", 1)
            content = f"<strong>{company.strip()}</strong>:{rest}"
        items_html += f"<li style='margin-bottom:8px;'>{content}</li>\n"

    today_str = datetime.now().strftime("%B %d, %Y")
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:0 auto;padding:24px;color:#1a1a2e;">
  <h2 style="font-size:18px;border-bottom:2px solid #003087;padding-bottom:8px;margin-bottom:16px;">
    VEEV Intel Brief &mdash; {today_str}
  </h2>
  <ul style="padding-left:20px;line-height:1.7;font-size:14px;">
    {items_html}
  </ul>
  <hr style="margin-top:24px;border:none;border-top:1px solid #eee;">
  <p style="font-size:11px;color:#999;margin-top:8px;">
    GWRE Research Agent &bull; Automated daily competitive brief &bull; {today_str}
  </p>
</body>
</html>"""


# ── SMTP sending ──────────────────────────────────────────────────────────────

def _send_smtp(subject: str, plain_body: str, html_body: str) -> None:
    """Send a multipart plain+HTML email via SMTP with STARTTLS."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.EMAIL_TO

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    recipients = [r.strip() for r in config.EMAIL_TO.split(",")]

    with smtplib.SMTP(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(config.EMAIL_SMTP_USER, config.EMAIL_SMTP_PASS)
        server.sendmail(config.EMAIL_FROM, recipients, msg.as_string())

    logger.info("Email sent → %s | subject: %s", config.EMAIL_TO, subject)


# ── Public interface ──────────────────────────────────────────────────────────

def send_digest(findings: list[dict], digest_text: str | None = None) -> None:
    """
    Dispatch the daily digest by email.

    digest_text: pass a pre-generated digest string to avoid a second Claude
    call (main.py generates it once and shares it with the database layer).
    If omitted, the digest is generated here.

    If SMTP credentials are not configured, the digest is printed to stdout
    so the agent still works out of the box during development.
    """
    today_str = datetime.now().strftime("%B %d, %Y")
    subject = f"VEEV Intel Brief – {today_str}"

    plain_body = digest_text if digest_text is not None else generate_digest(findings)
    html_body  = _to_html(subject, plain_body)

    smtp_configured = all([
        config.EMAIL_SMTP_HOST,
        config.EMAIL_SMTP_USER,
        config.EMAIL_SMTP_PASS,
        config.EMAIL_FROM,
        config.EMAIL_TO,
    ])

    if smtp_configured:
        try:
            _send_smtp(subject, plain_body, html_body)
        except Exception as exc:
            logger.error("SMTP send failed: %s — printing to stdout instead", exc)
            _print_digest(subject, plain_body)
    else:
        logger.warning("SMTP not configured — printing digest to stdout")
        _print_digest(subject, plain_body)


def _print_digest(subject: str, body: str) -> None:
    sep = "─" * 60
    print(f"\n{sep}\nSubject: {subject}\n{sep}\n{body}\n{sep}\n")
