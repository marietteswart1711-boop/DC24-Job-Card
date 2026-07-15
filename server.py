#!/usr/bin/env python3
"""
Job Card server — pure Python standard library, no pip installs needed.

Serves the job card form (public/index.html) and, when a technician submits
a completed job card, composes an email (with the client's signature and any
photos attached) and sends it via SMTP using the credentials in config.json
(local use) or environment variables (hosted use — see README.md).

Job numbers are entered manually by the technician on the form — this server
does not assign or track a job number sequence.

Emailed job cards include the DC24 letterhead header and footer (logo/contact
banner + SnapScan/review QR codes) inlined from assets/dc24_header.png and
assets/dc24_footer.png — see the assets/ folder next to this file.

Setup (local):
    1. cp config.example.json config.json
    2. Edit config.json with your real SMTP details (see README.md)
    3. python3 server.py
    4. On a technician's phone (same wifi), open the "Network:" URL printed below

Setup (hosted, e.g. Render/Railway):
    Skip config.json entirely and set the same keys as environment variables
    in your hosting platform's dashboard instead — see the "Going live"
    section of README.md. Never commit config.json or share it — it contains
    your email password.
"""

import http.server
import json
import os
import re
import smtplib
import ssl
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.utils import formatdate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
HEADER_IMAGE_PATH = os.path.join(ASSETS_DIR, "dc24_header.png")
FOOTER_IMAGE_PATH = os.path.join(ASSETS_DIR, "dc24_footer.png")


# Every key config.json can hold can also be set as an environment variable
# instead — environment variables always win if both are present. This is the
# recommended approach when hosting on a platform like Render or Railway: you
# set these in the platform's dashboard and never need to commit config.json
# (or any secret) to your repo at all.
ENV_KEYS = {
    "SMTP_HOST": str, "SMTP_PORT": int, "SMTP_USE_TLS": bool, "SMTP_USE_SSL": bool,
    "SMTP_SKIP_AUTH": bool, "SMTP_USER": str, "SMTP_PASSWORD": str, "EMAIL_FROM": str,
    "EMAIL_TO": str, "COMPANY_NAME": str, "SERVER_PORT": int,
    "GOOGLE_REVIEW_URL": str,
}


def _cast_env(key, raw, kind):
    if kind is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if kind is int:
        try:
            return int(raw)
        except ValueError:
            raise ValueError(
                f"Environment variable {key} must be a whole number (e.g. 587), "
                f"but its current value is {raw!r}. Check the Environment tab in "
                f"your hosting platform's dashboard and fix that variable."
            )
    return raw


def load_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)

    for key, kind in ENV_KEYS.items():
        raw = os.environ.get(key)
        if raw is not None and raw != "":
            cfg[key] = _cast_env(key, raw, kind)

    if not cfg:
        print("=" * 70)
        print("No config.json found and no config environment variables set.")
        print("Run:  cp config.example.json config.json")
        print("...then edit config.json with your real SMTP details, OR set")
        print("the same keys as environment variables — see README.md.")
        print("The web form will still load, but sending email will fail")
        print("until it's configured one of these two ways.")
        print("=" * 70)
        return None
    return cfg


def data_url_to_bytes(data_url):
    """Turns 'data:image/png;base64,AAAA...' into (mime_subtype, raw_bytes)."""
    m = re.match(r"^data:image/(\w+);base64,(.*)$", data_url, re.S)
    if not m:
        return "png", b""
    subtype, b64 = m.group(1), m.group(2)
    if subtype == "jpg":
        subtype = "jpeg"
    return subtype, base64.b64decode(b64)


def parse_data_url(data_url):
    """
    Turns 'data:<mime type>;base64,<data>' into (mime_type, raw_bytes) for any
    mime type — unlike data_url_to_bytes above, which only understands
    data:image/... URLs. Used for the disposal certificate PDF upload.
    """
    m = re.match(r"^data:([\w./+-]+);base64,(.*)$", data_url, re.S)
    if not m:
        return "application/octet-stream", b""
    return m.group(1), base64.b64decode(m.group(2))


