"""Paramètres du service : tout vient de l'environnement (cf. .env.example)."""

import os
from dataclasses import dataclass, field
from datetime import datetime


def log(*args):
    print(datetime.now().strftime("%H:%M:%S"), *args, flush=True)


# Barème générique (EUR HT) transmis à l'IA pour chiffrer les lignes.
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


def entreprise_depuis_env(env=os.environ) -> dict:
    """Coordonnées affichées sur le devis. Valeurs de démonstration par défaut."""
    return {
        "nom": env.get("ENTREPRISE_NOM", "Jardin Services Démo"),
        "legal": env.get("ENTREPRISE_LEGAL", "SARL Jardin Services (démonstration)"),
        "slogan": env.get("ENTREPRISE_SLOGAN", "Entretien de jardins & espaces verts"),
        "email": env.get("ENTREPRISE_EMAIL", "contact@jardin-services-demo.fr"),
        "site": env.get("ENTREPRISE_SITE", "jardin-services-demo.fr"),
        "tel": env.get("ENTREPRISE_TEL", "01 23 45 67 89"),
        "adresse": env.get("ENTREPRISE_ADRESSE", "Zone de démonstration - exemple non contractuel"),
        "siret": env.get("ENTREPRISE_SIRET", "SIRET DÉMO - non contractuel"),
        "tva_mention": env.get("ENTREPRISE_TVA_MENTION", "Exemple de démonstration - devis non contractuel"),
        # Chemin d'un logo PNG (optionnel) ; vide = pas de logo
        "logo": env.get("ENTREPRISE_LOGO", ""),
    }


def _cle_anthropic(env) -> str:
    """Clé API : variable d'environnement, sinon fichier .env externe (ANTHROPIC_ENV_FILE)."""
    cle = env.get("ANTHROPIC_API_KEY", "")
    if cle:
        return cle
    chemin = env.get("ANTHROPIC_ENV_FILE", os.path.expanduser("~/aria/.env"))
    try:
        with open(chemin) as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


@dataclass
class Config:
    gmail_address: str
    gmail_app_password: str
    from_email: str
    anthropic_key: str
    imap_host: str = "imap.gmail.com"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_timeout: int = 90
    poll_interval: int = 60
    output_dir: str = "devis_outputs"
    state_dir: str = "."
    entreprise: dict = field(default_factory=entreprise_depuis_env)

    @classmethod
    def depuis_env(cls, env=os.environ) -> "Config":
        email = env.get("GMAIL_ADDRESS", "")
        passwd = env.get("GMAIL_APP_PASSWORD", "")
        if not email or not passwd:
            raise ValueError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD manquants dans l'environnement (.env)")
        return cls(
            gmail_address=email,
            gmail_app_password=passwd,
            from_email=env.get("FROM_EMAIL", email),
            anthropic_key=_cle_anthropic(env),
            imap_host=env.get("IMAP_HOST", "imap.gmail.com"),
            smtp_host=env.get("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(env.get("SMTP_PORT", "587")),
            smtp_timeout=int(env.get("SMTP_TIMEOUT", "90")),
            poll_interval=int(env.get("POLL_INTERVAL", "60")),
            output_dir=env.get("DEVIS_OUTPUT_DIR", "devis_outputs"),
            state_dir=env.get("STATE_DIR", "."),
            entreprise=entreprise_depuis_env(env),
        )
