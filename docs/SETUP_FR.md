# Guide de Configuration — Email → Devis

## 🚀 Configuration rapide (5 minutes)

### Étape 1: Générer Google App Password

1. Va sur **https://myaccount.google.com/security**
2. Vérifie que **2FA (authentification double facteur)** est activée
3. Cherche **"App passwords"** ou **"Mots de passe des applis"**
4. Sélectionne:
   - App: **Mail**
   - Device: **Windows/Linux/Mac**
5. Copie le mot de passe généré (ex: `xxxx xxxx xxxx xxxx`)

### Étape 2: Lancer le script

```bash
# Export la variable d'environnement
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

# Lance le script
python3 scripts/email_to_devis_bridge.py
```

Tu devrais voir:
```
2026-06-28 16:35:00 [INFO] Email → Devis Bridge starting...
2026-06-28 16:35:00 [INFO]   Gmail: votre.adresse@gmail.com
2026-06-28 16:35:00 [INFO]   Poll interval: 60s
2026-06-28 16:35:01 [INFO] Polling cycle complete
```

### Étape 3: Tester

1. **Envoie un email** à `votre.adresse@gmail.com` avec:
   - Subject: n'importe quel sujet
   - Attachement: une image JPG ou PNG

2. **Attends 60 secondes** (le prochain polling)

3. **Vérifies le résultat:**
   ```bash
   ls -lah devis_outputs/
   # devis_DEV-20260628-1234.html devrait être là
   ```

---

## 🔧 Configuration avancée

### Arrière-plan (production)

**Option 1: Screen (simple)**
```bash
screen -S email_devis
export GMAIL_APP_PASSWORD="..."
python3 scripts/email_to_devis_bridge.py
# Ctrl+A puis D pour détacher
```

**Option 2: Systemd service (recommandé)**
```bash
sudo tee /etc/systemd/system/email-to-devis.service << 'EOF'
[Unit]
Description=Email to Devis Bridge
After=network.target

[Service]
Type=simple
User=photodevis
WorkingDirectory=/opt/photo-devis
Environment="GMAIL_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx"
ExecStart=/usr/bin/python3 scripts/email_to_devis_bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable email-to-devis
sudo systemctl start email-to-devis
sudo systemctl status email-to-devis
```

### Surveillance des logs

```bash
# Logs en direct
tail -f email_to_devis.log

# Dernier devis généré
tail -5 email_to_devis.log | grep "✅"

# Erreurs
grep "ERROR\|❌" email_to_devis.log
```

---

## 🐛 Troubleshooting

### Erreur: `ERROR: Set GMAIL_APP_PASSWORD`
```bash
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
```

### Erreur: `IMAP error: [AUTHENTICATIONFAILED]`
→ Le mot de passe est incorrect ou expiré
→ Régénère un nouveau App Password sur Google

### Erreur: `Failed to generate devis`
→ Le webhook photo-to-devis est peut-être down
→ Vérifies: `curl http://localhost:5678/webhook/photo-to-devis`

### Email trouvé mais pas de photo
→ Vérifies que l'attachement est une image (JPG/PNG)
→ Vérifies que l'image fait <25MB

### Script se coupe après quelques emails
→ Peut être une limite Gmail (backoff IMAP)
→ Le script retry automatiquement toutes les 60 sec

---

## ✅ Checklist

- [ ] Google Account avec 2FA activé
- [ ] App Password généré (16 caractères)
- [ ] Script lancé avec `export GMAIL_APP_PASSWORD=...`
- [ ] Email reçu à `votre.adresse@gmail.com`
- [ ] Fichier `devis_outputs/devis_*.html` créé
- [ ] Logs montrent `✅ Devis XXX: YYY€`

