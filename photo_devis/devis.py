"""Construction du devis : lignes, totaux, numéro, écriture HTML + PDF."""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .config import BAREME, log

VALIDITE_JOURS = 30

Prestation = tuple[str, float, str, float]  # (désignation, quantité, unité, prix unitaire HT)


@dataclass
class Devis:
    num: str
    client_email: str
    client_name: str
    sujet: str
    analyse: str
    duree: str
    prestations: list[Prestation]
    photos_b64: list[str] = field(default_factory=list)
    date_devis: str = ""
    date_validite: str = ""

    @property
    def total_ht(self) -> float:
        return sum(float(q) * float(pu) for _, q, _, pu in self.prestations)

    @property
    def total_ttc(self) -> float:
        # Franchise en base de TVA (micro-entreprise) : pas de TVA facturée.
        return self.total_ht


def numero_devis(maintenant=None) -> str:
    maintenant = maintenant or datetime.now()
    return f"{maintenant.strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"


def prestations_par_defaut(bareme=BAREME) -> list[Prestation]:
    return [
        ("Deplacement et evaluation sur site", 1, "forfait", bareme["deplacement_forfait"]),
        ("Main d'oeuvre - travaux demandes", 4, "heure", bareme["main_oeuvre_heure"]),
        ("Evacuation des dechets", 1, "m3", bareme["evacuation_dechets_m3"]),
    ]


ANALYSE_PAR_DEFAUT = (
    "Estimation standard etablie sur la base de votre demande. Une visite sur site permettra d'affiner ce chiffrage."
)


def construire_devis(client_email, client_name, sujet, analyse_ia, photos_b64, maintenant=None) -> Devis:
    """Assemble un Devis à partir de l'analyse IA (ou d'une estimation standard si absente)."""
    maintenant = maintenant or datetime.now()
    if analyse_ia and analyse_ia.get("lignes"):
        prestations = [(li["designation"], li["qte"], li["unite"], li["pu"]) for li in analyse_ia["lignes"]]
        analyse = analyse_ia.get("analyse", "")
        duree = analyse_ia.get("duree_estimee", "")
    else:
        prestations = prestations_par_defaut()
        analyse = ANALYSE_PAR_DEFAUT
        duree = ""
    return Devis(
        num=numero_devis(maintenant),
        client_email=client_email,
        client_name=client_name,
        sujet=sujet,
        analyse=analyse,
        duree=duree,
        prestations=prestations,
        photos_b64=list(photos_b64 or []),
        date_devis=maintenant.strftime("%d/%m/%Y"),
        date_validite=(maintenant + timedelta(days=VALIDITE_JOURS)).strftime("%d/%m/%Y"),
    )


def generer_devis(cfg, client_email, client_name, sujet, analyse_ia, photos_b64) -> tuple[str, str]:
    """Écrit le devis en HTML, puis en PDF si fpdf2 est disponible. Retourne (numéro, chemin envoyé)."""
    from .rendu_html import rendre_html

    d = construire_devis(client_email, client_name, sujet, analyse_ia, photos_b64)
    os.makedirs(cfg.output_dir, exist_ok=True)
    html_path = os.path.join(cfg.output_dir, f"devis_{d.num}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(rendre_html(d, cfg.entreprise))
    try:
        from .rendu_pdf import rendre_pdf

        pdf_path = rendre_pdf(d, cfg.entreprise, os.path.join(cfg.output_dir, f"Devis_{d.num}.pdf"))
        log(f"  [PDF] Genere: {pdf_path}")
        return d.num, pdf_path
    except Exception as e:
        log(f"  [!] PDF echec ({e}) - fallback HTML")
        return d.num, html_path
