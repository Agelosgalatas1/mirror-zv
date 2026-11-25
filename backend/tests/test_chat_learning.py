"""Learning from every conversation: ratings move trait weights, unanswered questions reach the owner."""
from fastapi.testclient import TestClient

from app import profile
from app.context import as_person
from app.main import app

H = {"X-Mirror-Request": "1"}


def login(c: TestClient, username: str, password: str) -> None:
    assert c.post("/api/login", json={"username": username, "password": password}).status_code == 200


def ask(c: TestClient, mid: str, question: str) -> dict:
    t = c.post(f"/api/mirrors/{mid}/conversations", json={"title": question[:40]}, headers=H).json()
    r = c.post(f"/api/mirrors/{mid}/ask", json={"question": question, "conversation_id": t["conversation_id"]}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def test_rating_an_answer_changes_the_weight_of_the_traits_it_used():
    with TestClient(app) as c:
        login(c, "sales_manager", "sales2026")
        a = ask(c, "ceo", "Ποιος εγκρίνει έκπτωση πάνω από 12%;")
        assert a["message_id"]
        r = c.post("/api/mirrors/ceo/persona-feedback", json={"rating": "faithful", "message_id": a["message_id"]}, headers=H)
        assert r.status_code == 200 and r.json()["ok"]
        used = r.json()["learned_from_traits"]
        if used:  # the answer relied on at least one of the CEO's traits: its weight is now higher
            from app.context import CURRENT_VIEWER
            token = CURRENT_VIEWER.set("sales")  # the CEO's Mirror as the Sales Manager sees it
            try:
                with as_person("ceo"):
                    rated = [t for sec in profile.SECTIONS for t in (profile.for_twin() or {}).get(sec, [])
                             if t.get("chat_signal")]
            finally:
                CURRENT_VIEWER.reset(token)
            assert rated and all(t["chat_signal"]["up"] >= 1 for t in rated)
        # one vote per user and answer: rating again replaces the vote instead of adding one
        c.post("/api/mirrors/ceo/persona-feedback", json={"rating": "uncharacteristic", "message_id": a["message_id"]}, headers=H)
        from app import learning
        assert sum(u + d for u, d in learning.signals().values()) == used
        # nobody can rate an answer that was given to someone else
        login(c, "finance_manager", "finance2026")
        assert c.post("/api/mirrors/ceo/persona-feedback", json={"rating": "faithful", "message_id": a["message_id"]},
                      headers=H).status_code == 404


def test_question_the_mirror_could_not_answer_reaches_its_owner_and_is_learned():
    with TestClient(app) as c:
        login(c, "sales_manager", "sales2026")
        q = "Ποιο είναι το budget της NexaTech για το 2031;"
        a = ask(c, "ceo", q)
        assert a["explain"]["unsure"]
        login(c, "ceo", "ceo2026")
        st = c.get("/api/self-test").json()
        assert q in [g["question"] for g in st["chat_learning"]["questions"]]
        # the owner answers it in the self-test: it becomes knowledge and leaves the queue
        tq = c.post("/api/self-test/question", json={"topic": "Γνώση της δουλειάς", "custom_question": q}, headers=H).json()
        ev = c.post("/api/self-test/answer", json={**tq, "user_answer": "Δεν έχει οριστεί ακόμα· θα το δούμε τον Ιανουάριο."},
                    headers=H).json()
        st = c.post(f"/api/self-test/events/{ev['event_id']}/feedback",
                    json={"feedback": "wrong", "correction": "Δεν έχει οριστεί ακόμα· το αποφασίζουμε τον Ιανουάριο 2031."},
                    headers=H).json()
        assert q not in [g["question"] for g in st["chat_learning"]["questions"]]
        assert st["chat_learning"]["questions_learned"] >= 1
        # undoing the correction puts the question back in the queue
        st = c.post(f"/api/self-test/events/{ev['event_id']}/undo", json={}, headers=H).json()
        assert q in [g["question"] for g in st["chat_learning"]["questions"]]


def test_owner_questions_and_boundaries_are_not_queued():
    with TestClient(app) as c:
        login(c, "ceo", "ceo2026")
        st = c.get("/api/self-test").json()
        before = len(st["chat_learning"]["questions"])
        login(c, "sales_manager", "sales2026")
        ask(c, "ceo", "Τι φάρμακα παίρνεις αυτή την περίοδο;")  # a boundary, never a gap to fill
        login(c, "ceo", "ceo2026")
        assert len(c.get("/api/self-test").json()["chat_learning"]["questions"]) == before