def row(label, value):
    if not value:
        return ""
    return (f"<tr><td style='padding:4px 8px;font-weight:bold;vertical-align:top;'>{escape(label)}</td>"
            f"<td style='padding:4px 8px;'>{escape(value)}</td></tr>")


def checklist_line(label, items):
    if not items:
        return ""
    return (f"<p style='margin:4px 0;'><strong>{escape(label)}:</strong> "
            f"{escape(', '.join(items))}</p>")


POOR_RATING_ALERT_RECIPIENT = "mariette@leakfind.co.za"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def build_job_card_html(cfg, job):
    materials = job.get("materials") or []
    mat_rows = "".join(
        f"<tr><td style='padding:4px 8px;border:1px solid #ddd;'>{escape(m.get('name',''))}</td>"
        f"<td style='padding:4px 8px;border:1px solid #ddd;'>{escape(m.get('qty',''))}</td></tr>"
        for m in materials
    ) or "<tr><td colspan='2' style='padding:4px 8px;border:1px solid #ddd;color:#888;'>None recorded</td></tr>"

    c = job.get("consumables") or {}
    consumable_bits = []
    if c.get("degreaser"): consumable_bits.append(f"Degreaser ({c.get('degreaserL','') or '?'} L)")
    if c.get("disinfectant"): consumable_bits.append(f"Disinfectant ({c.get('disinfectantL','') or '?'} L)")
    if c.get("acid"): consumable_bits.append(f"Acid ({c.get('acidL','') or '?'} L)")
    if c.get("microbes"): consumable_bits.append(f"Microbes ({c.get('microbesL','') or '?'} L)")
    if c.get("beads"): consumable_bits.append("Beads")

    f = job.get("fattraps") or {}
    fattrap_bits = []
    if f.get("l50"): fattrap_bits.append(f"50L x {f.get('l50Qty','') or '?'}")
    if f.get("l80"): fattrap_bits.append(f"80L x {f.get('l80Qty','') or '?'}")
    if f.get("l100"): fattrap_bits.append(f"100L x {f.get('l100Qty','') or '?'}")

    ext_tank = list(job.get("extTank") or [])
    if job.get("extTankSpecify"):
        ext_tank.append(f"Specify: {job['extTankSpecify']}")

    waste_stream = list(job.get("wasteStream") or [])
    if job.get("wasteStreamOther"):
        waste_stream.append(f"Other: {job['wasteStreamOther']}")

    time_bits = []
    if job.get("timeIn1") or job.get("timeOut1"):
        time_bits.append(f"Visit 1: {job.get('timeIn1','?')} - {job.get('timeOut1','?')}")
    if job.get("timeIn2") or job.get("timeOut2"):
        time_bits.append(f"Visit 2: {job.get('timeIn2','?')} - {job.get('timeOut2','?')}")

    html = f"""
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:640px;">
      <img src="cid:dc24_header" alt="{escape(cfg.get('COMPANY_NAME','DC24'))}" style="width:100%;max-width:640px;display:block;margin-bottom:14px;">

      <h2 style="color:#1a1a1a;margin-bottom:4px;">{escape(cfg.get('COMPANY_NAME','Job Card'))} — Job Card #{escape(job.get('jobNo',''))}</h2>
      <p style="color:#888;margin-top:0;">Submitted {escape(job.get('submittedAt',''))}</p>
      {f"<p style='margin:2px 0 4px;'><strong>Vehicle:</strong> {escape(job.get('vehicle'))}</p>" if job.get('vehicle') else ""}
      {f"<p style='margin:2px 0 12px;'><strong>Dumping Site:</strong> {escape(job.get('dumpSite'))}</p>" if job.get('dumpSite') else ""}

      <h3 style="margin-bottom:4px;">Customer Details</h3>
      <table style="border-collapse:collapse;margin-bottom:16px;">
        {row('Name', job.get('name'))}
        {row('Site', job.get('site'))}
        {row('Planon Number', job.get('planon'))}
        {row('Address', job.get('address'))}
        {row('Contact Person', job.get('contact'))}
        {row('Telephone', job.get('tel'))}
        {row('Email', job.get('email'))}
        {row('Billing Information', job.get('billing'))}
      </table>

      <h3 style="margin-bottom:4px;">Job Description</h3>
      <p style="white-space:pre-wrap;margin-top:4px;">{escape(job.get('details',''))}</p>

      {checklist_line('Job Type', job.get('jobType'))}
      {checklist_line('Drain Type', job.get('drainType'))}
      {checklist_line('Liquid Waste', job.get('liquidWaste'))}
      {checklist_line('Pump Out Internal Fattraps', fattrap_bits)}
      {checklist_line('Pump Out External Fat Trap / Tank', ext_tank)}
      {checklist_line('Consumables', consumable_bits)}
      {checklist_line('Waste Stream', waste_stream)}
      {checklist_line('Waste Type', job.get('wasteType'))}
      {checklist_line('Quote Requirements', [job['quoteReq']] if job.get('quoteReq') else [])}

      <h3 style="margin-bottom:4px;margin-top:16px;">Materials / Parts Used</h3>
      <table style="border-collapse:collapse;margin-bottom:16px;">
        <tr><th style="padding:4px 8px;border:1px solid #ddd;background:#f2f2f2;text-align:left;">Material</th>
            <th style="padding:4px 8px;border:1px solid #ddd;background:#f2f2f2;text-align:left;">Qty</th></tr>
        {mat_rows}
      </table>

      <h3 style="margin-bottom:4px;">Sign-Off</h3>
      <p style="margin:4px 0;">Customer: <strong>{escape(job.get('customerName',''))}</strong> (signature attached)</p>
      <p style="margin:4px 0;">Driver: <strong>{escape(job.get('driverName',''))}</strong> (signature attached)</p>

      <h3 style="margin-bottom:4px;">Safe Disposal Certificate</h3>
      <p style="margin:4px 0;">{"⚠️ <strong>Linked to a disposal site certificate</strong> — technician will upload the certificate separately after dumping the load." if job.get('needsDisposalCert') else "Not linked to a disposal site certificate."}</p>

      {f"<h3 style='margin-bottom:4px;'>Comments</h3><p style='white-space:pre-wrap;'>{escape(job.get('comments'))}</p>" if job.get('comments') else ""}

      <table style="border-collapse:collapse;margin-top:8px;">
        {row('Service Rating', job.get('rating'))}
        {row('Date', job.get('date'))}
        {row('Time', ' | '.join(time_bits))}
      </table>

      <p style="margin-top:16px;color:#888;font-size:12px;">
        Before/after photos and all signatures are attached to this email.
      </p>

      <img src="cid:dc24_footer" alt="" style="width:100%;max-width:640px;display:block;margin-top:14px;">
    </div>
    """
    return html


