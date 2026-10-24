"""Rendu HTML du devis (pièce jointe de secours et archive locale)."""

import base64
import html

STYLE = """
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Segoe UI',-apple-system,Helvetica,Arial,sans-serif; color:#1a2332; background:#f0f2f5; padding:20px; }
    .page { max-width:800px; margin:0 auto; background:white; border-radius:12px; overflow:hidden; box-shadow:0 8px 30px rgba(0,0,0,0.08); }
    .banner { background:linear-gradient(135deg,#1e3a5f 0%,#2d5f8a 100%); color:white; padding:36px 44px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; }
    .banner .brand h1 { font-size:26px; letter-spacing:0.5px; }
    .banner .brand p { opacity:0.85; font-size:14px; margin-top:4px; }
    .banner .doc { text-align:right; }
    .banner .doc .label { font-size:13px; text-transform:uppercase; letter-spacing:3px; opacity:0.8; }
    .banner .doc .num { font-size:22px; font-weight:700; margin-top:4px; }
    .meta { display:flex; justify-content:space-between; flex-wrap:wrap; gap:20px; padding:32px 44px; border-bottom:1px solid #e8ecf1; }
    .meta .block { min-width:200px; }
    .meta .block h4 { font-size:11px; text-transform:uppercase; letter-spacing:2px; color:#8494a8; margin-bottom:10px; }
    .meta .block p { font-size:14px; line-height:1.7; }
    .meta .block .name { font-weight:700; font-size:16px; color:#1e3a5f; }
    .objet { padding:24px 44px; background:#f7f9fc; border-bottom:1px solid #e8ecf1; font-size:14px; }
    .objet strong { color:#1e3a5f; }
    .analyse { padding:24px 44px; background:#eef6ee; border-left:4px solid #4a9d5f; margin:24px 44px; border-radius:8px; font-size:14px; line-height:1.7; }
    .analyse h3 { font-size:12px; text-transform:uppercase; letter-spacing:2px; color:#4a9d5f; margin-bottom:8px; }
    .content { padding:10px 44px 32px; }
    table { width:100%; border-collapse:collapse; font-size:14px; }
    thead th { background:#1e3a5f; color:white; padding:13px 14px; text-align:left; font-size:12px; text-transform:uppercase; letter-spacing:1px; }
    thead th.center, td.center { text-align:center; }
    thead th.right, td.right { text-align:right; }
    tbody td { padding:14px; border-bottom:1px solid #eef1f5; }
    .totaux { margin-top:26px; margin-left:auto; width:320px; }
    .totaux .row { display:flex; justify-content:space-between; padding:10px 14px; font-size:14px; }
    .totaux .row.ttc { background:#1e3a5f; color:white; font-size:17px; font-weight:700; border-radius:8px; margin-top:6px; }
    .photo-section { margin-top:34px; }
    .photo-section h3 { font-size:13px; text-transform:uppercase; letter-spacing:2px; color:#8494a8; margin-bottom:12px; }
    .photos { display:flex; gap:12px; flex-wrap:wrap; }
    .photos img { max-width:230px; width:100%; border-radius:10px; border:1px solid #e8ecf1; box-shadow:0 4px 14px rgba(0,0,0,0.08); }
    .conditions { padding:26px 44px; background:#f7f9fc; border-top:1px solid #e8ecf1; font-size:12px; color:#67788c; line-height:1.8; }
    .conditions strong { color:#1e3a5f; }
    .brand { display:flex; align-items:center; gap:16px; }
    .brand-logo { width:64px; height:64px; border-radius:10px; object-fit:cover; }
    .signature { padding:26px 44px 40px; display:flex; justify-content:space-between; flex-wrap:wrap; gap:20px; }
    .signature .box { width:46%; min-width:240px; border:1px dashed #c3ccd6; border-radius:10px; padding:16px; font-size:12px; color:#8494a8; min-height:110px; }
    .footer { text-align:center; padding:18px; font-size:11px; color:#a5b1bf; border-top:1px solid #eef1f5; }
    @media print { body { background:white; padding:0; } .page { box-shadow:none; border-radius:0; } }
"""

