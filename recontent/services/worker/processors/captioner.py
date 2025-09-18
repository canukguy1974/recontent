from services.worker.ai.mock_client import MockAIClient
from services.worker.ai.vertex_client import VertexAIClient
from packages.common.config import MOCK_AI

_ai = MockAIClient() if MOCK_AI else VertexAIClient()

def run(brief: str, staged: bool) -> str:
    return _ai.caption(brief, staged)