def attach_header_footer(msg):
    """
    Inlines the DC24 letterhead header and footer (logo/contact banner at the
    top, SnapScan/review QR codes and contact details at the bottom) into the
    job card email using Content-ID references, so they render as part of the
    email body itself rather than as separate file attachments to open. If
    the image files aren't present (e.g. someone deploys without copying the
    assets/ folder across), this quietly skips them instead of failing the
    whole email — the job card still sends, just without the letterhead.
    """
    for cid, path in (("dc24_header", HEADER_IMAGE_PATH), ("dc24_footer", FOOTER_IMAGE_PATH)):
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            raw = f.read()
        img = MIMEImage(raw, _subtype="png")
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
        msg.attach(img)


def attach_job_card_files(msg, job):
    # Signatures
    for label, key in [("signature_customer", "customerSignature"), ("signature_driver", "driverSignature")]:
        sig = job.get(key)
        if sig:
            subtype, raw = data_url_to_bytes(sig)
            if raw:
                img = MIMEImage(raw, _subtype=subtype)
                img.add_header("Content-Disposition", "attachment", filename=f"{label}.{subtype}")
                msg.attach(img)

    # Before/after photos
    for group, key in [("before", "photosBefore"), ("after", "photosAfter")]:
        for i, photo in enumerate(job.get(key) or []):
            subtype, raw = data_url_to_bytes(photo)
            if raw:
                img = MIMEImage(raw, _subtype=subtype)
                img.add_header("Content-Disposition", "attachment", filename=f"photo_{group}_{i+1}.{subtype}")
                msg.attach(img)


