# Setup Guide

## Email Ingestion (Python Script)

```bash
export GMAIL_APP_PASSWORD="your_app_password"
python3 scripts/email_to_devis_bridge.py
```

## Webhook Direct

```bash
curl -X POST https://n8n.example.com/webhook/photo-to-devis \
  -F image=@photo.jpg \
  -F nom_entreprise="Entreprise"
```

