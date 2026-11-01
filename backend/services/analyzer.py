"""Transparent, rule-based text screening for FactShield AI (v2, logic-corrected).

This is a heuristic screening tool, not a full fact-checker or lie detector.
It combines:
  1. A small built-in fact layer (well-known false claims, capitals, boiling point)
     so obviously wrong statements are marked "Contradicted" with a very low score.
  2. Language-signal rules (sweeping claims, emotional/biased wording,
     manipulation patterns, unsourced statistics).
Anything outside the built-in fact layer is "unverified", never "true".
"""
import re

# --------------------------------------------------------------------------
# Lexicons
# --------------------------------------------------------------------------
# Strong absolutes are sweeping on their own; weak ones only matter with other signals.
STRONG_ABSOLUTE = {
    "everyone", "nobody", "impossible", "guaranteed", "undeniably",
    "unquestionably", "flawless", "infallible", "irrefutable", "foolproof",
}
WEAK_ABSOLUTE = {"always", "never", "none", "proven", "definitely", "perfect", "totally", "absolutely"}
ABSOLUTE_PHRASES = [
    r"\beveryone knows\b", r"\bno one\b", r"\ball (?:\w+ ){0,2}(?:are|were|is|will|must|always)\b",
    r"\bevery (?:single )?(?:one|person|man|woman|child|time)\b",
    r"\b100\s?%\s*(?:sure|certain|guaranteed|safe|accurate|effective|true|proven|free|cure)",
]
# "not always", "not everyone", "almost all" ... are hedges, not sweeping claims.
HEDGE_PATTERN = re.compile(
    r"\b(?:not|n't|hardly|almost|nearly|rarely|seldom|not necessarily)\s+(?:\w+\s+)?"
    r"(?:always|never|everyone|all|every\w*|none|nobody)\b", re.I)

EMOTIONAL_TERMS = {
    "shocking", "outrageous", "horrifying", "unbelievable", "terrifying",
    "devastating", "explosive", "scandalous", "alarming", "catastrophic",
    "disastrous", "urgent", "crisis", "danger", "miracle", "secret",
    "exposed", "conspiracy", "warning", "breaking", "bombshell",
}
BIAS_TERMS = {
    "obviously", "clearly", "naturally", "merely", "radical",
    "extreme", "agenda", "propaganda", "brainwashed", "naive", "foolish",
    "ridiculous", "idiotic", "stupid", "sheeple", "so-called",
}
MANIPULATION_PATTERNS = {
    "Guilt-tripping": [
        r"if you (?:really )?loved me", r"after everything i've done",
        r"how could you do this to me", r"you owe me",
        r"you should feel guilty", r"this is how you repay me",
    ],
    "Emotional blackmail / threat": [
        r"if you (?:leave|reject|disobey)\b", r"you'll regret it",
        r"it will be your fault", r"i will (?:leave|abandon|expose|ruin)\b",
        r"i'll (?:leave|abandon|expose|ruin)\b",
    ],
    "Isolation / control": [
        r"nobody else (?:will|can) (?:ever )?love you", r"only i understand you",
        r"don't talk to anyone", r"you are not allowed to (?:see|talk|speak|leave|go|contact|meet)\b",
        r"you're not allowed to (?:see|talk|speak|leave|go|contact|meet)\b",
        r"you must obey", r"keep this (?:a )?secret",
    ],
    "Gaslighting-like language": [
        r"you're imagining things", r"you are imagining things", r"that never happened",
        r"you're too sensitive", r"you are too sensitive", r"you're making things up",
        r"you are making things up", r"you're (?:crazy|insane|paranoid)", r"i never said that",
    ],
    "Pressure / coercion": [
        r"if you don't\b[^.!?]{0,60}\b(?:or else|then i|i'll|i will|you'll|you will)\b",
        r"do this or else", r"prove (?:that )?you care", r"you have no choice",
    ],
}
STAT_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s?%|\b\d{1,3}(?:,\d{3})+\b|"
    r"\b\d+(?:\.\d+)?\s*(?:million|billion|trillion|thousand)\b|"
    r"\b(?:study|studies|research|survey|poll|data|statistics?|scientists|experts)\s+"
    r"(?:show(?:s|ed)?|found|reveal(?:s|ed)?|indicate(?:s|d)?|suggest(?:s|ed)?|say|said|prove[sd]?)",
    re.I,
)
CITATION_PATTERN = re.compile(
    r"\b(?:according to|sources?:|cited by|published in|doi:|arxiv:|pubmed:|"
    r"reported by|per the)\b|https?://|www\.", re.I)

