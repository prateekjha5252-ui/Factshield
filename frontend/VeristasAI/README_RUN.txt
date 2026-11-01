FACTSHIELD AI - UPDATED RUN GUIDE

1) Install Python dependencies:
   pip install -r requirements.txt

2) Run the Streamlit application:
   streamlit run app.py

3) Open the sidebar's "Provider / Token Settings" panel:
   - Choose Groq, Google Gemini, OpenAI, Anthropic, or Ollama (local).
   - Set/adjust the model ID to one currently supported by that provider.
   - Enter the provider API key for this Streamlit session (not required for Ollama).
   - For Ollama, install/run Ollama locally and pull a model, e.g. `ollama pull llama3.2`.
   - API keys are not stored in this project or written into source files.

4) Run an audit. The dashboard now includes:
   - Inline color-coded claim heatmap and numbered anchors to claim findings.
   - Rewrite with Objective Phrasing (uses the selected provider).
   - Side-by-side LLM audit comparison (each selected provider needs its own key).
   - JSON, Markdown and PDF report downloads.
   - SVG trust badge and embeddable HTML download.

5) Browser-native sentence segmentation:
   - `frontend/src/utils/sentenceSegmenter.js` uses Intl.Segmenter when available.
   - The Streamlit analysis pipeline remains server-side Python and has its own abbreviation-aware splitter.
   - Use the JS helper when the React client is connected to the analysis API.

IMPORTANT NOTES
- The model provider selector is an LLM assistance feature, not a truth oracle.
- Model comparison scores are model judgments, not measured probabilities or objective benchmark results.
- Google Fact Check results are previously published ClaimReview records; no match does not mean true.
- Wikidata entity matches provide context, not proof that a complete sentence is true.
- Trust scores are heuristic screening indicators, not probabilities of truth.
- Provider model names and availability change. If a listed default model is retired, update the editable Model ID to a currently supported one.
- Never commit real API keys to GitHub. For production, put keys in deployment secrets and call providers only from a secured backend.

DEPLOYMENT
The GitHub Pages URL is a static frontend and cannot run Streamlit or keep API keys secure by itself. Deploy this Python Streamlit app to Streamlit Community Cloud or another Python host. If using the React frontend, deploy a FastAPI backend separately and configure CORS for your exact frontend origin.
