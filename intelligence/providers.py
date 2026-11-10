"""Model providers: local Ollama and any OpenAI-compatible cloud API."""
import json
import os
import threading
from pathlib import Path
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


class EmbeddedProvider:
    """Built-in AI: llama.cpp running inside JARVIS with the bundled Hermes model.
    Needs no Ollama, no API key and no internet."""
    name = "embedded"
    _llm, _lock, _loaded_path = None, threading.Lock(), None

    def __init__(self, model_path, n_ctx=4096):
        self.model_path, self.n_ctx = str(model_path), n_ctx
        self.model = Path(model_path).stem

    def status(self):
        if Path(self.model_path).exists():
            return True, ["built-in"]
        return False, f"Built-in model missing: {self.model_path}"

    def _load(self):
        if EmbeddedProvider._llm is None or EmbeddedProvider._loaded_path != self.model_path:
            from llama_cpp import Llama
            EmbeddedProvider._llm = Llama(model_path=self.model_path, n_ctx=self.n_ctx,
                                          n_threads=max(1, (os.cpu_count() or 4)), verbose=False)
            EmbeddedProvider._loaded_path = self.model_path
        return EmbeddedProvider._llm

    def chat(self, messages, stream_cb=None):
        if not Path(self.model_path).exists():
            raise ProviderError(f"Built-in model not found at {self.model_path}")
        with EmbeddedProvider._lock:  # one generation at a time keeps RAM use predictable
            try:
                llm = self._load()
                out = []
                for chunk in llm.create_chat_completion(messages=messages, stream=True,
                                                        max_tokens=1024, temperature=0.6):
                    piece = chunk["choices"][0]["delta"].get("content") or ""
                    out.append(piece)
                    if stream_cb and piece:
                        stream_cb(piece)
                return "".join(out)
            except Exception as e:
                raise ProviderError(f"Built-in AI error: {e}")


def builtin_model_path(settings):
    custom = settings.get("embedded_model_path")
    if custom:
        return Path(custom)
    from storage.paths import resource, data_dir
    for base in (resource("models"), data_dir() / "models"):
        hits = sorted(base.glob("*.gguf")) if base.exists() else []
        if hits:
            return hits[0]
    return resource("models") / "Hermes-3-Llama-3.2-3B.Q4_K_M.gguf"


class ModelRouter:
    """Chooses the provider per request; records which model answered."""

    def __init__(self, settings):
        self.settings = settings

    def provider(self, override=None):
        s = self.settings
        which = override or s.get("provider")
        if which == "embedded":
            return EmbeddedProvider(builtin_model_path(s), int(s.get("embedded_ctx") or 4096))
        if which == "cloud":
            return CloudProvider(s.get("cloud_base_url"), s.get("cloud_model"), s.get("request_timeout"))
        return OllamaProvider(s.get("ollama_url"), s.get("ollama_model"), s.get("request_timeout"))

    def chat(self, messages, stream_cb=None, override=None):
        p = self.provider(override)
        return p.chat(messages, stream_cb), f"{p.name}:{p.model}"