# --------------------------------------------------------------------------
# Built-in fact layer (small on purpose; everything else stays "unverified")
# --------------------------------------------------------------------------
KNOWN_FALSE = [
    (r"\b(?:the )?(?:earth|world)\s+is\s+flat\b", "The Earth is not flat; it is an oblate spheroid."),
    (r"\bvaccines?\s+(?:cause|causes|caused|causing)\s+autism\b", "Large studies have found no link between vaccines and autism."),
    (r"\b5g\b[^.!?]{0,30}\b(?:spread|spreads|cause|causes|caused)\b[^.!?]{0,20}\b(?:covid|coronavirus)", "5G does not spread or cause COVID-19; viruses do not travel on radio waves."),
    (r"\bmoon\s+landings?\s+(?:was|were|is|are)\s+(?:fake|faked|staged|a hoax)\b", "The Apollo Moon landings are well documented and independently verified."),
    (r"\bhumans?\s+(?:only\s+)?use\s+(?:only\s+)?(?:10|ten)\s?%\s+of\s+(?:their|the)\s+brains?\b", "The '10% of the brain' claim is a myth; we use virtually all of it."),
    (r"\bthe sun\s+(?:orbits|revolves around)\s+the earth\b", "The Earth orbits the Sun."),
    (r"\bclimate change\s+is\s+(?:a\s+)?(?:hoax|fake|a lie)\b", "Climate change is supported by overwhelming scientific evidence."),
    (r"\b(?:the )?(?:sun|moon|earth)\s+is\s+(?:made of|made out of)\s+(?:cheese|ice cream)\b", "This is false."),
]
# Words that mean the sentence is *discussing* a claim (e.g. debunking it), not asserting it.
DEBUNK_CONTEXT = re.compile(
    r"\b(?:myth|myths|debunk\w*|false|untrue|hoax|misinformation|disinformation|disproven|"
    r"no evidence|not true|incorrect|wrong|conspiracy theor\w*|claim(?:s|ed)? that|people (?:say|believe))\b|"
    r"\b(?:do|does|did|can|could|will|would)\s+not\b|\b(?:don't|doesn't|didn't|can't|won't|isn't|aren't)\b", re.I)

CAPITALS = {
    "france": "paris", "germany": "berlin", "italy": "rome", "spain": "madrid",
    "india": "new delhi", "japan": "tokyo", "china": "beijing", "russia": "moscow",
    "canada": "ottawa", "australia": "canberra", "brazil": "brasilia", "egypt": "cairo",
    "united kingdom": "london", "uk": "london", "united states": "washington",
    "usa": "washington", "mexico": "mexico city", "pakistan": "islamabad",
    "bangladesh": "dhaka", "nepal": "kathmandu", "sri lanka": "colombo",
    "argentina": "buenos aires", "turkey": "ankara", "south africa": "pretoria",
    "nigeria": "abuja", "kenya": "nairobi", "indonesia": "jakarta", "thailand": "bangkok",
    "south korea": "seoul", "portugal": "lisbon", "greece": "athens", "norway": "oslo",
    "sweden": "stockholm", "poland": "warsaw", "ireland": "dublin", "switzerland": "bern",
}
CAPITAL_PATTERN = re.compile(r"\bthe capital (?:city )?of ([a-z ]+?) is ([a-z ]+?)\s*[.!?]?$", re.I)
BOIL_PATTERN = re.compile(r"\bwater boils at (\d+(?:\.\d+)?)\s*(?:degrees?|°)?\s*(c\b|celsius|f\b|fahrenheit)", re.I)

# Common abbreviations whose period must not end a sentence.
_ABBREV = re.compile(
    r"\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|vs|etc|e\.g|i\.e|No|Inc|Ltd|U\.S|U\.K|U\.N|a\.m|p\.m)\.", re.I)
