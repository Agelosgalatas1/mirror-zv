import os
import sys
import tempfile
from pathlib import Path

# Isolated, offline, deterministic test environment (must be set before importing the app).
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="mirror-test-")
os.environ["LLM_PROVIDER"] = "offline"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["ELEVENLABS_API_KEY"] = ""  # never call paid voice / avatar services from tests
os.environ["SIMLI_API_KEY"] = ""
os.environ["STATIC_DIR"] = str(Path(os.environ["DATA_DIR"]) / "no-static")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import pytest


@pytest.fixture
def published_company_rules():
    """Explicit human approvals for the legacy demo behaviour tests, never production seeding."""
    from app.main import bootstrap
    from app import sharing
    from app.context import CURRENT_VIEWER
    bootstrap()
    for person in ('ceo', 'sales', 'finance'):
        token = CURRENT_VIEWER.set(person)
        try:
            for rule in sharing.review_rules(person):
                sharing.set_publication(person, rule['id'], True, rule['content_hash'])
        finally:
            CURRENT_VIEWER.reset(token)