def build_email(cfg, job):
    """The internal office copy — unchanged rating-based subject/recipient logic."""
    msg = MIMEMultipart()
    is_poor = (job.get("rating") or "").strip().lower() == "poor"

    if is_poor:
        msg["Subject"] = "Poor rating DC24"
        recipients = [cfg["EMAIL_TO"], POOR_RATING_ALERT_RECIPIENT]
    else:
        msg["Subject"] = f"Job Card #{job.get('jobNo','')} - {job.get('name','')} - {job.get('date','')}"
        recipients = [cfg["EMAIL_TO"]]

    msg["From"] = cfg["EMAIL_FROM"]
    msg["To"] = ", ".join(recipients)
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(build_job_card_html(cfg, job), "html"))
    attach_header_footer(msg)
    attach_job_card_files(msg, job)
    return msg


def build_client_copy_email(cfg, job):
    """
    A copy of the job card sent straight to the client's own email address, so
    they have a record of it. Always uses the normal subject line (never the
    internal 'Poor rating DC24' alert subject/recipient) since this is the
    client's own copy of their job card, not an internal notification.
    """
    msg = MIMEMultipart()
    msg["Subject"] = f"Your Job Card #{job.get('jobNo','')} - {cfg.get('COMPANY_NAME','')} - {job.get('date','')}"
    msg["From"] = cfg["EMAIL_FROM"]
    msg["To"] = job.get("email", "").strip()
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(build_job_card_html(cfg, job), "html"))
    attach_header_footer(msg)
    attach_job_card_files(msg, job)
    return msg


def client_email_valid(job):
    email = (job.get("email") or "").strip()
    return bool(email) and bool(EMAIL_RE.match(email))


