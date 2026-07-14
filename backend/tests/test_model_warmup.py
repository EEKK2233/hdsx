from types import SimpleNamespace

from app.integrations.ollama import OllamaClient


def test_ollama_keep_alive_accepts_numeric_and_duration_config():
    client = OllamaClient()
    client.settings = SimpleNamespace(ollama_keep_alive="-1")
    assert client.keep_alive == -1
    client.settings = SimpleNamespace(ollama_keep_alive="30m")
    assert client.keep_alive == "30m"
