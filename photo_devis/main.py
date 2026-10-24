"""Boucle de polling : IMAP → analyse IA → devis → SMTP."""

import sys
import time

from . import __version__, devis, ia, mail
from .config import Config, log
from .state import Etat


def traiter_message(cfg, etat, msg, traites: set) -> None:
    msg_id = (msg.get("Message-ID") or "").strip()
    if msg_id in traites:
        return
    from_addr, from_name = mail.expediteur(msg)
    sujet = mail.decoder_sujet(msg.get("Subject", "Demande de devis"))

    if mail.est_ignore(from_addr, sujet):
        etat.marquer_traite(msg_id)
        traites.add(msg_id)
        return

    log(f"  [MAIL] De {from_name}: {sujet}")
    corps = mail.extraire_corps(msg)
    photos_b64 = mail.extraire_photos(msg)

    analyse_ia = None
    if photos_b64:
        log("  [IA] Analyse de la photo par Claude Vision...")
        analyse_ia = ia.analyser_avec_claude(photos_b64, sujet, corps, cfg.anthropic_key)

    num, path = devis.generer_devis(cfg, from_addr, from_name, sujet, analyse_ia, photos_b64)
    log(f"  [DEVIS] Genere: {num}")

    if mail.envoyer(cfg, from_addr, from_name, num, path, sujet):
        etat.marquer_traite(msg_id)
        traites.add(msg_id)
        log("  [OK] Traite avec succes!")


def poll(cfg, etat) -> None:
    try:
        traites = etat.charger_traites()
        imap = mail.connecter_imap(cfg)
        try:
            last_uid = etat.lire_last_uid()
            if last_uid == 0:
                # Premier lancement : on repère le dernier UID sans traiter le passé.
                last_uid = mail.uid_max(imap)
                etat.ecrire_last_uid(last_uid)
                log(f"[INIT] last_uid initialise a {last_uid}")
                return

            uids = mail.nouveaux_uids(imap, last_uid)
            if not uids:
                return
            log(f"[POLL] {len(uids)} nouveau(x) message(s)")
            max_seen = last_uid
            for uid in uids:
                max_seen = max(max_seen, uid)
                try:
                    msg = mail.lire_message(imap, uid)
                    if msg is None:
                        continue
                    if not msg.get("Message-ID"):
                        msg["Message-ID"] = f"uid-{uid}"
                    traiter_message(cfg, etat, msg, traites)
                except Exception as e:
                    log(f"  [X] Erreur traitement UID {uid}: {e}")
            etat.ecrire_last_uid(max_seen)
        finally:
            try:
                imap.logout()
            except Exception:
                pass
    except Exception as e:
        log(f"[X] Erreur poll: {e}")


def run(env=None) -> None:
    try:
        cfg = Config.depuis_env(env) if env is not None else Config.depuis_env()
    except ValueError as e:
        sys.exit(str(e))
    mail.forcer_ipv4()
    etat = Etat(cfg.state_dir)
    log("=" * 60)
    log(f"PHOTO -> DEVIS v{__version__} - ANALYSE IA - PRODUCTION")
    log(
        f"Entreprise: {cfg.entreprise['nom']} | Cle API: {'OK' if cfg.anthropic_key else 'ABSENTE'} | Polling: {cfg.poll_interval}s"
    )
    log("=" * 60)
    while True:
        poll(cfg, etat)
        time.sleep(cfg.poll_interval)


if __name__ == "__main__":
    run()
