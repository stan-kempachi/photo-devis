import io
import json
from contextlib import contextmanager

from photo_devis import ia


def _reponse_api(texte):
    body = json.dumps({"content": [{"type": "text", "text": texte}]}).encode()

    @contextmanager
    def ouvrir(req, timeout=0):
        ouvrir.requetes.append(req)
        yield io.BytesIO(body)

    ouvrir.requetes = []
    return ouvrir


def test_sans_cle_api_retourne_none():
    assert ia.analyser_avec_claude(["x"], "Devis", "corps", "") is None


def test_parse_json_entoure_de_backticks(analyse_ia, photo_jpeg_b64):
    ouvrir = _reponse_api("```json\n" + json.dumps(analyse_ia) + "\n```")
    res = ia.analyser_avec_claude([photo_jpeg_b64], "Devis haie", "Bonjour", "cle", ouvrir=ouvrir, pause=0)
    assert res == analyse_ia
    req = ouvrir.requetes[0]
    assert req.get_header("X-api-key") == "cle"
    payload = json.loads(req.data)
    assert payload["messages"][0]["content"][0]["type"] == "image"
    assert "Devis haie" in payload["messages"][0]["content"][-1]["text"]


def test_reponse_sans_lignes_retourne_none_apres_retries(photo_jpeg_b64):
    ouvrir = _reponse_api(json.dumps({"analyse": "rien", "lignes": []}))
    assert ia.analyser_avec_claude([photo_jpeg_b64], "Devis", "", "cle", ouvrir=ouvrir, pause=0, tentatives=2) is None
    assert len(ouvrir.requetes) == 2


def test_erreur_reseau_puis_succes(analyse_ia, photo_jpeg_b64):
    ok = _reponse_api(json.dumps(analyse_ia))
    appels = []

    @contextmanager
    def ouvrir(req, timeout=0):
        appels.append(1)
        if len(appels) == 1:
            raise OSError("timeout")
        with ok(req, timeout) as r:
            yield r

    assert ia.analyser_avec_claude([photo_jpeg_b64], "Devis", "", "cle", ouvrir=ouvrir, pause=0) == analyse_ia


def test_max_trois_photos(photo_jpeg_b64):
    req = ia.construire_requete([photo_jpeg_b64] * 5, "Devis", "", "cle")
    content = json.loads(req.data)["messages"][0]["content"]
    assert sum(1 for c in content if c["type"] == "image") == 3
