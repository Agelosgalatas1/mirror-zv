# Επεξήγηση: Ελέγχει απόκρυψη προσωπικών στοιχείων, ανάγνωση αρχείων και μετρήσεις ύφους.
from app.ingest.parsers import Owner, parse_file
from app.privacy import DEFAULT_BOUNDARIES, check_boundaries, redact
from app.stylometry import channel_profile, similarity

OWNER = Owner(name="Eleni Markou", aliases=["Eleni Markou", "Eleni"], emails=["eleni@kyma.example"], org_domain="kyma.example")


def test_redacts_greek_and_generic_pii():
    r = redact("IBAN GR63 0110 1250 0000 0012 3006, AFM 123456783, tel +30 210 555 0142, mail a.b@c.gr, card 4111 1111 1111 1111")
    assert "[IBAN]" in r.text and "[AFM]" in r.text and "[PHONE]" in r.text and "[EMAIL]" in r.text and "[CARD]" in r.text
    assert "0142" not in r.text


def test_checksums_avoid_false_positives():
    r = redact("Meeting on 2026-06-08 at 10:30, order 123456789, 38,000 riders")
    assert r.text == "Meeting on 2026-06-08 at 10:30, order 123456789, 38,000 riders"


def test_whatsapp_parser_marks_owner_and_context():
    txt = "12/06/2026, 20:14 - Katerina: Σάββατο;\n12/06/2026, 20:31 - Eleni Markou: ναιιι!\n12/06/2026, 20:32 - Katerina: ok\n"
    items = parse_file("chat.txt", txt.encode(), OWNER)
    assert [i.is_owner for i in items] == [False, True, False]
    assert items[1].meta["in_reply_to_text"] == "Σάββατο;"
    assert items[1].channel == "chat_personal"


def test_email_parser_classifies_internal_vs_external():
    eml = (b"From: Eleni Markou <eleni@kyma.example>\nTo: Bob <bob@vendor.example>\nSubject: Hi\n"
           b"Content-Type: text/plain; charset=utf-8\n\nHi Bob,\n\nNo thanks.\n\nBest,\nEleni\n-- \nsig 210 555 0142\n")
    [item] = parse_file("a.eml", eml, OWNER)
    assert item.is_owner and item.channel == "email_external"
    assert "sig" not in item.text  # signature stripped


def test_boundaries_match_greek_and_english():
    assert check_boundaries("What medication do you take?", DEFAULT_BOUNDARIES)["id"] == "health"
    assert check_boundaries("Τι φάρμακα παίρνεις;", DEFAULT_BOUNDARIES)["id"] == "health"
    assert check_boundaries("Should we reduce password-reset tickets?", DEFAULT_BOUNDARIES) is None


def test_stylometry_prefers_matching_style():
    owner_msgs = ["όχι Παρασκευή πλιζ 🙏 Δευτέρα πάμε 🚀", "τέλειο!! ship it 🚀", "tbh όχι μέσα στο sprint 😅"]
    prof = channel_profile(owner_msgs)
    assert similarity("οκ πάμε Δευτέρα 🚀", prof) > similarity(
        "Dear colleague, thank you for your message. I will review the proposal and revert in due course.", prof)
