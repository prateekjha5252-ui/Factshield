# FactShield AI – Enhanced build

## Added
- Runtime LLM provider selector: Groq, Google Gemini, OpenAI, Anthropic, and local Ollama.
- Editable model ID and per-provider API key entry in the Streamlit Provider / Token Settings panel.
- Browser-native `Intl.Segmenter` sentence segmentation helper for the React client, with a compatibility fallback.
- Color-coded inline audit heatmap with numbered links to visible claim findings.
- LLM-powered objective rewrite with `[CITATION NEEDED]` markers.
- Side-by-side model audit comparison with model-estimated hallucination-risk and emotional-bias scores.
- JSON, Markdown, and PDF report downloads.
- SVG trust badge and embeddable HTML badge download.
- Existing Google Fact Check Tools and Wikidata lookups retained.

## Validation performed
- Python syntax compilation passed for the updated Streamlit app, LLM provider module, FastAPI backend, and analyzer.
- Analyzer smoke test passed with `Dr. Smith` and `3.14%` in the same sample; it split into the expected two claims.
- Provider configuration import smoke test passed.

## Not performed / requirements
- Live calls to Groq, Gemini, OpenAI, Anthropic, Ollama, Google Fact Check, or Wikidata were not run; API credentials and/or a running Ollama service are required.
- Streamlit is not installed in the build environment, so a full interactive Streamlit browser test was not run. Install project requirements before launch.
- GitHub Pages has not been redeployed. This ZIP updates source code only; publishing requires a push to the connected repository and a separately hosted Python runtime for the Streamlit/backend functionality.