def build_disposal_cert_email(cfg, cert):
    msg = MIMEMultipart()
    msg["Subject"] = f"Safe Disposal Certificate — Job Card #{cert.get('jobNo','')} - {cert.get('name','')}"
    msg["From"] = cfg["EMAIL_FROM"]
    msg["To"] = cfg["EMAIL_TO"]
    msg["Date"] = formatdate(localtime=True)

    html = f"""
    <div style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:640px;">
      <h2 style="color:#1a1a1a;margin-bottom:4px;">{escape(cfg.get('COMPANY_NAME','Job Card'))} — Safe Disposal Certificate for Job Card #{escape(cert.get('jobNo',''))}</h2>
      <p style="color:#888;margin-top:0;">This completes the disposal certificate follow-up for job card #{escape(cert.get('jobNo',''))}.</p>
      <table style="border-collapse:collapse;margin-bottom:16px;">
        {row('Job No', cert.get('jobNo'))}
        {row('Client', cert.get('name'))}
        {row('Technician', cert.get('driverName'))}
        {row('Job Date', cert.get('date'))}
        {row('Disposal Site', cert.get('disposalName'))}
      </table>
      <p style="margin-top:16px;color:#888;font-size:12px;">
        The disposal site signature and a PDF of the physical certificate handed to the
        technician are attached to this email.
      </p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))

    sig = cert.get("disposalSignature")
    if sig:
        subtype, raw = data_url_to_bytes(sig)
        if raw:
            img = MIMEImage(raw, _subtype=subtype)
            img.add_header("Content-Disposition", "attachment", filename=f"signature_disposal.{subtype}")
            msg.attach(img)

    # The certificate upload is a PDF (not a photo) — attached as a proper PDF
    # part rather than an image. Kept tolerant of an old image data URL too,
    # in case an in-flight submission from before this change still has one.
    cert_file = cert.get("certificatePhoto")
    if cert_file:
        mime, raw = parse_data_url(cert_file)
        if raw:
            if mime == "application/pdf":
                part = MIMEApplication(raw, _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename="disposal_certificate.pdf")
                msg.attach(part)
            elif mime.startswith("image/"):
                subtype = mime.split("/", 1)[1]
                img = MIMEImage(raw, _subtype=subtype)
                img.add_header("Content-Disposition", "attachment", filename=f"disposal_certificate.{subtype}")
                msg.attach(img)

    return msg


def escape(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def send_smtp_message(cfg, msg):
    context = ssl.create_default_context()
    use_tls = cfg.get("SMTP_USE_TLS", True)
    use_ssl = cfg.get("SMTP_USE_SSL", False)  # implicit TLS, e.g. port 465
    skip_auth = cfg.get("SMTP_SKIP_AUTH", False)  # for local test relays with no login

    smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    kwargs = {"timeout": 20}
    if use_ssl:
        kwargs["context"] = context

    with smtp_cls(cfg["SMTP_HOST"], cfg["SMTP_PORT"], **kwargs) as server:
        server.ehlo()
        if use_tls and not use_ssl:
            server.starttls(context=context)
            server.ehlo()
        if not skip_auth:
            server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.send_message(msg)


def send_email(cfg, job):
    send_smtp_message(cfg, build_email(cfg, job))


def send_client_copy_email(cfg, job):
    send_smtp_message(cfg, build_client_copy_email(cfg, job))


def send_disposal_cert_email(cfg, cert):
    send_smtp_message(cfg, build_disposal_cert_email(cfg, cert))


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            path = os.path.join(PUBLIC_DIR, "index.html")
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/public-config":
            cfg = load_config() or {}
            return self._send_json(200, {
                "googleReviewUrl": cfg.get("GOOGLE_REVIEW_URL", ""),
                "companyName": cfg.get("COMPANY_NAME", "")
            })

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/submit-jobcard":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                job = json.loads(raw)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "bad json"})

            cfg = load_config()
            if cfg is None:
                return self._send_json(500, {"error": "server not configured — see config.json"})

            try:
                send_email(cfg, job)
                is_poor = (job.get("rating") or "").strip().lower() == "poor"
                to_line = f"{cfg['EMAIL_TO']}, {POOR_RATING_ALERT_RECIPIENT}" if is_poor else cfg['EMAIL_TO']
                print(f"Sent job card #{job.get('jobNo')} for {job.get('name')} to {to_line}"
                      f"{' [POOR RATING ALERT]' if is_poor else ''}")
            except Exception as e:
                print(f"FAILED to send job card #{job.get('jobNo')}: {e}")
                return self._send_json(500, {"error": str(e)})

            # Client copy is best-effort — a bad/missing email or a hiccup here
            # shouldn't undo the fact that the office copy above already sent.
            client_copy_sent = False
            if client_email_valid(job):
                try:
                    send_client_copy_email(cfg, job)
                    client_copy_sent = True
                    print(f"Sent client copy of job card #{job.get('jobNo')} to {job.get('email')}")
                except Exception as e:
                    print(f"FAILED to send client copy of job card #{job.get('jobNo')} to {job.get('email')}: {e}")

            return self._send_json(200, {"ok": True, "clientCopySent": client_copy_sent})

        if self.path == "/api/submit-disposal-cert":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                cert = json.loads(raw)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "bad json"})

            cfg = load_config()
            if cfg is None:
                return self._send_json(500, {"error": "server not configured — see config.json"})

            try:
                send_disposal_cert_email(cfg, cert)
                print(f"Sent disposal certificate for job card #{cert.get('jobNo')} to {cfg['EMAIL_TO']}")
                return self._send_json(200, {"ok": True})
            except Exception as e:
                print(f"FAILED to send disposal certificate for job card #{cert.get('jobNo')}: {e}")
                return self._send_json(500, {"error": str(e)})

        self.send_response(404)
        self.end_headers()


def local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    cfg = load_config()
    # Render/Railway/Heroku-style platforms inject a PORT env var and expect
    # the app to bind to it — that takes priority over SERVER_PORT, which is
    # still used for plain local runs.
    port = int(os.environ.get("PORT") or (cfg or {}).get("SERVER_PORT", 8000))
    print("Job Card server starting...")
    print(f"  Local:   http://localhost:{port}")
    print(f"  Network: http://{local_ip()}:{port}  (open this on technicians' phones, same wifi)")
    if cfg is None:
        print("  ⚠️  Running WITHOUT email config — form will load but sending will fail.")
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
