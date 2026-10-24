"""Rendu PDF du devis avec fpdf2 (dépendance optionnelle : sans elle, le HTML est envoyé)."""

import base64
import io
import os

BLEU = (30, 58, 95)
GRIS = (132, 148, 168)
VERT = (74, 157, 95)
FOND_VERT = (238, 246, 238)
TEXTE = (30, 40, 55)
BLANC = (255, 255, 255)

CONDITIONS = (
    "Conditions : Devis valable 30 jours. Acompte de 30 % a la commande, solde a la fin des travaux. "
    "Reglement par virement ou cheque. Chiffrage etabli sur la base des photos transmises - "
    "susceptible d'ajustement apres visite sur site."
)


def _txt(s) -> str:
    """Les polices de base de fpdf2 sont latin-1 : on remplace ce qui ne passe pas."""
    return str(s).encode("latin-1", "replace").decode("latin-1")


def rendre_pdf(d, ent: dict, chemin: str) -> str:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    _banniere(pdf, d, ent)
    _meta(pdf, d, ent)
    _objet(pdf, d)
    _analyse(pdf, d)
    _tableau(pdf, d)
    _totaux(pdf, d, ent)
    _photos(pdf, d)
    _conditions_signatures(pdf)

    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    pdf.output(chemin)
    return chemin


def _banniere(pdf, d, ent):
    pdf.set_fill_color(*BLEU)
    pdf.rect(0, 0, 210, 34, "F")
    logo = ent.get("logo", "")
    if logo and os.path.exists(logo):
        try:
            pdf.image(logo, x=176, y=4, w=26, h=26)
        except Exception:
            pass
    pdf.set_text_color(*BLANC)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(12, 8)
    pdf.cell(120, 10, _txt(ent["nom"]))
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(12, 19)
    pdf.cell(120, 6, _txt(ent["slogan"]))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(120, 8)
    pdf.cell(52, 5, "DEVIS", align="R")
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_xy(120, 14)
    pdf.cell(52, 9, _txt(f"N. {d.num}"), align="R")


def _meta(pdf, d, ent):
    y = 42
    pdf.set_text_color(*GRIS)
    pdf.set_font("Helvetica", "B", 8)
    for x, label in ((12, "EMETTEUR"), (78, "CLIENT"), (146, "DATES")):
        pdf.set_xy(x, y)
        pdf.cell(60, 5, label)
    pdf.set_text_color(*TEXTE)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(12, y + 6)
    pdf.cell(60, 5, _txt(ent["nom"]))
    pdf.set_xy(78, y + 6)
    pdf.cell(60, 5, _txt(d.client_name[:32]))
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_xy(12, y + 12)
    pdf.multi_cell(62, 4.2, _txt(f"{ent['legal']}\n{ent['adresse']}\n{ent['email']} - {ent['tel']}\nSIRET : {ent['siret']}"))
    pdf.set_xy(78, y + 12)
    pdf.multi_cell(62, 4.2, _txt(d.client_email[:40]))
    pdf.set_xy(146, y + 12)
    pdf.multi_cell(52, 4.2, _txt(f"Emis le : {d.date_devis}\nValable jusqu'au : {d.date_validite}"))


def _objet(pdf, d):
    y = 70
    pdf.set_fill_color(247, 249, 252)
    pdf.rect(8, y, 194, 10, "F")
    pdf.set_xy(12, y + 2)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*BLEU)
    pdf.cell(16, 6, "Objet :")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*TEXTE)
    pdf.cell(170, 6, _txt(d.sujet[:95]))


def _analyse(pdf, d):
    y = 86
    pdf.set_xy(12, y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*VERT)
    pdf.cell(0, 5, "NOTRE ANALYSE DE VOTRE DEMANDE")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 60, 45)
    corps = d.analyse + (f"\nDuree estimee : {d.duree}" if d.duree else "")
    pdf.set_fill_color(*FOND_VERT)
    pdf.set_xy(12, y + 6)
    pdf.multi_cell(186, 4.8, _txt(corps), fill=True)


def _tableau(pdf, d):
    pdf.set_xy(12, pdf.get_y() + 8)
    pdf.set_fill_color(*BLEU)
    pdf.set_text_color(*BLANC)
    pdf.set_font("Helvetica", "B", 8.5)
    W = [92, 16, 20, 28, 30]
    for w, titre in zip(W, ["DESIGNATION", "QTE", "UNITE", "PU HT", "TOTAL HT"], strict=True):
        pdf.cell(w, 8, titre, fill=True, align="C" if w < 90 else "L")
    pdf.ln()
    pdf.set_text_color(*TEXTE)
    for i, (desc, qte, unite, pu) in enumerate(d.prestations):
        pdf.set_fill_color(252, 253, 255) if i % 2 else pdf.set_fill_color(245, 247, 250)
        pdf.set_x(12)
        pdf.set_font("Helvetica", "", 8.5)
        txt = _txt(desc)
        if len(txt) > 62:
            txt = txt[:60] + "..."
        pdf.cell(W[0], 7.5, txt, fill=True)
        pdf.cell(W[1], 7.5, f"{float(qte):g}", fill=True, align="C")
        pdf.cell(W[2], 7.5, _txt(unite), fill=True, align="C")
        pdf.cell(W[3], 7.5, f"{float(pu):,.2f} EUR", fill=True, align="R")
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(W[4], 7.5, f"{float(qte) * float(pu):,.2f} EUR", fill=True, align="R")
        pdf.ln()


def _totaux(pdf, d, ent):
    y = pdf.get_y() + 6
    pdf.set_xy(120, y)
    pdf.set_fill_color(*BLEU)
    pdf.set_text_color(*BLANC)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(45, 9, " Total a regler", fill=True)
    pdf.cell(33, 9, f"{d.total_ttc:,.2f} EUR ", fill=True, align="R")
    pdf.set_text_color(120, 130, 145)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_xy(120, y + 11)
    pdf.cell(78, 4, _txt(ent["tva_mention"]), align="R")
    pdf.set_text_color(*TEXTE)
    pdf.set_y(y + 20)


def _photos(pdf, d):
    if not d.photos_b64:
        return
    y = pdf.get_y() + 16
    if y > 230:
        pdf.add_page()
        y = 20
    pdf.set_xy(12, y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*GRIS)
    pdf.cell(0, 5, "PHOTOS TRANSMISES PAR LE CLIENT")
    x = 12
    for pb64 in d.photos_b64[:3]:
        try:
            pdf.image(io.BytesIO(base64.b64decode(pb64)), x=x, y=y + 7, w=58)
            x += 62
        except Exception:
            pass
    pdf.set_y(y + 7 + 46)


def _conditions_signatures(pdf):
    if pdf.get_y() > 235:
        pdf.add_page()
    y = pdf.get_y() + 6
    pdf.set_xy(12, y)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(103, 120, 140)
    pdf.multi_cell(186, 3.8, _txt(CONDITIONS))
    y = pdf.get_y() + 5
    pdf.set_draw_color(195, 204, 214)
    pdf.rect(12, y, 90, 26)
    pdf.set_xy(14, y + 2)
    pdf.multi_cell(86, 3.6, _txt("Bon pour accord - Date et signature du client\n(precede de la mention lu et approuve)"))
    pdf.rect(108, y, 90, 26)
    pdf.set_xy(110, y + 2)
    pdf.multi_cell(86, 3.6, _txt("Cachet et signature de l'entreprise"))
