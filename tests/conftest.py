import base64
import io

import pytest

from photo_devis.config import Config, entreprise_depuis_env

ENV_TEST = {
    "GMAIL_ADDRESS": "test@example.com",
    "GMAIL_APP_PASSWORD": "xxxx",
    "ANTHROPIC_API_KEY": "cle-test",
    "ENTREPRISE_NOM": "Jardin Test",
}


@pytest.fixture
def cfg(tmp_path):
    env = dict(ENV_TEST, DEVIS_OUTPUT_DIR=str(tmp_path / "out"), STATE_DIR=str(tmp_path))
    return Config.depuis_env(env)


@pytest.fixture
def entreprise():
    return entreprise_depuis_env(ENV_TEST)


@pytest.fixture
def photo_jpeg_b64():
    """Petite image JPEG rouge 10x10 encodée en base64 (sans Pillow : un pseudo-JPEG)."""
    try:
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (10, 10), (200, 30, 30)).save(buf, format="JPEG")
        data = buf.getvalue()
    except ImportError:
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 64
    return base64.b64encode(data).decode()


@pytest.fixture
def analyse_ia():
    return {
        "analyse": "Haie de thuyas d'environ 12 m, hauteur 2 m, à tailler sur les deux faces.",
        "lignes": [
            {"designation": "Deplacement", "qte": 1, "unite": "forfait", "pu": 50.0},
            {"designation": "Taille de haie 12 ml", "qte": 12, "unite": "ml", "pu": 8.0},
            {"designation": "Evacuation dechets", "qte": 1.5, "unite": "m3", "pu": 45.0},
        ],
        "duree_estimee": "une demi-journee",
    }
