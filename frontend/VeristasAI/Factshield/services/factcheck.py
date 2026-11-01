"""External evidence lookups for FactShield AI.

Google Fact Check Tools returns existing ClaimReview records; it does not
create a new verdict. Wikidata results provide entity context only and must
not be presented as proof that a sentence is true.
"""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GOOGLE_ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
WIKIDATA_ENDPOINT = "https://www.wikidata.org/w/api.php"
TIMEOUT_SECONDS = 7
MAX_CLAIMS = 5
MAX_ENTITIES = 5

# Conservative extraction: only proper-name-like phrases are searched.
_ENTITY_RE = re.compile(r"\b(?:[A-Z][a-z][\w'-]*(?:\s+[A-Z][a-z][\w'-]*){0,3})\b")
_ENTITY_STOPWORDS = {
    "The", "This", "That", "These", "Those", "According", "Scientists",
    "Researchers", "Experts", "Studies", "Research", "People", "Everyone",
    "However", "Therefore", "Meanwhile", "Breaking", "Factshield",
}


def _get_json(url: str, params: dict) -> dict:
    request_url = url + "?" + urlencode(params)
    request = Request(
        request_url,
        headers={"User-Agent": "FactShieldAI/1.0 (educational fact-checking prototype)"},
    )
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _google_claim_reviews(claim: str, api_key: str) -> list[dict]:
    data = _get_json(
        GOOGLE_ENDPOINT,
        {"query": claim[:500], "key": api_key, "pageSize": 3, "languageCode": "en"},
    )
    reviews = []
    for item in data.get("claims", []):
        for review in item.get("claimReview", []):
            publisher = review.get("publisher") or {}
            reviews.append({
                "claim_text": item.get("text", ""),
                "claimant": item.get("claimant", ""),
                "publisher": publisher.get("name", "Unknown publisher"),
                "title": review.get("title", "Fact-check review"),
                "rating": review.get("textualRating", "Rating not supplied"),
                "review_date": review.get("reviewDate", ""),
                "url": review.get("url", ""),
                "language_code": review.get("languageCode", ""),
            })
    return reviews


def _candidate_entities(text: str) -> list[str]:
    candidates = []
    for match in _ENTITY_RE.findall(text):
        name = match.strip()
        if name in _ENTITY_STOPWORDS or len(name) < 3:
            continue
        # Skip sentence-initial generic words while retaining country/person names.
        if name.split()[0] in _ENTITY_STOPWORDS:
            continue
        if name not in candidates:
            candidates.append(name)
        if len(candidates) >= MAX_ENTITIES:
            break
    return candidates


def _wikidata_entities(text: str) -> list[dict]:
    entities = []
    for name in _candidate_entities(text):
        data = _get_json(WIKIDATA_ENDPOINT, {
            "action": "wbsearchentities", "search": name, "language": "en",
            "format": "json", "limit": 2,
        })
        for item in data.get("search", [])[:2]:
            entity_id = item.get("id", "")
            if not entity_id:
                continue
            entities.append({
                "searched_name": name,
                "id": entity_id,
                "label": item.get("label", ""),
                "description": item.get("description", ""),
                "url": item.get("concepturi", f"https://www.wikidata.org/wiki/{entity_id}"),
            })
    return entities


def run_external_checks(text: str, claims: list[dict] | None = None, api_key: str | None = None) -> dict:
    """Look up existing Google ClaimReview records and Wikidata entities.

    Failures are isolated per provider so the normal heuristic audit still works.
    """
    api_key = api_key or os.getenv("GOOGLE_FACT_CHECK_API_KEY", "").strip()
    claim_texts = [c.get("claim_text", "") for c in (claims or []) if c.get("claim_text")]
    if not claim_texts and text.strip():
        claim_texts = [text.strip()]

    google_reviews: list[dict] = []
    google_status = "not_configured" if not api_key else "no_matches"
    google_error = ""
    if api_key:
        seen_urls = set()
        try:
            for claim in claim_texts[:MAX_CLAIMS]:
                try:
                    for review in _google_claim_reviews(claim, api_key):
                        if review["url"] and review["url"] not in seen_urls:
                            seen_urls.add(review["url"])
                            google_reviews.append(review)
                except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                    google_error = str(exc)[:240]
            google_status = "matches_found" if google_reviews else ("error" if google_error else "no_matches")
        except Exception as exc:  # keep external lookups from breaking local analysis
            google_status, google_error = "error", str(exc)[:240]

    wikidata_entities: list[dict] = []
    wikidata_status = "not_checked"
    wikidata_error = ""
    if text.strip():
        try:
            wikidata_entities = _wikidata_entities(text[:2000])
            wikidata_status = "entities_found" if wikidata_entities else "no_entities_found"
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            wikidata_status, wikidata_error = "error", str(exc)[:240]
        except Exception as exc:
            wikidata_status, wikidata_error = "error", str(exc)[:240]

    return {
        "google_fact_check": {
            "status": google_status,
            "message": (
                "Existing ClaimReview records found. Read each publisher's review and rating."
                if google_reviews else
                "No matching published fact-check was returned. This does not mean the claim is true."
                if google_status == "no_matches" else
                "Set GOOGLE_FACT_CHECK_API_KEY on the backend to enable Google fact-check lookups."
                if google_status == "not_configured" else
                "Google Fact Check lookup could not be completed. The local audit is still available."
            ),
            "reviews": google_reviews,
            "error": google_error,
        },
        "wikidata": {
            "status": wikidata_status,
            "message": "Entity references are context only; they do not verify the claim itself.",
            "entities": wikidata_entities,
            "error": wikidata_error,
        },
    }
