# Επεξήγηση: Ελέγχει ταυτοποίηση, ιδιωτικές μνήμες, συνομιλίες, εισαγωγή και κληρονομικότητα.
import pytest

pytestmark = pytest.mark.usefixtures("published_company_rules")

import time

from fastapi.testclient import TestClient

from app.main import app

SALES = ("sales_manager", "sales2026")
FINANCE = ("finance_manager", "finance2026")
CEO = ("ceo", "ceo2026")


def login(c: TestClient, who=SALES) -> dict:
    r = c.post("/api/login", json={"username": who[0], "password": who[1]})
    assert r.status_code == 200, r.text
    c.cookies.clear()  # these tests use the bearer token; the cookie flow has its own test
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_login_required_and_wrong_password_rejected():
    with TestClient(app) as c:
        assert c.get("/api/status").status_code == 401
        assert c.post("/api/login", json={"username": SALES[0], "password": "wrong"}).status_code == 401
        org = c.get("/api/org").json()
        roles = {p["id"]: p["reports_to"] for p in org["persons"]}
        assert roles == {"ceo": None, "sales": "ceo", "finance": "ceo", "sales_employee": "sales",
                         "finance_employee": "finance"}
        assert org["company"] == "NexaTech Solutions"
        # e-mail works as well as the username
        assert c.post("/api/login", json={"email": "a.petrou@nexatech.example", "password": "sales2026"}).status_code == 200


def test_each_manager_sees_only_own_data_and_can_consult_ceo():
    with TestClient(app) as c:
        hs, hf = login(c, SALES), login(c, FINANCE)
        st = c.get("/api/status", headers=hs).json()
        assert st["me"]["id"] == "sales" and [t["id"] for t in st["targets"]] == ["sales", "ceo"]
        sales_sources = {s["id"] for s in c.get("/api/sources", headers=hs).json()["sources"]}
        fin_sources = {s["id"] for s in c.get("/api/sources", headers=hf).json()["sources"]}
        assert sales_sources and fin_sources and not (sales_sources & fin_sources)
        # sideways access is forbidden, upwards is allowed
        assert c.post("/api/twin/ask", headers=hs, json={"question": "Γεια", "target": "finance"}).status_code == 403
        ceo = c.post("/api/twin/ask", headers=hs, json={"question": "Ποιος εγκρίνει όρους πληρωμής net90;",
                                                         "target": "ceo"}).json()
        assert "net90" in ceo["answer"]
        # a finance item is invisible to sales
        fin_item = c.get("/api/sources", headers=hf).json()["sources"][0]["id"] + "-000"
        assert c.get(f"/api/items/{fin_item}", headers=hs).status_code == 404


def test_managers_inherit_ceo_company_rules():
    from app import profile
    from app.context import as_person

    with TestClient(app) as c:
        hs = login(c, SALES)
        prof = c.get("/api/profile", headers=hs).json()
        inherited = {r["id"] for r in prof["inherited"]["decision_rules"]}
        with as_person("ceo"):
            ceo_rules = profile.current()["decision_rules"]
        company = {f"ceo.{r['id']}" for r in ceo_rules if r.get("scope") == "company"}
        personal = {f"ceo.{r['id']}" for r in ceo_rules if r.get("scope") == "personal"}
        assert company and company <= inherited and not (personal & inherited)
        assert all(not r["id"].startswith("ceo.") for r in prof["decision_rules"])
        # inherited rules are read-only for the manager
        assert c.patch("/api/profile/traits/ceo.r1", headers=hs, json={"action": "delete"}).status_code == 403
        # the twin applies an inherited rule and says where it comes from
        d = c.post("/api/twin/decide", headers=hs, json={
            "situation": "Μια εταιρεία θέλει αποκλειστικό συμβόλαιο 24 μηνών με μεγάλη έκπτωση",
            "options": ["Αποκλειστικό συμβόλαιο 24 μηνών", "Μη αποκλειστική δοκιμή με ρήτρα εξόδου"]}).json()
        assert d["choice"] == 1 and any(t.get("inherited_from") for t in d["traits"])


def test_manager_follows_company_rules_from_the_ceo():
    with TestClient(app) as c:
        hf = login(c, FINANCE)
        d = c.post("/api/twin/decide", headers=hf, json={
            "situation": "Ένας πελάτης ζητά όρους πληρωμής net90",
            "options": ["Η Μυρτώ εγκρίνει μόνη της το net90", "Το net90 πηγαίνει στην CEO με εισήγηση του Finance"]}).json()
        assert d["choice"] == 1
        spend = c.post("/api/twin/decide", headers=hf, json={
            "situation": "Ένας πελάτης ζητά αποκλειστικότητα δύο ετών",
            "options": ["Υπογράφουμε την αποκλειστικότητα", "Μη αποκλειστικό pilot 6 μηνών με stop-loss"]}).json()
        assert spend["choice"] == 1


