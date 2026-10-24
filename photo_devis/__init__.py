"""Photo → Devis : un email avec une photo entre, un devis chiffré par IA ressort.

Modules :
- config  : paramètres (variables d'environnement), coordonnées de l'entreprise, barème
- mail    : lecture IMAP, décodage des messages, envoi SMTP
- ia      : analyse des photos par Claude (vision)
- devis   : génération du devis (HTML + PDF)
- state   : état local (messages traités, dernier UID)
- main    : boucle de polling
"""

__version__ = "3.1.0"
