"""Côté email : décodage des messages reçus (IMAP) et envoi du devis (SMTP)."""

import base64
import imaplib
import io
import smtplib
import socket
import ssl
import time
from email.encoders import encode_base64
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import log

BLACKLIST = ["mailer-daemon", "no-reply", "noreply", "notification", "postmaster", "daemon", "do-not-reply", "newsletter"]
MAX_PHOTOS = 3


def forcer_ipv4():
    """IPv6 instable sur certains hébergements (RPi) : forcer la résolution en IPv4."""
    orig = socket.getaddrinfo

    def ipv4_only(host, port, family=0, *args, **kwargs):
        return orig(host, port, socket.AF_INET, *args, **kwargs)

    socket.getaddrinfo = ipv4_only


# ---------- lecture ----------


def decoder_sujet(subject) -> str:
    if not subject:
        return "Demande de devis"
    decoded = ""
    for part, enc in decode_header(subject):
        decoded += part.decode(enc or "utf-8", errors="replace") if isinstance(part, bytes) else part
    return decoded.strip()


def expediteur(msg) -> tuple[str, str]:
    """(adresse en minuscules, nom affiché) à partir de l'en-tête From."""
    from_hdr = msg.get("From", "") or ""
    addr = from_hdr.split("<")[-1].rstrip(">").strip().lower()
    raw_name = from_hdr.split("<")[0].strip().strip('"')
    name = decoder_sujet(raw_name) if raw_name and "<" in from_hdr else "Client"
    return addr, name


def extraire_corps(msg) -> str:
    """Texte brut du corps (première partie text/plain), tronqué à 1000 caractères."""
    try:
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace").strip()[:1000]
    except Exception:
        pass
    return ""


def compresser_photo(payload: bytes, max_dim=800, quality=70) -> bytes:
    """Réduit la photo (JPEG) pour l'API et la pièce jointe ; renvoie l'original si Pillow est absent."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(payload))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((max_dim, max_dim))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception:
        return payload


def extraire_photos(msg) -> list[str]:
    """Photos jointes, compressées puis encodées en base64 (3 max)."""
    photos = []
    for part in msg.walk():
        if part.get_content_maintype() == "image" and len(photos) < MAX_PHOTOS:
            payload = part.get_payload(decode=True)
            if payload:
                comp = compresser_photo(payload)
                photos.append(base64.b64encode(comp).decode())
                log(f"  [PHOTO] {len(payload) // 1024} Ko -> {len(comp) // 1024} Ko")
    return photos


def est_ignore(from_addr: str, sujet: str) -> bool:
    """Vrai pour les expéditeurs automatiques, nos propres envois, ou un sujet sans « devis »."""
    s = sujet.lower()
    return any(b in from_addr for b in BLACKLIST) or "votre devis" in s or "devis" not in s


# ---------- IMAP ----------


def connecter_imap(cfg):
    mail = imaplib.IMAP4_SSL(cfg.imap_host, timeout=15)
    mail.login(cfg.gmail_address, cfg.gmail_app_password)
    mail.select("INBOX")
    return mail


def uid_max(mail) -> int:
    _, msgs = mail.uid("search", None, "ALL")
    uids = [int(u) for u in msgs[0].split()] or [0]
    return max(uids)


def nouveaux_uids(mail, last_uid: int) -> list[int]:
    _, msgs = mail.uid("search", None, f"UID {last_uid + 1}:*")
    return sorted(int(u) for u in msgs[0].split() if int(u) > last_uid)


def lire_message(mail, uid: int):
    from email import message_from_bytes

    _, data = mail.uid("fetch", str(uid), "(RFC822)")
    if not data or not data[0]:
        return None
    return message_from_bytes(data[0][1])


# ---------- SMTP ----------


def composer_message(cfg, client_email, client_name, num, path, sujet) -> MIMEMultipart:
    ent = cfg.entreprise
    msg = MIMEMultipart()
    msg["From"] = f"{ent['nom']} <{cfg.from_email}>"
    msg["Reply-To"] = cfg.from_email
    msg["To"] = client_email
    msg["Subject"] = f"Votre devis N° {num} — {ent['nom']}"
    body = f"""Bonjour {client_name},

Nous vous remercions pour votre demande concernant : {sujet}

Nos equipes ont analyse votre demande et les photos transmises. Vous trouverez ci-joint votre devis N° {num}, valable 30 jours.

N'hesitez pas a nous contacter pour toute question ou ajustement.

Bien cordialement,

{ent["nom"]}
{ent["email"]}
{ent["tel"]}"""
    msg.attach(MIMEText(body, "plain", "utf-8"))
    ext = "pdf" if path.endswith(".pdf") else "html"
    mtype = ("application", "pdf") if ext == "pdf" else ("text", "html")
    with open(path, "rb") as att:
        part = MIMEBase(*mtype)
        part.set_payload(att.read())
    encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="Devis_{num}.{ext}"')
    msg.attach(part)
    return msg


def envoyer(cfg, client_email, client_name, num, path, sujet, *, smtp_cls=smtplib.SMTP, tentatives=3, pause=5) -> bool:
    try:
        msg = composer_message(cfg, client_email, client_name, num, path, sujet)
    except Exception as e:
        log(f"  [X] Erreur email: {e}")
        return False
    ctx = ssl.create_default_context()
    for tentative in range(1, tentatives + 1):
        try:
            with smtp_cls(cfg.smtp_host, cfg.smtp_port, timeout=cfg.smtp_timeout) as server:
                server.starttls(context=ctx)
                server.login(cfg.gmail_address, cfg.gmail_app_password)
                server.send_message(msg)
            log(f"  [OK] Devis {num} envoye a {client_email} (tentative {tentative})")
            return True
        except Exception as e:
            log(f"  [!] Tentative {tentative}/{tentatives}: {e}")
            time.sleep(pause)
    log(f"  [X] Echec envoi apres {tentatives} tentatives")
    return False
