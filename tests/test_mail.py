import base64
from email.header import Header
from email.message import EmailMessage

from photo_devis import mail


def _message(
    from_hdr="Marie Dupont <marie@example.com>", subject="Demande de devis haie", body="Bonjour,\nvoici la photo.", photos=0
):
    msg = EmailMessage()
    msg["From"] = from_hdr
    msg["Subject"] = subject
    msg["Message-ID"] = "<abc@example.com>"
    msg.set_content(body)
    for i in range(photos):
        msg.add_attachment(b"\xff\xd8\xff" + bytes([i]) * 20, maintype="image", subtype="jpeg", filename=f"p{i}.jpg")
    return msg


def test_decoder_sujet_encode_utf8():
    encode = Header("Devis élagage été", "utf-8").encode()
    assert mail.decoder_sujet(encode) == "Devis élagage été"
    assert mail.decoder_sujet("") == "Demande de devis"


def test_expediteur_nom_et_adresse():
    assert mail.expediteur(_message()) == ("marie@example.com", "Marie Dupont")
    assert mail.expediteur(_message(from_hdr="marie@example.com")) == ("marie@example.com", "Client")


def test_extraire_corps_et_photos():
    msg = _message(photos=2)
    assert mail.extraire_corps(msg).startswith("Bonjour,")
    photos = mail.extraire_photos(msg)
    assert len(photos) == 2
    assert base64.b64decode(photos[0]).startswith(b"\xff\xd8\xff")


def test_max_trois_photos():
    assert len(mail.extraire_photos(_message(photos=5))) == 3


def test_est_ignore():
    assert mail.est_ignore("noreply@site.fr", "Demande de devis")  # expéditeur automatique
    assert mail.est_ignore("marie@x.fr", "Votre devis N° 202610-AB12")  # notre propre envoi
    assert mail.est_ignore("marie@x.fr", "Bonjour")  # pas de mot « devis »
    assert not mail.est_ignore("marie@x.fr", "DEVIS pour ma haie")


class FauxSMTP:
    envoyes = []
    echecs = 0

    def __init__(self, host, port, timeout):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context=None):
        pass

    def login(self, u, p):
        pass

    def send_message(self, msg):
        if FauxSMTP.echecs:
            FauxSMTP.echecs -= 1
            raise OSError("connexion coupee")
        FauxSMTP.envoyes.append(msg)


def test_envoyer_piece_jointe_pdf_et_retry(cfg, tmp_path):
    pdf = tmp_path / "Devis_X.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    FauxSMTP.envoyes, FauxSMTP.echecs = [], 1
    ok = mail.envoyer(cfg, "marie@x.fr", "Marie", "202610-AB12", str(pdf), "haie", smtp_cls=FauxSMTP, pause=0)
    assert ok and len(FauxSMTP.envoyes) == 1
    msg = FauxSMTP.envoyes[0]
    assert msg["To"] == "marie@x.fr"
    assert "202610-AB12" in msg["Subject"]
    pj = [p for p in msg.walk() if p.get_content_type() == "application/pdf"]
    assert pj and 'filename="Devis_202610-AB12.pdf"' in pj[0]["Content-Disposition"]


def test_envoyer_echec_apres_tentatives(cfg, tmp_path):
    html = tmp_path / "d.html"
    html.write_text("<html></html>")
    FauxSMTP.envoyes, FauxSMTP.echecs = [], 10
    assert not mail.envoyer(cfg, "m@x.fr", "M", "N", str(html), "s", smtp_cls=FauxSMTP, pause=0, tentatives=2)
