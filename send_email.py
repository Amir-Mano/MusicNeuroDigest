"""Skill 3: build and send the weekly digest email via Gmail SMTP."""

import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def _authors_line(a: dict) -> str:
    authors = ", ".join(a["authors"][:3]) + (" et al." if len(a["authors"]) > 3 else "")
    return f"{authors} -- {a['journal']} ({a['pub_date']})"


def _build_plain_text(articles: list, must_read: dict | None, classic: dict | None) -> str:
    lines = [f"Music & Neuroplasticity Digest -- {date.today().isoformat()}", ""]

    if must_read:
        lines.append("MUST-READ THIS WEEK")
        lines.append(must_read["title"])
        lines.append(_authors_line(must_read))
        lines.append(must_read["summary"])
        lines.append(must_read["url"])
        lines.append("")

    others = [a for a in articles if not must_read or a["pmid"] != must_read["pmid"]]
    if others:
        lines.append("ALSO NEW THIS WEEK")
        for a in others:
            lines.append(a["title"])
            lines.append(_authors_line(a))
            lines.append(a["summary"])
            lines.append(a["url"])
            lines.append("")

    if classic:
        lines.append("CLASSIC WORTH REVISITING (high-impact, not new)")
        lines.append(classic["title"])
        lines.append(_authors_line(classic))
        lines.append(f"Cited {classic.get('citation_count', 0)} times")
        lines.append(classic["summary"])
        lines.append(classic["url"])
        lines.append("")

    return "\n".join(lines)


def _article_block(a: dict, extra_line: str = "") -> str:
    extra = f'<p style="margin:0 0 8px;color:#888;font-size:0.85em;">{extra_line}</p>' if extra_line else ""
    return f"""
        <div style="margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #ddd;">
          <h3 style="margin:0 0 4px;"><a href="{a['url']}">{a['title']}</a></h3>
          <p style="margin:0 0 8px;color:#555;font-size:0.9em;">{_authors_line(a)}</p>
          {extra}
          <p style="margin:0;">{a['summary']}</p>
        </div>"""


def _build_html(articles: list, must_read: dict | None, classic: dict | None) -> str:
    sections = []

    if must_read:
        sections.append(f"""
        <h3 style="margin:0 0 8px;">Must-read this week</h3>
        <div style="border:2px solid #c0392b;border-radius:8px;padding:12px 16px;margin-bottom:28px;">
          {_article_block(must_read)}
        </div>""")

    others = [a for a in articles if not must_read or a["pmid"] != must_read["pmid"]]
    if others:
        sections.append('<h3 style="margin:0 0 8px;">Also new this week</h3>')
        sections.extend(_article_block(a) for a in others)

    if classic:
        cite_line = f"Cited {classic.get('citation_count', 0)} times"
        sections.append(f"""
        <h3 style="margin:28px 0 8px;">Classic worth revisiting</h3>
        <div style="border:2px solid #2980b9;border-radius:8px;padding:12px 16px;">
          {_article_block(classic, extra_line=cite_line)}
        </div>""")

    return f"""
    <html><body style="font-family:sans-serif;max-width:640px;margin:auto;">
      <h2>Music &amp; Neuroplasticity Digest &mdash; {date.today().isoformat()}</h2>
      {''.join(sections)}
    </body></html>"""


def send_digest(articles: list, must_read: dict | None = None, classic: dict | None = None) -> None:
    """Send the digest email. No-ops (returns) if there's nothing to send."""
    if not articles and not classic:
        return

    if not (config.EMAIL_ADDRESS and config.EMAIL_APP_PASSWORD and config.EMAIL_TO):
        raise RuntimeError("EMAIL_ADDRESS / EMAIL_APP_PASSWORD / EMAIL_TO must be set in .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Music & Neuroplasticity Digest — {date.today().isoformat()} ({len(articles)} new)"
    msg["From"] = config.EMAIL_ADDRESS
    msg["To"] = config.EMAIL_TO
    msg.attach(MIMEText(_build_plain_text(articles, must_read, classic), "plain"))
    msg.attach(MIMEText(_build_html(articles, must_read, classic), "html"))

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        server.sendmail(config.EMAIL_ADDRESS, [config.EMAIL_TO], msg.as_string())
