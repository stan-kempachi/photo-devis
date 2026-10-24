from email.message import EmailMessage

from photo_devis import main
from photo_devis.state import Etat


def test_etat_roundtrip(tmp_path):
    e = Etat(str(tmp_path))
    assert e.charger_traites() == set()
    assert e.lire_last_uid() == 0
    e.marquer_traite("<a@x>")
    e.marquer_traite("<b@x>")
    e.ecrire_last_uid(42)
    assert e.charger_traites() == {"<a@x>", "<b@x>"}
    assert e.lire_last_uid() == 42


def test_etat_last_uid_corrompu(tmp_path):
    (tmp_path / ".last_uid").write_text("pas un nombre")
    assert Etat(str(tmp_path)).lire_last_uid() == 0


def _msg(subject="Demande de devis", mid="<m1@x>"):
    m = EmailMessage()
    m["From"] = "Paul <paul@x.fr>"
    m["Subject"] = subject
    m["Message-ID"] = mid
    m.set_content("corps")
    return m


def test_traiter_message_enchaine_devis_et_envoi(cfg, monkeypatch):
    appels = {}
    monkeypatch.setattr(main.devis, "generer_devis", lambda *a: appels.setdefault("devis", a) and ("202610-0001", "x.html"))
    monkeypatch.setattr(main.mail, "envoyer", lambda *a, **k: appels.setdefault("envoi", a) and True)
    etat = Etat(cfg.state_dir)
    traites = set()
    main.traiter_message(cfg, etat, _msg(), traites)
    assert appels["devis"][1:4] == ("paul@x.fr", "Paul", "Demande de devis")
    assert appels["envoi"][3] == "202610-0001"
    assert "<m1@x>" in traites and "<m1@x>" in etat.charger_traites()


def test_traiter_message_ignore_sans_devis(cfg, monkeypatch):
    monkeypatch.setattr(main.devis, "generer_devis", lambda *a: (_ for _ in ()).throw(AssertionError("ne doit pas generer")))
    etat = Etat(cfg.state_dir)
    traites = set()
    main.traiter_message(cfg, etat, _msg(subject="Bonjour"), traites)
    assert "<m1@x>" in traites


def test_traiter_message_deja_traite(cfg, monkeypatch):
    monkeypatch.setattr(main.devis, "generer_devis", lambda *a: (_ for _ in ()).throw(AssertionError("ne doit pas generer")))
    main.traiter_message(cfg, Etat(cfg.state_dir), _msg(), {"<m1@x>"})
