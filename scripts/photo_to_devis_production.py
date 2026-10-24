#!/usr/bin/env python3
"""PHOTO -> DEVIS v3 - ANALYSE INTELLIGENTE PAR CLAUDE VISION
La/les photos sont analysees par IA, le devis est chiffre selon un bareme."""
import imaplib, smtplib, ssl, os, sys, time, uuid, base64, json, urllib.request
import socket as _socket
from email import message_from_bytes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from email.header import decode_header
from datetime import datetime, timedelta

# FORCER IPv4 (IPv6 instable sur ce RPi)
_orig_getaddrinfo = _socket.getaddrinfo
def _ipv4_only(host, port, family=0, *args, **kwargs):
    return _orig_getaddrinfo(host, port, _socket.AF_INET, *args, **kwargs)
_socket.getaddrinfo = _ipv4_only

def log(*args):
    print(datetime.now().strftime("%H:%M:%S"), *args)

# Identifiants : variables d'environnement uniquement (cf. .env.example)
EMAIL = os.getenv('GMAIL_ADDRESS')
PASSWD = os.getenv('GMAIL_APP_PASSWORD')
if not EMAIL or not PASSWD:
    sys.exit("GMAIL_ADDRESS / GMAIL_APP_PASSWORD manquants dans l'environnement (.env)")
# Adresse d'expédition affichée (alias « Envoyer en tant que » déclaré dans Gmail) ; défaut : le compte Gmail
FROM_EMAIL = os.getenv('FROM_EMAIL', EMAIL)

# Charger la cle API Anthropic depuis aria/.env
ANTHROPIC_KEY = os.getenv('ANTHROPIC_API_KEY', '')
if not ANTHROPIC_KEY:
    try:
        with open(os.getenv('ANTHROPIC_ENV_FILE', os.path.expanduser('~/aria/.env'))) as f:
            for line in f:
                if line.startswith('ANTHROPIC_API_KEY='):
                    ANTHROPIC_KEY = line.split('=', 1)[1].strip()
                    break
    except Exception:
        pass

ENTREPRISE = {
    "nom": os.getenv('ENTREPRISE_NOM', 'Jardin Services Démo'),
    "legal": "SARL Jardin Services (démonstration)",
    "slogan": "Entretien de jardins & espaces verts",
    "email": os.getenv('ENTREPRISE_EMAIL', 'contact@jardin-services-demo.fr'),
    "site": "jardin-services-demo.fr",
    "tel": os.getenv('ENTREPRISE_TEL', '01 23 45 67 89'),
    "adresse": "Zone de démonstration - exemple non contractuel",
    "siret": os.getenv('ENTREPRISE_SIRET', 'SIRET DÉMO - non contractuel'),
    "tva_mention": "Exemple de démonstration - devis non contractuel",
    "logo": "/home/standev/waouh-portfolio/karakuri-content/assets/brand/logo.png",
}

# ============ BAREME DE PRIX GENERIQUE ============
BAREME = {
    "deplacement_forfait": 50.0,
    "main_oeuvre_heure": 45.0,
    "taille_haie_ml": 8.0,
    "tonte_pelouse_m2": 0.45,
    "debroussaillage_m2": 0.35,
    "elagage_petit_arbre": 90.0,
    "elagage_grand_arbre": 220.0,
    "abattage_arbre": 350.0,
    "evacuation_dechets_m3": 45.0,
    "nettoyage_terrasse_m2": 4.0,
    "peinture_mur_m2": 25.0,
    "pose_cloture_ml": 35.0,
    "petite_maconnerie_heure": 55.0,
    "nettoyage_general_forfait": 90.0,
}

