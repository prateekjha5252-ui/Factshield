# FactShield AI – External Fact-check API Integration

This update adds two external evidence lookups to the existing FactShield project:

1. **Google Fact Check Tools API** – searches for existing `ClaimReview` records. It displays the publisher, review title, textual rating, review date and original review URL. It does not generate a new fact-check verdict.
2. **Wikidata API** – searches proper-name-like entities mentioned in the submitted text and returns entity labels, descriptions and Wikidata links. Entity matches provide context only; they do not prove the sentence is true.

The existing heuristic audit remains in place. Its scores are screening indicators, not calibrated probabilities of truth.

## Configure Google Fact Check Tools API

1. Open Google Cloud Console: https://console.cloud.google.com/
2. Create/select a project and enable **Fact Check Tools API**.
3. Create an API key. Restrict it to the Fact Check Tools API where possible.
4. Set the key as a backend environment variable named `GOOGLE_FACT_CHECK_API_KEY`.
   - FastAPI: copy `backend/.env.example` as a reference and configure the variable in the hosting provider's environment settings.
   - Streamlit: add `GOOGLE_FACT_CHECK_API_KEY = "YOUR_KEY"` in Streamlit Community Cloud **App settings → Secrets**, or locally in `.streamlit/secrets.toml`.
5. Never commit the real key, put it in GitHub Pages, or prefix it with `REACT_APP_` / `VITE_`.

Google API documentation: https://developers.google.com/fact-check/tools/api
Wikidata API documentation: https://www.wikidata.org/w/api.php

## Run the Streamlit application

From `frontend/VeristasAI`:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Run the FastAPI backend

From `backend`:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to test `POST /analyze`.

The `/analyze` response now includes an `external_checks` object with `google_fact_check` and `wikidata` results. If the Google key is not configured, local analysis still works and Google lookup reports `not_configured`.

## Important deployment note

GitHub Pages hosts static frontend files only; it cannot safely store API secrets or run the Python backend. Deploy the FastAPI/Streamlit backend separately (for example, on a Python-capable host), then configure the frontend to call that backend. Do not assume the GitHub Pages link itself has the new live API integration until that backend is deployed and connected.

## Accuracy and limitations

- A Google search with no returned ClaimReview is **not** evidence that a claim is true.
- Ratings belong to the original publisher; FactShield should display them as reported ratings, not rewrite them as its own verdict.
- Wikidata search results are entity references, not claim-level validation. Dates, offices, and locations require a specific property-level comparison before any mismatch can be asserted.
- The API calls use short timeouts and fail independently so an external service outage does not disable the existing audit.
