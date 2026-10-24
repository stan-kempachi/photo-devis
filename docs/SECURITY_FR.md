# Guide de Sécurité

## 🔐 Principes généraux

### Secrets & Credentials
```bash
# ❌ JAMAIS en dur dans le code
password = "mon_mot_de_passe"

# ✅ TOUJOURS via variables d'environnement
password = os.getenv("GMAIL_APP_PASSWORD", "")
```

### Fichiers sensibles
```bash
.env                        # ❌ Jamais commité
.env.local                  # ❌ Jamais commité
.email_processed_hashes     # ✅ Permissions 0600
email_to_devis.log         # ✅ Permissions 0600
```

---

## 🔑 Gestion des clés SSH

### Génération (déjà fait)
```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_portfolio -N ""
```

### Sécurité
- ✅ Clé privée: `0600` (lisible par owner seulement)
- ✅ Clé publique: Ajoutée à GitHub
- ✅ Pas de passphrase (OK pour CI/CD)
- ✅ Rotation: Annuelle recommandée

### Utilisation
```bash
git push origin main  # Utilise automatiquement la clé SSH
```

---

## 📧 Email & IMAP

### App Password (Google)
- ✅ Plus sécurisé que le mot de passe Gmail
- ✅ Révocable à tout moment
- ✅ Limité à l'app (Gmail seul)
- ✅ 16 caractères alphanumériques

### Bonnes pratiques
```bash
# ❌ Mauvais
script.sh GMAIL_APP_PASSWORD="xxxx"

# ✅ Bon
export GMAIL_APP_PASSWORD="xxxx"
python3 script.py
```

---

## 🖼️ Validation des images

### Vérifications effectuées
1. **Format valide**: Base64 + magic bytes (JPG/PNG)
2. **Taille max**: 25 MB
3. **Encodage**: UTF-8 sans erreurs

### Exemple rejeté
```
❌ Image too large: 30000000 > 25000000
❌ Image doesn't match JPEG or PNG format
❌ Invalid base64
```

---

## 🔄 Retry & Rate Limiting

### Retry logic
- **Max retries**: 3 tentatives
- **Delay entre retries**: 5 secondes
- **Timeout par requête**: 30 secondes

### Polling rate
- **Intervalle**: 60 secondes (pas de spam IMAP)
- **Déduplication**: Via hashes SHA256

---

## 📝 Logging

### Format
```
2026-06-28 16:35:00 [INFO] Message informatif
2026-06-28 16:35:01 [WARNING] Attention: quelque chose
2026-06-28 16:35:02 [ERROR] Erreur: action échouée
```

### Fichiers
- `email_to_devis.log` → Logs persistants
- `stdout` → Affichage en direct

### Aucun secret en log
```
# ❌ Mauvais
logger.info(f"Password: {GMAIL_APP_PASSWORD}")

# ✅ Bon
logger.info("Gmail auth successful")
```

---

## 🛡️ Recommandations

### Développement
- [ ] Utiliser `.env.example` pour les variables
- [ ] Ne jamais commiter `.env` ou `.env.local`
- [ ] Tester avec des données fictives
- [ ] Vérifier les logs avant de déployer

### Production
- [ ] Utiliser systemd service avec `Restart=always`
- [ ] Monitorer les logs pour les erreurs
- [ ] Faire du backups des fichiers (devis_outputs/)
- [ ] Mettre à jour les App Passwords tous les 6 mois
- [ ] Surveiller l'utilisation de quota Gmail

### Audit
- [ ] Revoir les logs mensuellement
- [ ] Vérifier les permissions des fichiers
- [ ] Tester la récupération après erreur
- [ ] Valider que les secrets ne sont pas exposés

