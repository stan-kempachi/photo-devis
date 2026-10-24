"""Analyse des photos par Claude (vision) : retourne l'analyse et les lignes chiffrées."""

import json
import time
import urllib.request

from .config import BAREME, log

MODELE = "claude-sonnet-4-6"
API_URL = "https://api.anthropic.com/v1/messages"
MAX_PHOTOS = 3

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


def construire_requete(photos_b64, sujet, corps, api_key, bareme=BAREME) -> urllib.request.Request:
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": p}} for p in photos_b64[:MAX_PHOTOS]
    ]
    bareme_txt = "\n".join(f"- {k.replace('_', ' ')}: {v} EUR" for k, v in bareme.items())
    content.append({"type": "text", "text": PROMPT_ANALYSE.format(sujet=sujet, corps=corps[:500], bareme=bareme_txt)})
    payload = json.dumps({"model": MODELE, "max_tokens": 1500, "messages": [{"role": "user", "content": content}]}).encode()
    return urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
    )


def parser_reponse(data: dict):
    """Extrait le JSON du devis depuis la réponse de l'API (tolère un bloc ```json)."""
    texte = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    texte = texte.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    result = json.loads(texte)
    return result if result.get("lignes") else None


def analyser_avec_claude(photos_b64, sujet, corps, api_key, *, ouvrir=urllib.request.urlopen, tentatives=2, pause=3):
    """Envoie photos + demande à Claude Vision. Retourne un dict {analyse, lignes, duree_estimee} ou None."""
    if not api_key:
        log("  [!] Pas de cle API - fallback generique")
        return None
    req = construire_requete(photos_b64, sujet, corps, api_key)
    for tentative in range(tentatives):
        try:
            with ouvrir(req, timeout=60) as resp:
                data = json.loads(resp.read())
            result = parser_reponse(data)
            if result:
                log(f"  [IA] Analyse OK: {len(result['lignes'])} lignes")
                return result
        except Exception as e:
            log(f"  [!] Tentative IA {tentative + 1}: {e}")
            time.sleep(pause)
    return None