PROMPT_ANALYSE = """Tu es un expert en chiffrage de travaux (paysagisme, jardin, batiment, services exterieurs) pour une petite entreprise francaise.

Analyse la ou les photos envoyees par le client ainsi que sa demande, puis etablis un devis realiste.

DEMANDE DU CLIENT:
Sujet: {sujet}
Message: {corps}

BAREME DE PRIX A UTILISER (EUR HT):
{bareme}

INSTRUCTIONS:
1. Decris precisement ce que tu VOIS sur la/les photos (type de vegetation/surface/etat, dimensions estimees)
2. Estime les quantites de facon realiste A PARTIR DE LA PHOTO (longueur de haie en metres, surface en m2, nombre d'arbres, volume de dechets...)
3. Etablis les lignes du devis en utilisant le bareme. Ajoute toujours le deplacement. Ajoute l'evacuation des dechets si des dechets seront produits.
4. Si la photo ne correspond pas a des travaux identifiables, fais une estimation prudente basee sur la demande texte.

Reponds UNIQUEMENT avec un JSON valide, sans markdown, sans backticks:
{{"analyse": "description detaillee de ce que tu vois et du travail necessaire (2-4 phrases, en francais)",
"lignes": [{{"designation": "libelle precis avec dimensions estimees", "qte": nombre, "unite": "ml|m2|m3|heure|forfait|unite", "pu": prix_unitaire_ht}}],
"duree_estimee": "duree du chantier (ex: une demi-journee)"}}"""

def analyser_avec_claude(photos_b64, sujet, corps):
    """Envoie photos + demande a Claude Vision, retourne dict analyse+lignes"""
    if not ANTHROPIC_KEY:
        log("  [!] Pas de cle API - fallback generique")
        return None
    try:
        content = []
        for pb64 in photos_b64[:3]:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": pb64}})
        bareme_txt = "\n".join(f"- {k.replace('_',' ')}: {v} EUR" for k, v in BAREME.items())
        content.append({"type": "text", "text": PROMPT_ANALYSE.format(sujet=sujet, corps=corps[:500], bareme=bareme_txt)})
        
        payload = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": content}]
        }).encode()
        
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01"
            })
        
        for tentative in range(2):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                texte = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
                texte = texte.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                result = json.loads(texte)
                if result.get("lignes"):
                    log(f"  [IA] Analyse OK: {len(result['lignes'])} lignes")
                    return result
            except Exception as e:
                log(f"  [!] Tentative IA {tentative+1}: {e}")
                time.sleep(3)
        return None
    except Exception as e:
        log(f"  [!] Erreur analyse IA: {e}")
        return None

def compresser_photo(payload, max_dim=800, quality=70):
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(payload))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.thumbnail((max_dim, max_dim))
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        return buf.getvalue()
    except Exception:
        return payload

def decoder_sujet(subject):
    if not subject:
        return "Demande de devis"
    parts = decode_header(subject)
    decoded = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded += part.decode(enc or 'utf-8', errors='replace')
        else:
            decoded += part
    return decoded.strip()

def extraire_corps(msg):
    """Extrait le texte du corps de l'email"""
    try:
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    return payload.decode(charset, errors='replace').strip()[:1000]
    except Exception:
        pass
    return ""

def numero_devis():
    return f"{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"

