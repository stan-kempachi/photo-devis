import os
import re
from datetime import datetime

from photo_devis import devis
from photo_devis.config import BAREME
from photo_devis.rendu_html import rendre_html


def test_numero_devis_format():
    num = devis.numero_devis(datetime(2026, 10, 25))
    assert re.fullmatch(r"202610-[0-9A-F]{4}", num)


def test_construire_devis_avec_analyse_ia(analyse_ia):
    d = devis.construire_devis("c@x.fr", "Client", "Devis haie", analyse_ia, [], maintenant=datetime(2026, 10, 25))
    assert len(d.prestations) == 3
    assert d.total_ht == 50 + 12 * 8 + 1.5 * 45
    assert d.total_ttc == d.total_ht  # franchise de TVA
    assert d.duree == "une demi-journee"
    assert d.date_devis == "25/10/2026"
    assert d.date_validite == "24/11/2026"


def test_construire_devis_sans_ia_utilise_le_bareme():
    d = devis.construire_devis("c@x.fr", "Client", "Devis", None, [])
    assert d.analyse == devis.ANALYSE_PAR_DEFAUT
    assert d.total_ht == BAREME["deplacement_forfait"] + 4 * BAREME["main_oeuvre_heure"] + BAREME["evacuation_dechets_m3"]


def test_rendre_html_contient_les_elements_cles(analyse_ia, entreprise, photo_jpeg_b64):
    d = devis.construire_devis("client@x.fr", "Mme <Dupont>", "Taille & haie", analyse_ia, [photo_jpeg_b64])
    html = rendre_html(d, entreprise)
    assert d.num in html
    assert "Jardin Test" in html
    assert "Taille de haie 12 ml" in html
    assert "Mme &lt;Dupont&gt;" in html  # échappement HTML
    assert "Taille &amp; haie" in html
    assert f"{d.total_ttc:,.2f} €" in html
    assert 'src="data:image/jpeg;base64,' in html
    assert 'class="brand-logo"' not in html  # pas de logo configuré → pas de balise <img> vide


def test_generer_devis_ecrit_html_et_pdf(cfg, analyse_ia, photo_jpeg_b64):
    num, path = devis.generer_devis(cfg, "c@x.fr", "Client", "Devis", analyse_ia, [photo_jpeg_b64])
    assert os.path.exists(os.path.join(cfg.output_dir, f"devis_{num}.html"))
    assert path.endswith(".pdf") and os.path.getsize(path) > 1000


def test_generer_devis_fallback_html_sans_fpdf(cfg, analyse_ia, monkeypatch):
    import photo_devis.rendu_pdf as rp

    def boom(*a, **k):
        raise RuntimeError("fpdf absent")

    monkeypatch.setattr(rp, "rendre_pdf", boom)
    num, path = devis.generer_devis(cfg, "c@x.fr", "Client", "Devis", analyse_ia, [])
    assert path.endswith(f"devis_{num}.html") and os.path.exists(path)
