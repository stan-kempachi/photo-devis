"""État local persistant : messages déjà traités et dernier UID IMAP vu."""

import os


class Etat:
    def __init__(self, dossier: str = "."):
        self.dossier = dossier
        self._traites = os.path.join(dossier, ".processed_emails")
        self._last_uid = os.path.join(dossier, ".last_uid")

    # ----- messages traités (Message-ID) -----

    def charger_traites(self) -> set[str]:
        if not os.path.exists(self._traites):
            return set()
        with open(self._traites) as f:
            return {line.strip() for line in f if line.strip()}

    def marquer_traite(self, msg_id: str) -> None:
        with open(self._traites, "a") as f:
            f.write(msg_id + "\n")

    # ----- dernier UID -----

    def lire_last_uid(self) -> int:
        try:
            with open(self._last_uid) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            return 0

    def ecrire_last_uid(self, uid: int) -> None:
        with open(self._last_uid, "w") as f:
            f.write(str(uid))
