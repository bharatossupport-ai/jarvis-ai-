"""Model providers: local Ollama and any OpenAI-compatible cloud API."""
import json
import requests
from storage.settings import get_secret


class ProviderError(Exception):
    pass


class OllamaProvider:
    name = "ollama"

    def __init__(self, url, model, timeout=120):
        self.url, self.model, self.timeout = url.rstrip("/"), model, timeout

    def status(self):
        try:
            r = requests.get(f"{self.url}/api/tags", timeout=3)
            models = [m["name"] for m in r.json().get("models", [])]
            return True, models
        except Exception as e:
            return False, str(e)

    def chat(self, messages, stream_cb=None):
        try:
            r = requests.post(f"{self.url}/api/chat", json={
                "model": self.model, "messages": messages, "stream": True},
                stream=True, timeout=self.timeout)
            r.raise_for_status()
        except requests.RequestException as e:
            raise ProviderError(f"Ollama unreachable at {self.url}: {e}. Is Ollama running?")
        out = []
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if "error" in chunk:
                raise ProviderError(chunk["error"])
            piece = chunk.get("message", {}).get("content", "")
            out.append(piece)
            if stream_cb and piece:
                stream_cb(piece)
            if chunk.get("done"):
                break
        return "".join(out)


class CloudProvider:
    """OpenAI-compatible /chat/completions (OpenAI, Groq, OpenRouter, Together...)."""
    name = "cloud"

    def __init__(self, base_url, model, timeout=120):
        self.base_url, self.model, self.timeout = base_url.rstrip("/"), model, timeout

    def status(self):
        return (bool(get_secret("cloud_api_key")), "API key set" if get_secret("cloud_api_key") else "No API key")

    def chat(self, messages, stream_cb=None):
        key = get_secret("cloud_api_key")
        if not key:
            raise ProviderError("No cloud API key saved. Add one in Settings.")
        try:
            r = requests.post(f"{self.base_url}/chat/completions",
                              headers={"Authorization": f"Bearer {key}"},
                              json={"model": self.model, "messages": messages},
                              timeout=self.timeout)
            r.raise_for_status()
        except requests.RequestException as e:
            raise ProviderError(f"Cloud provider error: {e}")
        text = r.json()["choices"][0]["message"]["content"]
        if stream_cb:
            stream_cb(text)
        return text


class ModelRouter:
    """Chooses the provider per request; records which model answered."""

    def __init__(self, settings):
        self.settings = settings

    def provider(self, override=None):
        s = self.settings
        which = override or s.get("provider")
        if which == "cloud":
            return CloudProvider(s.get("cloud_base_url"), s.get("cloud_model"), s.get("request_timeout"))
        return OllamaProvider(s.get("ollama_url"), s.get("ollama_model"), s.get("request_timeout"))

    def chat(self, messages, stream_cb=None, override=None):
        p = self.provider(override)
        return p.chat(messages, stream_cb), f"{p.name}:{p.model}"