@pytest.mark.parametrize("amount, correct_role", [("12", 0), ("12,01", 1), ("13", 1)])
@pytest.mark.parametrize("reverse_options", [False, True])
def test_discount_approval_uses_the_inherited_company_threshold(amount, correct_role, reverse_options):
    options = [f"Ο Sales Manager εγκρίνει την έκπτωση {amount}%.",
               f"Η έκπτωση {amount}% πάει στην CEO."]
    if reverse_options:
        options.reverse()
    with TestClient(app) as c:
        result = c.post("/api/twin/decide", headers=login(c, SALES), json={
            "situation": f"Ο πελάτης ζητά έκπτωση {amount}% με SALE-DISC-v2.",
            "options": options,
        }).json()
    assert result["choice"] == (1 - correct_role if reverse_options else correct_role)
    assert any(t["id"] == "ceo.demo-sale-disc-v2" for t in result["traits"])


def test_chat_small_talk_and_follow_ups():
    with TestClient(app) as c:
        hs = login(c, SALES)
        hi = c.post("/api/twin/ask", headers=hs, json={"question": "Γεια!"}).json()
        assert "Αλέξανδρος" in hi["answer"]
        a = c.post("/api/twin/ask", headers=hs, json={"question": "Ποια έκπτωση εγκρίνεις εσύ;"}).json()
        assert "12%" in a["answer"]
        history = [{"role": "user", "text": "Ποια έκπτωση εγκρίνεις εσύ;"},
                   {"role": "twin", "text": a["answer"], "traits": [t["id"] for t in a["traits"]]}]
        why = c.post("/api/twin/ask", headers=hs, json={"question": "γιατί;", "history": history}).json()
        assert "Είχα γράψει" in why["answer"] and why["memories"]
        b = c.post("/api/twin/ask", headers=hs, json={"question": "Τι φάρμακα παίρνεις;"}).json()
        assert b["boundary"]["id"] == "health"


def test_upload_and_forget_own_source_and_rebuild():
    chat = "\n".join([
        "01/11/2026, 10:00 - Alexis: Πάμε για καφέ αύριο;",
        "01/11/2026, 10:05 - Αλέξανδρος Πέτρου: ναι! 11:00 στο γνωστό ☕",
        "02/11/2026, 18:00 - Alexis: Ποιο deal κλείνουμε πρώτο;",
        "02/11/2026, 18:10 - Αλέξανδρος Πέτρου: το renewal της Orion, πάντα με margin πρώτα",
    ])
    with TestClient(app) as c:
        hs = login(c, SALES)
        r = c.post("/api/sources", headers=hs, files={"file": ("chat.txt", chat.encode(), "text/plain")}).json()
        assert r["items"] == 4 and r["source_id"].startswith("sales-")
        job = c.post("/api/profile/build", headers=hs).json()
        for _ in range(50):
            j = c.get(f"/api/jobs/{job['id']}", headers=hs).json()
            if j["status"] != "running":
                break
            time.sleep(0.1)
        assert j["status"] == "done"
        res = c.delete(f"/api/sources/{r['source_id']}", headers=hs).json()
        assert res["deleted_items"]
        hc = login(c, CEO)
        assert c.post("/api/reset-demo", headers=hc, json={"confirmation":"RESET_DEMO"}).status_code == 200


def test_ceo_evaluation_beats_baseline_offline():
    from app import evaluation
    from app.context import as_person

    with TestClient(app):
        with as_person("ceo"):
            res = evaluation.run()
    s = res["summary"]
    assert s["errors"] == 0
    assert s["decision_accuracy"] > s["baseline_decision_accuracy"]
    assert s["abstention_rate"] >= 75 and s["knowledge_recall"] >= 50


def test_offline_decisions_use_only_relevant_situation_evidence():
    from app import evaluation, twin
    from app.context import as_person

    with TestClient(app):
        for person in ("ceo", "sales", "finance"):
            with as_person(person):
                holdout = evaluation.load_holdout()
                for case in holdout["decisions"]:
                    result = twin.decide(case["situation"], case["options"], log=False)
                    assert result["choice"] == case["actual"], f"{person}/{case['id']}: {result['why']}"

        with as_person("sales"):
            unknown = twin.decide("Να ιδρύσουμε γραφείο στη Σελήνη;", ["Ναι", "Όχι"], log=False)
        assert unknown["choice"] is None and unknown["unsure"]