CONDITIONS = (
    "Devis valable 30 jours. Acompte de 30 % à la commande, solde à la fin des travaux. "
    "Règlement par virement ou chèque. Chiffrage établi sur la base des photos transmises — "
    "susceptible d'ajustement après visite sur site."
)


def _logo_b64(chemin: str) -> str:
    if not chemin:
        return ""
    try:
        with open(chemin, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except OSError:
        return ""


def rendre_html(d, ent: dict) -> str:
    e = html.escape
    lignes = "".join(
        f"""
            <tr>
                <td>{e(str(desc))}</td>
                <td class="center">{float(qte):g}</td>
                <td class="center">{e(str(unite))}</td>
                <td class="right">{float(pu):,.2f} €</td>
                <td class="right"><strong>{float(qte) * float(pu):,.2f} €</strong></td>
            </tr>"""
        for desc, qte, unite, pu in d.prestations
    )
    duree_html = f'<p style="margin-top:8px"><strong>Durée estimée :</strong> {e(d.duree)}</p>' if d.duree else ""
    photos_html = ""
    if d.photos_b64:
        imgs = "".join(f'<img src="data:image/jpeg;base64,{p}" alt="Photo {i + 1}" />' for i, p in enumerate(d.photos_b64[:3]))
        photos_html = f"""
        <div class="photo-section">
            <h3>Photos transmises par le client</h3>
            <div class="photos">{imgs}</div>
        </div>"""
    logo = _logo_b64(ent.get("logo", ""))
    logo_html = f'<img src="data:image/png;base64,{logo}" class="brand-logo"/>' if logo else ""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Devis {e(d.num)}</title>
<style>{STYLE}</style>
</head>
<body>
<div class="page">
    <div class="banner">
        <div class="brand">{logo_html}<div><h1>{e(ent["nom"])}</h1><p>{e(ent["slogan"])}</p></div></div>
        <div class="doc"><div class="label">Devis</div><div class="num">N° {e(d.num)}</div></div>
    </div>
    <div class="meta">
        <div class="block"><h4>Émetteur</h4><p class="name">{e(ent["nom"])}</p><p>{e(ent["legal"])}<br>{e(ent["adresse"])}<br>{e(ent["email"])} · {e(ent["tel"])}<br>SIRET : {e(ent["siret"])}<br><span style="font-size:11px;color:#6b7688">{e(ent["tva_mention"])}</span></p></div>
        <div class="block"><h4>Client</h4><p class="name">{e(d.client_name)}</p><p>{e(d.client_email)}</p></div>
        <div class="block"><h4>Dates</h4><p>Émis le : <strong>{e(d.date_devis)}</strong><br>Valable jusqu'au : <strong>{e(d.date_validite)}</strong></p></div>
    </div>
    <div class="objet"><strong>Objet :</strong> {e(d.sujet)}</div>
    <div class="analyse">
        <h3>🔍 Notre analyse de votre demande</h3>
        <p>{e(d.analyse)}</p>
        {duree_html}
    </div>
    <div class="content">
        <table>
            <thead><tr><th>Désignation</th><th class="center">Qté</th><th class="center">Unité</th><th class="right">Prix unit. HT</th><th class="right">Total HT</th></tr></thead>
            <tbody>{lignes}</tbody>
        </table>
        <div class="totaux">
            <div class="row ttc"><span>Total à régler</span><span>{d.total_ttc:,.2f} €</span></div>
            <div class="row"><span style="font-size:11px;color:#6b7688">{e(ent["tva_mention"])}</span></div>
        </div>
        {photos_html}
    </div>
    <div class="conditions"><strong>Conditions :</strong> {CONDITIONS}</div>
    <div class="signature">
        <div class="box">Bon pour accord — Date et signature du client<br>(précédé de la mention « lu et approuvé »)</div>
        <div class="box">Cachet et signature de l'entreprise</div>
    </div>
    <div class="footer">{e(ent["nom"])} — Devis {e(d.num)} — Document généré le {e(d.date_devis)}</div>
</div>
</body>
</html>"""
