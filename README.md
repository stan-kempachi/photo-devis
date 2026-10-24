# Photo → Devis

Un client envoie une photo par email, il reçoit un devis en retour — sans intervention humaine.

Boucle de traitement qui tourne sur un Raspberry Pi 5 :

```
Email + photo (Gmail IMAP, polling 60 s)
        │
        ▼
Analyse de la photo par IA (Claude, vision) → description du besoin, estimation
        │
        ▼
Génération du devis HTML numéroté
        │
        ▼
Envoi par email (SMTP, IPv4 forcé + TLS), pièce jointe HTML
```

Projet de démonstration : l'entreprise fictive « Jardin Services Démo » (entretien de jardins) ; les coordonnées se changent par variables d'environnement.

## Stack

- Python 3.12+, **bibliothèque standard uniquement** (`imaplib`, `smtplib`, `email`) — aucune dépendance à installer
- API Anthropic (Claude) pour l'analyse de la photo
- systemd pour le service, redémarrage automatique
- Variante n8n : workflows `workflows/*.json` (webhook → génération → envoi)

## Installation

```bash
git clone https://github.com/stan-kempachi/photo-devis.git /opt/photo-devis
cd /opt/photo-devis
cp .env.example .env        # GMAIL_ADDRESS, GMAIL_APP_PASSWORD (mot de passe d'application), ENTREPRISE_*
chmod 600 .env
export ANTHROPIC_API_KEY=... # ou dans .env

python3 scripts/photo_to_devis_production.py   # test en premier plan
```

Service :

```bash
sudo cp photo-devis.service /etc/systemd/system/
sudo systemctl enable --now photo-devis
journalctl -u photo-devis -f
```

Guides détaillés : [`docs/SETUP_FR.md`](docs/SETUP_FR.md) · [`docs/SECURITY_FR.md`](docs/SECURITY_FR.md) (versions anglaises à côté).

## Sécurité

- Aucun identifiant dans le code : tout passe par `.env` (ignoré par git) ou l'environnement du service
- Mot de passe d'application Gmail, jamais le mot de passe du compte
- Les devis générés (`devis_outputs/`) et l'état de traitement restent locaux

## Structure

```
scripts/photo_to_devis_production.py   boucle complète (IMAP → IA → devis → SMTP)
workflows/                             variantes n8n (email-to-devis, photo-to-devis)
docs/                                  installation et sécurité (FR/EN)
photo-devis.service                    unité systemd
.env.example                           variables attendues
```

## Licence

Code publié à titre de portfolio. Tous droits réservés — Karakuri Studio.