def generer_devis(client_email, client_name, sujet, analyse_ia, photos_b64):
    num = numero_devis()
    date_devis = datetime.now().strftime('%d/%m/%Y')
    date_validite = (datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y')
    
    if analyse_ia and analyse_ia.get("lignes"):
        prestations = [(l["designation"], l["qte"], l["unite"], l["pu"]) for l in analyse_ia["lignes"]]
        analyse_txt = analyse_ia.get("analyse", "")
        duree = analyse_ia.get("duree_estimee", "")
    else:
        prestations = [
            ("Deplacement et evaluation sur site", 1, "forfait", BAREME["deplacement_forfait"]),
            ("Main d'oeuvre - travaux demandes", 4, "heure", BAREME["main_oeuvre_heure"]),
            ("Evacuation des dechets", 1, "m3", BAREME["evacuation_dechets_m3"]),
        ]
        analyse_txt = "Estimation standard etablie sur la base de votre demande. Une visite sur site permettra d'affiner ce chiffrage."
        duree = ""
    
    lignes_html = ""
    total_ht = 0
    for desc, qte, unite, pu in prestations:
        total_ligne = float(qte) * float(pu)
        total_ht += total_ligne
        lignes_html += f"""
            <tr>
                <td>{desc}</td>
                <td class="center">{qte:g}</td>
                <td class="center">{unite}</td>
                <td class="right">{pu:,.2f} €</td>
                <td class="right"><strong>{total_ligne:,.2f} €</strong></td>
            </tr>"""
    
    tva = 0.0
    total_ttc = total_ht  # franchise en base de TVA (micro-entreprise)
    
    duree_html = f'<p style="margin-top:8px"><strong>Durée estimée :</strong> {duree}</p>' if duree else ''
    
    photos_html = ""
    if photos_b64:
        imgs = "".join(f'<img src="data:image/jpeg;base64,{p}" alt="Photo {i+1}" />' for i, p in enumerate(photos_b64[:3]))
        photos_html = f"""
        <div class="photo-section">
            <h3>Photos transmises par le client</h3>
            <div class="photos">{imgs}</div>
        </div>"""
    
    import base64 as _b64
    try:
        with open(ENTREPRISE.get('logo',''), 'rb') as _lf:
            logo_b64 = _b64.b64encode(_lf.read()).decode()
    except Exception:
        logo_b64 = ''
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Devis {num}</title>
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:'Segoe UI',-apple-system,Helvetica,Arial,sans-serif; color:#1a2332; background:#f0f2f5; padding:20px; }}
    .page {{ max-width:800px; margin:0 auto; background:white; border-radius:12px; overflow:hidden; box-shadow:0 8px 30px rgba(0,0,0,0.08); }}
    .banner {{ background:linear-gradient(135deg,#1e3a5f 0%,#2d5f8a 100%); color:white; padding:36px 44px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; }}
    .banner .brand h1 {{ font-size:26px; letter-spacing:0.5px; }}
    .banner .brand p {{ opacity:0.85; font-size:14px; margin-top:4px; }}
    .banner .doc {{ text-align:right; }}
    .banner .doc .label {{ font-size:13px; text-transform:uppercase; letter-spacing:3px; opacity:0.8; }}
    .banner .doc .num {{ font-size:22px; font-weight:700; margin-top:4px; }}
    .meta {{ display:flex; justify-content:space-between; flex-wrap:wrap; gap:20px; padding:32px 44px; border-bottom:1px solid #e8ecf1; }}
    .meta .block {{ min-width:200px; }}
    .meta .block h4 {{ font-size:11px; text-transform:uppercase; letter-spacing:2px; color:#8494a8; margin-bottom:10px; }}
    .meta .block p {{ font-size:14px; line-height:1.7; }}
    .meta .block .name {{ font-weight:700; font-size:16px; color:#1e3a5f; }}
    .objet {{ padding:24px 44px; background:#f7f9fc; border-bottom:1px solid #e8ecf1; font-size:14px; }}
    .objet strong {{ color:#1e3a5f; }}
    .analyse {{ padding:24px 44px; background:#eef6ee; border-left:4px solid #4a9d5f; margin:24px 44px; border-radius:8px; font-size:14px; line-height:1.7; }}
    .analyse h3 {{ font-size:12px; text-transform:uppercase; letter-spacing:2px; color:#4a9d5f; margin-bottom:8px; }}
    .content {{ padding:10px 44px 32px; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    thead th {{ background:#1e3a5f; color:white; padding:13px 14px; text-align:left; font-size:12px; text-transform:uppercase; letter-spacing:1px; }}
    thead th.center, td.center {{ text-align:center; }}
    thead th.right, td.right {{ text-align:right; }}
    tbody td {{ padding:14px; border-bottom:1px solid #eef1f5; }}
    .totaux {{ margin-top:26px; margin-left:auto; width:320px; }}
    .totaux .row {{ display:flex; justify-content:space-between; padding:10px 14px; font-size:14px; }}
    .totaux .row.ttc {{ background:#1e3a5f; color:white; font-size:17px; font-weight:700; border-radius:8px; margin-top:6px; }}
    .photo-section {{ margin-top:34px; }}
    .photo-section h3 {{ font-size:13px; text-transform:uppercase; letter-spacing:2px; color:#8494a8; margin-bottom:12px; }}
    .photos {{ display:flex; gap:12px; flex-wrap:wrap; }}
    .photos img {{ max-width:230px; width:100%; border-radius:10px; border:1px solid #e8ecf1; box-shadow:0 4px 14px rgba(0,0,0,0.08); }}
    .conditions {{ padding:26px 44px; background:#f7f9fc; border-top:1px solid #e8ecf1; font-size:12px; color:#67788c; line-height:1.8; }}
    .conditions strong {{ color:#1e3a5f; }}
    .brand {{ display:flex; align-items:center; gap:16px; }}
    .brand-logo {{ width:64px; height:64px; border-radius:10px; object-fit:cover; }}
    .signature {{ padding:26px 44px 40px; display:flex; justify-content:space-between; flex-wrap:wrap; gap:20px; }}
    .signature .box {{ width:46%; min-width:240px; border:1px dashed #c3ccd6; border-radius:10px; padding:16px; font-size:12px; color:#8494a8; min-height:110px; }}
    .footer {{ text-align:center; padding:18px; font-size:11px; color:#a5b1bf; border-top:1px solid #eef1f5; }}
    @media print {{ body {{ background:white; padding:0; }} .page {{ box-shadow:none; border-radius:0; }} }}
</style>
</head>
<body>
<div class="page">
    <div class="banner">
        <div class="brand"><img src="data:image/png;base64,{logo_b64}" class="brand-logo"/><div><h1>{ENTREPRISE['nom']}</h1><p>{ENTREPRISE['slogan']}</p></div></div>
        <div class="doc"><div class="label">Devis</div><div class="num">N° {num}</div></div>
    </div>
    <div class="meta">
        <div class="block"><h4>Émetteur</h4><p class="name">{ENTREPRISE['nom']}</p><p>{ENTREPRISE['legal']}<br>{ENTREPRISE['adresse']}<br>{ENTREPRISE['email']} · {ENTREPRISE['tel']}<br>SIRET : {ENTREPRISE['siret']}<br><span style="font-size:11px;color:#6b7688">{ENTREPRISE['tva_mention']}</span></p></div>
        <div class="block"><h4>Client</h4><p class="name">{client_name}</p><p>{client_email}</p></div>
        <div class="block"><h4>Dates</h4><p>Émis le : <strong>{date_devis}</strong><br>Valable jusqu'au : <strong>{date_validite}</strong></p></div>
    </div>
    <div class="objet"><strong>Objet :</strong> {sujet}</div>
    <div class="analyse">
        <h3>🔍 Notre analyse de votre demande</h3>
        <p>{analyse_txt}</p>
        {duree_html}
    </div>
    <div class="content">
        <table>
            <thead><tr><th>Désignation</th><th class="center">Qté</th><th class="center">Unité</th><th class="right">Prix unit. HT</th><th class="right">Total HT</th></tr></thead>
            <tbody>{lignes_html}</tbody>
        </table>
        <div class="totaux">
            <div class="row ttc"><span>Total à régler</span><span>{total_ttc:,.2f} €</span></div>
            <div class="row"><span style="font-size:11px;color:#6b7688">{ENTREPRISE['tva_mention']}</span></div>
        </div>
        {photos_html}
    </div>
    <div class="conditions"><strong>Conditions :</strong> Devis valable 30 jours. Acompte de 30 % à la commande, solde à la fin des travaux. Règlement par virement ou chèque. Chiffrage établi sur la base des photos transmises — susceptible d'ajustement après visite sur site.</div>
    <div class="signature">
        <div class="box">Bon pour accord — Date et signature du client<br>(précédé de la mention « lu et approuvé »)</div>
        <div class="box">Cachet et signature de l'entreprise</div>
    </div>
    <div class="footer">{ENTREPRISE['nom']} — Devis {num} — Document généré le {date_devis}</div>
</div>
</body>
</html>"""
    
    os.makedirs('devis_outputs', exist_ok=True)
    path = f"devis_outputs/devis_{num}.html"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    try:
        pdf_path = generer_pdf(num, client_email, client_name, sujet, analyse_txt, duree, prestations, photos_b64, date_devis, date_validite)
        log(f"  [PDF] Genere: {pdf_path}")
        return num, pdf_path
    except Exception as e:
        log(f"  [!] PDF echec ({e}) - fallback HTML")
        return num, path


def generer_pdf(num, client_email, client_name, sujet, analyse_txt, duree, prestations, photos_b64, date_devis, date_validite):
    """Genere le devis en PDF avec fpdf2"""
    from fpdf import FPDF
    import io as _io

    BLEU = (30, 58, 95)
    BLEU2 = (45, 95, 138)
    GRIS = (132, 148, 168)
    VERT = (74, 157, 95)
    FONDVERT = (238, 246, 238)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    def txt(s):
        return str(s).encode("latin-1", "replace").decode("latin-1")

    # ===== BANNIERE =====
    pdf.set_fill_color(*BLEU)
    pdf.rect(0, 0, 210, 34, "F")
    # logo karakuri en haut à droite du bandeau
    try:
        _logo = ENTREPRISE.get("logo", "")
        if _logo and os.path.exists(_logo):
            pdf.image(_logo, x=176, y=4, w=26, h=26)
    except Exception:
        pass
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(12, 8)
    pdf.cell(120, 10, txt(ENTREPRISE["nom"]))
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(12, 19)
    pdf.cell(120, 6, txt(ENTREPRISE["slogan"]))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(120, 8)
    pdf.cell(52, 5, "DEVIS", align="R")
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_xy(120, 14)
    pdf.cell(52, 9, txt(f"N. {num}"), align="R")

    # ===== META (3 blocs) =====
    y = 42
    pdf.set_text_color(*GRIS)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(12, y); pdf.cell(60, 5, "EMETTEUR")
    pdf.set_xy(78, y); pdf.cell(60, 5, "CLIENT")
    pdf.set_xy(146, y); pdf.cell(52, 5, "DATES")
    pdf.set_text_color(30, 40, 55)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(12, y+6); pdf.cell(60, 5, txt(ENTREPRISE["nom"]))
    pdf.set_xy(78, y+6); pdf.cell(60, 5, txt(client_name[:32]))
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_xy(12, y+12); pdf.multi_cell(62, 4.2, txt(f"{ENTREPRISE['legal']}\n{ENTREPRISE['adresse']}\n{ENTREPRISE['email']} - {ENTREPRISE['tel']}\nSIRET : {ENTREPRISE['siret']}"))
    pdf.set_xy(78, y+12); pdf.multi_cell(62, 4.2, txt(client_email[:40]))
    pdf.set_xy(146, y+12); pdf.multi_cell(52, 4.2, txt(f"Emis le : {date_devis}\nValable jusqu'au : {date_validite}"))

    # ===== OBJET =====
    y = 70
    pdf.set_fill_color(247, 249, 252)
    pdf.rect(8, y, 194, 10, "F")
    pdf.set_xy(12, y+2)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*BLEU)
    pdf.cell(16, 6, "Objet :")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(30, 40, 55)
    pdf.cell(170, 6, txt(sujet[:95]))

    # ===== ANALYSE IA =====
    y = 86
    pdf.set_xy(12, y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*VERT)
    pdf.cell(0, 5, "NOTRE ANALYSE DE VOTRE DEMANDE")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 60, 45)
    corps_analyse = analyse_txt + (f"\nDuree estimee : {duree}" if duree else "")
    pdf.set_fill_color(*FONDVERT)
    pdf.set_xy(12, y+6)
    pdf.multi_cell(186, 4.8, txt(corps_analyse), fill=True)

    # ===== TABLEAU =====
    y = pdf.get_y() + 8
    pdf.set_xy(12, y)
    pdf.set_fill_color(*BLEU)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8.5)
    W = [92, 16, 20, 28, 30]
    for w, h_ in zip(W, ["DESIGNATION", "QTE", "UNITE", "PU HT", "TOTAL HT"]):
        pdf.cell(w, 8, h_, fill=True, align="C" if w < 90 else "L")
    pdf.ln()
    pdf.set_text_color(30, 40, 55)
    total_ht = 0
    for i, (desc, qte, unite, pu) in enumerate(prestations):
        tot = float(qte) * float(pu)
        total_ht += tot
        pdf.set_fill_color(252, 253, 255) if i % 2 else pdf.set_fill_color(245, 247, 250)
        pdf.set_x(12)
        pdf.set_font("Helvetica", "", 8.5)
        d = txt(desc)
        if len(d) > 62: d = d[:60] + "..."
        pdf.cell(W[0], 7.5, d, fill=True)
        pdf.cell(W[1], 7.5, f"{float(qte):g}", fill=True, align="C")
        pdf.cell(W[2], 7.5, txt(unite), fill=True, align="C")
        pdf.cell(W[3], 7.5, f"{float(pu):,.2f} EUR", fill=True, align="R")
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(W[4], 7.5, f"{tot:,.2f} EUR", fill=True, align="R")
        pdf.ln()

    # ===== TOTAUX (franchise de TVA micro-entreprise) =====
    ttc = total_ht
    y = pdf.get_y() + 6
    pdf.set_xy(120, y)
    pdf.set_fill_color(*BLEU)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(45, 9, " Total a regler", fill=True)
    pdf.cell(33, 9, f"{ttc:,.2f} EUR ", fill=True, align="R")
    pdf.set_text_color(120, 130, 145)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_xy(120, y+11)
    pdf.cell(78, 4, txt(ENTREPRISE['tva_mention']), align="R")
    pdf.set_text_color(30, 40, 55)
    pdf.set_y(y + 20)  # curseur SOUS le bloc totaux

    # ===== PHOTOS =====
    if photos_b64:
        y = pdf.get_y() + 16
        if y > 230:
            pdf.add_page(); y = 20
        pdf.set_xy(12, y)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*GRIS)
        pdf.cell(0, 5, "PHOTOS TRANSMISES PAR LE CLIENT")
        x = 12
        for pb64 in photos_b64[:3]:
            try:
                img = _io.BytesIO(base64.b64decode(pb64))
                pdf.image(img, x=x, y=y+7, w=58)
                x += 62
            except Exception:
                pass
        pdf.set_y(y + 7 + 46)

    # ===== CONDITIONS + SIGNATURES =====
    if pdf.get_y() > 235:
        pdf.add_page()
    y = pdf.get_y() + 6
    pdf.set_xy(12, y)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(103, 120, 140)
    pdf.multi_cell(186, 3.8, txt("Conditions : Devis valable 30 jours. Acompte de 30 % a la commande, solde a la fin des travaux. Reglement par virement ou cheque. Chiffrage etabli sur la base des photos transmises - susceptible d'ajustement apres visite sur site."))
    y = pdf.get_y() + 5
    pdf.set_draw_color(195, 204, 214)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.rect(12, y, 90, 26)
    pdf.set_xy(14, y+2)
    pdf.multi_cell(86, 3.6, txt("Bon pour accord - Date et signature du client\n(precede de la mention lu et approuve)"))
    pdf.rect(108, y, 90, 26)
    pdf.set_xy(110, y+2)
    pdf.multi_cell(86, 3.6, txt("Cachet et signature de l'entreprise"))

    out = f"devis_outputs/Devis_{num}.pdf"
    pdf.output(out)
    return out

def envoyer(client_email, client_name, num, path, sujet):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{ENTREPRISE['nom']} <{FROM_EMAIL}>"
        msg['Reply-To'] = FROM_EMAIL
        msg['To'] = client_email
        msg['Subject'] = f"Votre devis N° {num} — {ENTREPRISE['nom']}"
        body = f"""Bonjour {client_name},

Nous vous remercions pour votre demande concernant : {sujet}

Nos equipes ont analyse votre demande et les photos transmises. Vous trouverez ci-joint votre devis N° {num}, valable 30 jours.

N'hesitez pas a nous contacter pour toute question ou ajustement.

Bien cordialement,

{ENTREPRISE['nom']}
{ENTREPRISE['email']}
{ENTREPRISE['tel']}"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        ext = 'pdf' if path.endswith('.pdf') else 'html'
        mtype = ('application', 'pdf') if ext == 'pdf' else ('text', 'html')
        with open(path, 'rb') as att:
            part = MIMEBase(*mtype)
            part.set_payload(att.read())
            encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="Devis_{num}.{ext}"')
            msg.attach(part)
        ctx = ssl.create_default_context()
        for tentative in range(1, 4):
            try:
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=90) as server:
                    server.starttls(context=ctx)
                    server.login(EMAIL, PASSWD)
                    server.send_message(msg)
                log(f"  [OK] Devis {num} envoye a {client_email} (tentative {tentative})")
                return True
            except Exception as e:
                log(f"  [!] Tentative {tentative}/3: {e}")
                time.sleep(5)
        log(f"  [X] Echec envoi apres 3 tentatives")
        return False
    except Exception as e:
        log(f"  [X] Erreur email: {e}")
        return False

PROCESSED_FILE = ".processed_emails"

def charger_traites():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(l.strip() for l in f if l.strip())
    return set()

def marquer_traite(msg_id):
    with open(PROCESSED_FILE, 'a') as f:
        f.write(msg_id + "\n")

BLACKLIST = ['mailer-daemon', 'no-reply', 'noreply', 'notification', 'postmaster', 'daemon', 'do-not-reply', 'newsletter']

def poll():
    try:
        traites = charger_traites()
        mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=15)
        mail.login(EMAIL, PASSWD)
        mail.select('INBOX')

        # --- Tracking par UID: on ne regarde QUE les messages nouveaux ---
        last_uid = 0
        if os.path.exists('.last_uid'):
            try:
                last_uid = int(open('.last_uid').read().strip())
            except Exception:
                last_uid = 0

        if last_uid == 0:
            # Initialisation: reperer le plus grand UID actuel sans traiter le passe
            status, msgs = mail.uid('search', None, 'ALL')
            uids = [int(u) for u in msgs[0].split()] or [0]
            last_uid = max(uids)
            with open('.last_uid', 'w') as f:
                f.write(str(last_uid))
            log(f"[INIT] last_uid initialise a {last_uid}")
            mail.logout()
            return

        status, msgs = mail.uid('search', None, f'UID {last_uid+1}:*')
        uids = [int(u) for u in msgs[0].split() if int(u) > last_uid]
        if not uids:
            mail.logout()
            return

        log(f"[POLL] {len(uids)} nouveau(x) message(s)")
        max_seen = last_uid
        for uid in sorted(uids):
            try:
                max_seen = max(max_seen, uid)
                status, data = mail.uid('fetch', str(uid), '(RFC822)')
                if not data or not data[0]:
                    continue
                msg = message_from_bytes(data[0][1])
                msg_id = (msg.get('Message-ID') or f"uid-{uid}").strip()
                if msg_id in traites:
                    continue

                from_addr = msg['From'].split('<')[-1].rstrip('>').lower()
                raw_name = msg['From'].split('<')[0].strip().strip('"')
                from_name = decoder_sujet(raw_name) if raw_name else "Client"
                sujet = decoder_sujet(msg.get('Subject', 'Demande de devis'))

                if any(b in from_addr for b in BLACKLIST) or 'votre devis' in sujet.lower() or 'devis' not in sujet.lower():
                    marquer_traite(msg_id); traites.add(msg_id)
                    continue

                log(f"  [MAIL] De {from_name}: {sujet}")
                corps = extraire_corps(msg)

                photos_b64 = []
                for part in msg.walk():
                    if part.get_content_maintype() == 'image' and len(photos_b64) < 3:
                        payload = part.get_payload(decode=True)
                        if payload:
                            comp = compresser_photo(payload)
                            photos_b64.append(base64.b64encode(comp).decode())
                            log(f"  [PHOTO] {len(payload)//1024} Ko -> {len(comp)//1024} Ko")

                analyse_ia = None
                if photos_b64:
                    log("  [IA] Analyse de la photo par Claude Vision...")
                    analyse_ia = analyser_avec_claude(photos_b64, sujet, corps)

                num, path = generer_devis(from_addr, from_name, sujet, analyse_ia, photos_b64)
                log(f"  [DEVIS] Genere: {num}")

                if envoyer(from_addr, from_name, num, path, sujet):
                    marquer_traite(msg_id); traites.add(msg_id)
                    log(f"  [OK] Traite avec succes!")
            except Exception as e:
                log(f"  [X] Erreur traitement UID {uid}: {e}")

        with open('.last_uid', 'w') as f:
            f.write(str(max_seen))
        mail.logout()
    except Exception as e:
        log(f"[X] Erreur poll: {e}")

if __name__ == "__main__":
    log("="*60)
    log("PHOTO -> DEVIS v3 - ANALYSE IA - PRODUCTION")
    log(f"Entreprise: {ENTREPRISE['nom']} | Cle API: {'OK' if ANTHROPIC_KEY else 'ABSENTE'}")
    log("="*60)
    while True:
        poll()
        time.sleep(30)
