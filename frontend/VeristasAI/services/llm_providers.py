"""Multi-provider LLM helpers. Keys are supplied at runtime and never persisted."""
from __future__ import annotations
import json
import urllib.request
import urllib.error

PROVIDERS = {
    "Groq": {"model": "llama-3.3-70b-versatile", "kind": "openai", "url": "https://api.groq.com/openai/v1/chat/completions"},
    "Google Gemini": {"model": "gemini-1.5-flash", "kind": "gemini", "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"},
    "OpenAI": {"model": "gpt-4o-mini", "kind": "openai", "url": "https://api.openai.com/v1/chat/completions"},
    "Anthropic": {"model": "claude-3-5-haiku-latest", "kind": "anthropic", "url": "https://api.anthropic.com/v1/messages"},
    "Ollama (local)": {"model": "llama3.2", "kind": "ollama", "url": "http://localhost:11434/api/chat"},
}

def _post(url, payload, headers=None, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json", **(headers or {})}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"Provider returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach provider: {exc.reason}") from exc

def generate(provider, prompt, api_key="", model=None, base_url=None, system="You are a careful, evidence-conscious text auditor. Do not invent sources or facts."):
    cfg = PROVIDERS[provider]
    model = (model or cfg["model"]).strip()
    url = (base_url or cfg["url"]).strip()
    if cfg["kind"] == "ollama":
        data = _post(url, {"model": model, "stream": False, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
        return data.get("message", {}).get("content", "").strip()
    if not api_key:
        raise RuntimeError(f"Add an API key for {provider} in Provider Settings.")
    if cfg["kind"] == "openai":
        data = _post(url, {"model": model, "temperature": 0.2, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}, {"Authorization": f"Bearer {api_key}"})
        return data["choices"][0]["message"]["content"].strip()
    if cfg["kind"] == "gemini":
        data = _post(url.format(model=model) + "?key=" + api_key, {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}})
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
    if cfg["kind"] == "anthropic":
        data = _post(url, {"model": model, "max_tokens": 1800, "temperature": 0.2, "system": system, "messages": [{"role": "user", "content": prompt}]}, {"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        return "".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text").strip()
    raise RuntimeError("Unsupported provider.")

def neutralize_prompt(text):
    return ("Rewrite the text in objective, measured language. Preserve the author's core meaning and all checkable details. "
            "Remove sensationalism and coercive wording; qualify unsupported absolutes only when justified. Do not invent facts or citations. "
            "Insert [CITATION NEEDED] after claims needing sources, then add a short 'Changes made' list.\n\nTEXT:\n" + text[:12000])

def audit_prompt(text):
    return ("Audit this text for factual claims needing sources, possible hallucinations or unsupported absolutes, emotional manipulation, "
            "and one-sided/bias signals. For comparison only, provide an estimated hallucination-risk score (0-100) and emotional-bias score (0-100), "
            "with brief evidence and limitations; clearly label these as model judgments, not measured probabilities. Do not claim to verify facts without evidence or invent citations.\n\nTEXT:\n" + text[:12000])
