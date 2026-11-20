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