_PLACEHOLDER = "\u2024"  # one-dot leader; looks like '.', never matches '.'


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _normalise(text: str) -> str:
    return (text.replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201c", '"').replace("\u201d", '"'))


def _matches(patterns, text):
    return [cat for cat, exprs in patterns.items() if any(re.search(e, text, re.I) for e in exprs)]


def _split_claims(text):
    """Sentence-level split that survives 'Dr.', 'U.S.', initials and decimals."""
    protected = _ABBREV.sub(lambda m: m.group(0).replace(".", _PLACEHOLDER), text)
    protected = re.sub(r"\b([A-Z])\.(?=\s?[A-Z])", lambda m: m.group(1) + _PLACEHOLDER, protected)
    parts = re.split(r"(?<=[.!?])\s+|\n+", protected.strip())
    out = [p.replace(_PLACEHOLDER, ".").strip() for p in parts if p.strip()]
    return out or ([text.strip()] if text.strip() else [])


def _absolute_level(claim_lower, words):
    """Return 'strong', 'weak' or None, ignoring hedged phrases like 'not always'."""
    scrubbed = HEDGE_PATTERN.sub(" ", claim_lower)
    sw = set(re.findall(r"[a-z']+", scrubbed))
    if sw & STRONG_ABSOLUTE or any(re.search(p, scrubbed) for p in ABSOLUTE_PHRASES):
        return "strong"
    if sw & WEAK_ABSOLUTE:
        return "weak"
    return None


def _fact_check(claim):
    """Return ('contradicted'|'matches'|None, explanation)."""
    lower = claim.lower().strip()
    debunk = bool(DEBUNK_CONTEXT.search(lower))
    for expr, why in KNOWN_FALSE:
        if re.search(expr, lower) and not debunk:
            return "contradicted", why
    m = CAPITAL_PATTERN.search(lower)
    if m:
        country, city = m.group(1).strip(), m.group(2).strip()
        if country in CAPITALS:
            if CAPITALS[country] == city:
                return "matches", f"Matches built-in fact: capital of {country.title()} is {city.title()}."
            return "contradicted", f"The capital of {country.title()} is {CAPITALS[country].title()}, not {city.title()}."
    m = BOIL_PATTERN.search(lower)
    at_altitude = any(w in lower for w in ("altitude", "mountain", "pressure", "everest", "feet above"))
    if m and not at_altitude:
        val, unit = float(m.group(1)), m.group(2)[0]
        target = 100.0 if unit == "c" else 212.0
        if abs(val - target) < 0.5:
            return "matches", "Matches the boiling point of water at sea level."
        return "contradicted", f"Water boils at {'100 C' if unit == 'c' else '212 F'} at sea level."
    return None, ""


# --------------------------------------------------------------------------
# Main entry
# --------------------------------------------------------------------------
def analyze_text(text: str) -> dict:
    text = _normalise((text or "").strip())
    if not text:
        return {
            "overall_trust_score": 0.0,
            "summary": "No text provided for analysis.",
            "claims": [],
            "metrics": {
                "factual_integrity_score": 0.0, "certainty_score": 0.0,
                "hallucination_count": 0, "contradicted_count": 0,
                "bias_detected": False, "bias_score": 0.0,
                "emotional_manipulation_score": 0.0,
                "emotional_manipulation_detected": False,
                "manipulation_types": [], "unverified_stats_count": 0, "claim_count": 0,
            },
            "limitations": "No text was provided.",
        }

    claims, confidences = [], []
    emotional_hits = bias_hits = unverified_stats = 0
    flagged = needs_review = contradicted = matched = 0
    manip_claims = 0
    all_manip = set()

    for idx, claim in enumerate(_split_claims(text), 1):
        lower = claim.lower()
        words = set(re.findall(r"[a-z'-]+", lower))
        absolute = _absolute_level(lower, words)
        emotional = sorted(words & EMOTIONAL_TERMS)
        bias = sorted(words & BIAS_TERMS)
        shouting = len(re.findall(r"!{2,}", claim)) + (1 if re.search(r"\b[A-Z]{4,}\b.*\b[A-Z]{4,}\b", claim) else 0)
        manip = _matches(MANIPULATION_PATTERNS, claim)
        has_stat = bool(STAT_PATTERN.search(claim))
        has_source = bool(CITATION_PATTERN.search(claim))
        fact_state, fact_note = _fact_check(claim)

        emotional_hits += len(emotional) + shouting
        bias_hits += len(bias)
        if manip:
            manip_claims += 1
        all_manip.update(manip)

        # "Review confidence" (NOT probability of truth). Neutral, unverifiable text sits at 0.70.
        conf = 0.70
        if absolute == "strong": conf -= 0.18
        elif absolute == "weak": conf -= 0.08
        if emotional: conf -= min(0.10 * len(emotional), 0.20)
        if bias: conf -= min(0.08 * len(bias), 0.16)
        if shouting: conf -= 0.06
        if has_stat and not has_source: conf -= 0.18
        if manip: conf -= 0.25
        if has_source and not manip: conf += 0.05      # unchecked source: tiny bonus only
        if fact_state == "matches": conf = max(conf, 0.92) - 0.05 * bool(manip)
        if fact_state == "contradicted": conf = 0.03
        conf = round(max(0.03, min(0.98, conf)), 2)
        confidences.append(conf)

        reasons = []
        if fact_state == "contradicted": reasons.append("Contradicted by built-in fact check: " + fact_note)
        if fact_state == "matches": reasons.append(fact_note)
        if manip: reasons.append("Possible manipulation pattern: " + ", ".join(manip) + ".")
        if absolute: reasons.append("Uses absolute or sweeping language.")
        if has_stat and not has_source:
            reasons.append("Contains a statistic or research reference without a source; verify it independently.")
            unverified_stats += 1
        if emotional: reasons.append("Emotionally loaded wording: " + ", ".join(emotional) + ".")
        if bias: reasons.append("Potentially biased wording: " + ", ".join(bias) + ".")
        if has_source: reasons.append("A source-like reference is present, but it has not been checked.")
        if not reasons:
            reasons.append("No rule-based warning detected. The claim was not fact-checked, so this is not proof it is true.")

        if fact_state == "contradicted":
            status = "Contradicted"; contradicted += 1
        elif manip or absolute == "strong" or (absolute == "weak" and (emotional or bias or has_stat)):
            status = "Flagged"; flagged += 1
        elif fact_state == "matches":
            status = "Matches known fact"; matched += 1
        elif absolute == "weak" or (has_stat and not has_source) or emotional or bias or conf < 0.60:
            status = "Needs review"; needs_review += 1
        else:
            status = "No strong signal"

        claims.append({
            "id": idx, "claim_text": claim, "status": status,
            "confidence": conf, "reason": " ".join(reasons),
            "manipulation_types": manip,
            "emotional_terms": emotional, "bias_terms": bias,
            "has_statistical_claim": has_stat, "has_source_reference": has_source,
        })

    n = len(claims)
    avg = sum(confidences) / n
    worst = min(confidences)
    # Blend average with the weakest statement so one bad claim cannot hide in many clean ones.
    base = (0.65 * avg + 0.35 * worst) * 100
    penalty = (flagged * 8 + needs_review * 3 + contradicted * 25) / n
    trust = max(0.0, min(100.0, base - penalty))
    if contradicted:
        trust = min(trust, 35.0 - min(15.0, 10.0 * contradicted / n))   # any false claim caps trust low
    trust = round(trust, 1)

    certainty = round(avg * 100, 1)
    factual = 70.0 + 30.0 * matched / n - 70.0 * contradicted / n - 25.0 * unverified_stats / n - 6.0 * flagged / n
    factual = round(max(0.0, min(100.0, factual)), 1)
    manipulation_score = round(min(100.0, len(all_manip) * 20 + 40.0 * manip_claims / n + 6 * emotional_hits), 1)
    bias_score = round(min(100.0, bias_hits / max(n * 2, 1) * 100), 1)
    warning_count = flagged + needs_review + contradicted

    if contradicted: verdict = "Contains statement(s) that contradict well-known facts."
    elif trust >= 80: verdict = "Few rule-based warning signals detected."
    elif trust >= 60: verdict = "No major warning signals, but claims are unverified and need review."
    elif trust >= 40: verdict = "Several warning signals detected; review the claims carefully."
    else: verdict = "Strong warning signals detected; do not rely on this text without verification."
    summary = (f"{verdict} Reviewed {n} statement(s): {contradicted} contradicted, {flagged} flagged, "
               f"{needs_review} needing review, {matched} matching known facts, and "
               f"{n - contradicted - flagged - needs_review - matched} with no strong signal.")

    return {
        "overall_trust_score": trust,
        "summary": summary,
        "claims": claims,
        "metrics": {
            "factual_integrity_score": factual,
            "certainty_score": certainty,
            "hallucination_count": warning_count,
            "contradicted_count": contradicted,
            "bias_detected": bias_hits > 0,
            "bias_score": bias_score,
            "emotional_manipulation_score": manipulation_score,
            "emotional_manipulation_detected": bool(all_manip) or emotional_hits > 0,
            "manipulation_types": sorted(all_manip),
            "unverified_stats_count": unverified_stats,
            "claim_count": n,
        },
        "limitations": ("Rule-based screening with a small built-in fact layer. Statements outside it are "
                        "unverified, so this tool cannot establish whether a claim is true, false, or a lie."),
    }