def test_offline_answers_respect_policy_versions_and_abstain_without_evidence():
    from app import twin
    from app.context import as_person

    with TestClient(app):
        with as_person("sales"):
            versioned = twin.ask("Μέχρι πόση έκπτωση μπορεί να βάλει σε draft ένας Sales Executive με το v2?",
                                 log=False)
            unknown = twin.ask("Ποιος θα αντικαταστήσει την CEO αν φύγει?", log=False)
        with as_person("ceo"):
            budget = twin.ask("Πόσο budget έμεινε αδιάθετο για το Q4?", log=False)

    assert "6%" in versioned["answer"] and "23%" in versioned["answer"]
    assert "5%" not in versioned["answer"]
    assert unknown["unsure"] and "δεν το ξέρω" in unknown["answer"].lower()
    assert "34k" in budget["answer"].lower()


def test_ceo_quarter_priorities_are_in_the_shipped_profile():
    from app import twin
    from app.context import as_person

    with TestClient(app):
        with as_person("ceo"):
            result = twin.ask("Τι είναι προτεραιότητα αυτό το τρίμηνο;", log=False)

    assert not result["unsure"]
    assert any(t["id"] == "k16" for t in result["traits"])
    assert "renewals" in result["answer"].lower()


def test_live_model_abstention_cannot_hide_matching_profile_evidence(monkeypatch):
    from app import twin
    from app.context import as_person

    monkeypatch.setattr(twin.LLM_CLIENT, "provider", "openai")
    monkeypatch.setattr(twin.LLM_CLIENT, "json", lambda *args, **kwargs: {
        "answer": "Δεν ξέρω ακόμη.", "confidence": 0.2, "unsure": True,
        "trait_refs": [], "memory_refs": [], "why": "No relevant memories found.",
    })
    with TestClient(app):
        with as_person("ceo"):
            result = twin.ask("Σε pilot, αν ένα τιμολόγιο είναι πάνω από 15 ημέρες ληξιπρόθεσμο, ποιο stop-loss εφαρμόζω;",
                              log=False)

    assert not result["unsure"]
    assert result["mode"] == "grounded-profile"
    assert any(t["id"] == "r4" for t in result["traits"])
    assert "παγώνω νέες παραγγελίες" in result["answer"].lower()


def test_manager_evaluation_uses_held_out_examples():
    with TestClient(app) as c:
        hf = login(c, SALES)
        job = c.post("/api/eval/run", headers=hf).json()
        for _ in range(100):
            j = c.get(f"/api/jobs/{job['id']}", headers=hf).json()
            if j["status"] != "running":
                break
            time.sleep(0.1)
        assert j["status"] == "done" and not j["result"]["auto_holdout"] and j["result"]["cases"]["reply"]
        s = j["result"]["summary"]
        assert s["decision_accuracy"] > s["baseline_decision_accuracy"]


def test_evaluation_is_owner_only():
    with TestClient(app) as c:
        hs = login(c, SALES)
        assert c.post("/api/eval/run?target=finance", headers=hs).status_code == 403
        assert c.post("/api/eval/run?target=ceo", headers=hs).status_code == 403
        assert c.get("/api/eval/latest?target=ceo", headers=hs).status_code == 403


def test_saved_conversations_are_private_and_keep_context():
    with TestClient(app) as c:
        hs, hf = login(c, SALES), login(c, FINANCE)
        conv = c.post("/api/conversations", headers=hs, json={"target": "ceo", "title": "Όροι πληρωμής"}).json()
        a = c.post("/api/twin/ask", headers=hs, json={"question": "Ποιος εγκρίνει όρους πληρωμής net90;", "target": "ceo",
                                                      "conversation_id": conv["id"]}).json()
        assert a["message_id"]
        # "why?" uses the history stored on the server, not sent by the browser
        why = c.post("/api/twin/ask", headers=hs, json={"question": "γιατί;", "target": "ceo",
                                                        "conversation_id": conv["id"]}).json()
        assert why['traits'] and not why['memories']
        assert 'δημοσιευμένος' in why['answer']
        assert len(c.get(f"/api/conversations/{conv['id']}", headers=hs).json()["messages"]) == 4
        assert c.get(f"/api/conversations/{conv['id']}", headers=hf).status_code == 404
        assert c.post("/api/twin/ask", headers=hs, json={"question": "x", "target": "sales",
                                                         "conversation_id": conv["id"]}).status_code == 400
        fb = c.post("/api/feedback", headers=hs, json={"target": "ceo", "message_id": a["message_id"],
                                                       "rating": "faithful"}).json()
        assert fb["faithful"] >= 1
        assert c.post("/api/feedback", headers=hs, json={"target": "finance", "rating": "faithful"}).status_code == 403
        assert c.delete(f"/api/conversations/{conv['id']}", headers=hs).json()["ok"]
