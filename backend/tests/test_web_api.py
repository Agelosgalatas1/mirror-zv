"""The API of the MIRROR web app: cookie sessions, upward-only access, conversations, self-test."""
from fastapi.testclient import TestClient

from app.main import app

H = {"X-Mirror-Request": "1"}


def web_login(c: TestClient, username: str, password: str) -> dict:
    r = c.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    assert "mirror_session" in r.cookies
    return r.json()


def test_cookie_session_and_csrf_header():
    with TestClient(app) as c:
        assert c.get("/api/session").status_code == 401
        s = web_login(c, "sales_manager", "sales2026")
        assert s["user"]["role_name"] == "sales_manager" and s["user"]["department"] == "sales"
        assert [m["id"] for m in s["mirrors"]] == ["ceo"]           # never their own, never sideways
        assert c.get("/api/session").json()["user"]["employee_id"] == "sales"
        # a cookie-authenticated write without the app's header is rejected
        assert c.post("/api/mirrors/ceo/conversations", json={"title": "x"}).status_code == 403
        assert c.post("/api/mirrors/ceo/conversations", json={"title": "x"}, headers=H).status_code == 200
        assert c.post("/api/logout", headers=H).status_code == 200
        assert c.get("/api/session").status_code == 401


def test_hierarchy_explains_access():
    with TestClient(app) as c:
        web_login(c, "finance_manager", "finance2026")
        rows = {p["id"]: p for p in c.get("/api/hierarchy").json()}
        assert rows["finance"]["is_me"] and rows["finance"]["reason"] == "self"
        assert rows["ceo"]["can_chat"] and rows["ceo"]["relation"] == "manager"
        assert not rows["sales"]["can_chat"] and rows["sales"]["reason"] == "other_line"
        web_login(c, "ceo", "ceo2026")
        rows = {p["id"]: p for p in c.get("/api/hierarchy").json()}
        assert rows["sales"]["reason"] == "below" and not any(p["can_chat"] for p in rows.values())


def test_conversation_flow_and_access_errors():
    with TestClient(app) as c:
        web_login(c, "sales_manager", "sales2026")
        bad = c.post("/api/mirrors/finance/ask", json={"question": "Γεια"}, headers=H)
        assert bad.status_code == 403 and bad.json()["code"] == "mirror_access"
        t = c.post("/api/mirrors/ceo/conversations", json={"title": "Εγκρίσεις"}, headers=H).json()
        cid = t["conversation_id"]
        a = c.post("/api/mirrors/ceo/ask", json={"question": "Ποιος εγκρίνει έκπτωση πάνω από 12%;",
                                                  "conversation_id": cid}, headers=H).json()
        assert a["answer"]
        why = c.post("/api/mirrors/ceo/ask", json={"question": "γιατί;", "conversation_id": cid}, headers=H).json()
        assert why["answer"]
        turns = c.get(f"/api/mirrors/ceo/conversations/{cid}").json()
        assert [t["question"] for t in turns] == ["Ποιος εγκρίνει έκπτωση πάνω από 12%;", "γιατί;"]
        threads = c.get("/api/mirrors/ceo/conversations").json()
        assert threads[0]["turns"] == 2 and threads[0]["last_question"] == "γιατί;"
        r = c.post(f"/api/mirrors/ceo/conversations/{cid}/rename", json={"title": "Όρια εκπτώσεων"}, headers=H).json()
        assert r["title"] == "Όρια εκπτώσεων"
        assert c.post("/api/mirrors/ceo/persona-feedback", json={"rating": "faithful"}, headers=H).json()["ok"]
        # another user cannot read this conversation
        web_login(c, "finance_manager", "finance2026")
        assert c.get(f"/api/mirrors/ceo/conversations/{cid}").status_code == 404
        web_login(c, "sales_manager", "sales2026")
        assert c.post(f"/api/mirrors/ceo/conversations/{cid}/delete", json={}, headers=H).json()["deleted"] == 1


def test_avatar_caps_and_voice_turns_are_private():
    with TestClient(app) as c:
        web_login(c, "sales_manager", "sales2026")
        caps = c.get("/api/mirrors/ceo/avatar").json()
        assert caps["avatar_provider"] == "simli" and caps["face_name"] == "Kate"
        assert c.get("/api/voice/" + "0" * 32).status_code == 404


def test_self_test_learns_from_a_correction_and_can_undo():
    with TestClient(app) as c:
        web_login(c, "finance_manager", "finance2026")
        st = c.get("/api/self-test").json()
        assert st["mirror"]["id"] == "finance" and st["topics"]
        topic = st["next_topic"]
        q = c.post("/api/self-test/question", json={"topic": topic}, headers=H).json()
        assert q["question"] and q["question_source"].startswith("trait:")
        ans = c.post("/api/self-test/answer", json={**q, "user_answer": "Θα ζητούσα πρώτα τα στοιχεία."},
                     headers=H).json()
        assert ans["twin_answer"]
        snap = c.post(f"/api/self-test/events/{ans['event_id']}/feedback",
                      json={"feedback": "wrong", "correction": "Ζητώ πάντα ιστορικό πληρωμών 12 μηνών."},
                      headers=H).json()
        assert snap["events"][0]["feedback"] == "wrong"
        from app import profile
        from app.context import as_person
        with as_person("finance"):
            assert any("12 μηνών" in (t.get("text") or "") for t in profile.current()["knowledge"])
        c.post(f"/api/self-test/events/{ans['event_id']}/undo", json={}, headers=H)
        with as_person("finance"):
            assert not any("12 μηνών" in (t.get("text") or "") for t in profile.current()["knowledge"])


def test_employees_have_no_ai_and_talk_upwards_only():
    with TestClient(app) as c:
        s = web_login(c, "sales_employee", "employee2026")
        assert s["user"]["manager_id"] == "sales"
        assert [m["id"] for m in s["mirrors"]] == ["sales", "ceo"]          # their manager first, then the CEO
        rows = {p["id"]: p for p in c.get("/api/hierarchy").json()}
        assert rows["sales_employee"]["is_me"] and rows["sales_employee"]["mirror_id"] is None
        assert rows["sales"]["relation"] == "manager" and rows["ceo"]["relation"] == "above"
        assert not rows["finance"]["can_chat"] and rows["finance_employee"]["reason"] == "no_ai"
        assert c.post("/api/mirrors/finance/ask", json={"question": "Γεια"}, headers=H).status_code == 403
        assert c.post("/api/mirrors/sales/ask", json={"question": "Ποιος εγκρίνει έκπτωση 8%;"}, headers=H).json()["answer"]
        assert c.get("/api/self-test").status_code == 409
        # a manager sees the employee below, without an AI to talk to
        web_login(c, "finance_manager", "finance2026")
        rows = {p["id"]: p for p in c.get("/api/hierarchy").json()}
        assert rows["finance_employee"]["reason"] == "no_ai" and not rows["finance_employee"]["can_chat"]
