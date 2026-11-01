import streamlit as st
from datetime import datetime
from services.analyzer import analyze_text
from services.factcheck import run_external_checks
import os, json, html, re
from services.llm_providers import PROVIDERS, generate, neutralize_prompt, audit_prompt

st.set_page_config(page_title="FactShield AI", page_icon="🛡️", layout="wide")

BG, TEXT, ACCENT, PANEL, SAGE, BORDER = "#F7F4EC", "#2D3732", "#88A378", "#FFFFFF", "#EBEFE7", "#DCE4D7"
if "current_page" not in st.session_state: st.session_state.current_page = "🏠 Landing Page"
if "raw_text" not in st.session_state: st.session_state.raw_text = ""
if "current_result" not in st.session_state: st.session_state.current_result = None
if "audit_history" not in st.session_state: st.session_state.audit_history = []

st.markdown(f"""<style>
html {{ scroll-behavior: smooth; }}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"]{{background:{BG}!important}}
[data-testid="stSidebar"],[data-testid="stSidebar"]>div:first-child{{background:#EDE7DF!important}}
h1,h2,h3,h4,p,label,.stMarkdown{{color:{TEXT}!important}}
textarea,input{{background:{PANEL}!important;color:{TEXT}!important;border:1px solid {BORDER}!important}}
.stButton>button{{background:{ACCENT}!important;color:white!important;font-weight:700!important;border:0!important;border-radius:7px!important}}
.metric-card{{background:{SAGE};border:1px solid {BORDER};border-radius:10px;padding:17px;text-align:center;min-height:112px}}
.metric-label{{font-size:12px;font-weight:700;letter-spacing:.5px;color:#556B4D}}
.metric-value{{font-size:30px;font-weight:800;color:{TEXT}}}
.audit-card{{background:white;border:1px solid {BORDER};border-left:5px solid {ACCENT};border-radius:9px;padding:15px;margin:10px 0}}
.small-muted{{font-size:12px;color:#647268}}
</style>""", unsafe_allow_html=True)

PAGES = ["🏠 Landing Page", "🔍 AI Text Analyzer", "📊 Analysis Dashboard", "📄 Detailed Reports", "📜 Audit History"]
with st.sidebar:
    st.markdown("## 🛡️ FactShield AI")
    st.caption("Rule-based text screening demo")
    for page in PAGES:
        if st.button(page, key="nav_" + page, use_container_width=True):
            st.session_state.current_page = page
            st.rerun()
    st.divider()
    st.caption("Evidence-led text audit • Results are indicative, not proof of truth")
    with st.expander("🔑 Provider / Token Settings", expanded=False):
        provider_names = list(PROVIDERS.keys())
        st.session_state.setdefault("llm_provider", "Groq")
        chosen = st.selectbox("LLM provider", provider_names, index=provider_names.index(st.session_state.llm_provider), key="provider_picker")
        st.session_state.llm_provider = chosen
        st.text_input("Model ID (editable)", value=st.session_state.get("model_"+chosen, PROVIDERS[chosen]["model"]), key="model_input_"+chosen)
        st.session_state["model_"+chosen] = st.session_state["model_input_"+chosen]
        if chosen != "Ollama (local)":
            st.text_input("API key", type="password", key="key_"+chosen, placeholder="Paste provider key for this session")
        else:
            st.text_input("Ollama endpoint", value="http://localhost:11434/api/chat", key="ollama_url")
        st.caption("Keys are used only for this session and are not written to project files. Use server-side secrets for public deployment.")

st.title("🛡️ FactShield AI")
st.caption("Multi-signal text audit • Factual review • Manipulation • Bias")
st.divider()
page = st.session_state.current_page

if page == "🏠 Landing Page":
    st.header("Trust-as-a-Service for AI-generated text")
    st.write("Submit a statement to screen it for unsupported statistics, sweeping claims, emotionally loaded language, possible manipulation patterns, and bias indicators.")
    c1,c2,c3 = st.columns(3)
    for col, title, desc in [
        (c1,"🔎 Claim review","Break text into smaller statements and show why each one was flagged."),
        (c2,"💬 Manipulation signals","Look for guilt-tripping, coercion, isolation, and gaslighting-like phrases."),
        (c3,"⚖️ Bias signals","Highlight loaded or sweeping language that deserves human review.")]:
        with col: st.markdown(f"<div class='audit-card'><h3>{title}</h3><p>{desc}</p></div>",unsafe_allow_html=True)
    st.info("FactShield combines heuristic screening with optional external fact-check references and configurable LLM assistance. A score is a screening signal, not proof of truth.")
    if st.button("Open Text Analyzer"):
        st.session_state.current_page = "🔍 AI Text Analyzer"; st.rerun()

elif page == "🔍 AI Text Analyzer":
    st.header("📥 Submit text for audit")
    uploaded = st.file_uploader("Optional: upload a .txt or .md file", type=["txt","md"])
    if uploaded is not None:
        try:
            file_text = uploaded.getvalue().decode("utf-8")
            st.text_area("Uploaded file preview", file_text, height=130, disabled=True)
        except UnicodeDecodeError:
            st.error("Could not read this file as UTF-8 text.")
            file_text = ""
    else:
        file_text = ""
    st.session_state.raw_text = st.text_area("Paste the statement or text you want to audit", value=st.session_state.raw_text, height=220, placeholder="Example: If you really loved me, you would do this.")
    if st.button("🚀 RUN COMPLETE AUDIT", type="primary", use_container_width=True):
        submitted = file_text.strip() if file_text.strip() else st.session_state.raw_text.strip()
        if not submitted:
            st.warning("Please paste text or upload a text file first.")
        else:
            result = analyze_text(submitted)
            # API keys belong in Streamlit Secrets or backend environment variables,
            # never in the public frontend source code.
            try:
                google_api_key = st.secrets.get("GOOGLE_FACT_CHECK_API_KEY", "")
            except Exception:
                google_api_key = ""
            result["external_checks"] = run_external_checks(
                submitted, result.get("claims", []), google_api_key or os.getenv("GOOGLE_FACT_CHECK_API_KEY", "")
            )
            st.session_state.current_result = result
            st.session_state.audited_text = submitted
            st.session_state.audit_history.insert(0, {
                "time": datetime.now().strftime("%d %b %Y, %I:%M:%S %p"),
                "preview": submitted[:110] + ("…" if len(submitted)>110 else ""),
                "score": result["overall_trust_score"],
                "claims": result["metrics"]["claim_count"],
            })
            st.session_state.current_page = "📊 Analysis Dashboard"
            st.rerun()

elif page == "📊 Analysis Dashboard":
    st.header("📊 Audit Dashboard")
    result = st.session_state.current_result
    if not result:
        st.info("No audit results yet. Open AI Text Analyzer and run an audit.")
    else:
        m = result["metrics"]
        a,b,c,d = st.columns(4)
        metrics = [
            (a,"TRUST SCREENING SCORE",f"{result['overall_trust_score']}%"),
            (b,"FACTUAL REVIEW SIGNAL",f"{m['factual_integrity_score']}%"),
            (c,"WARNING FLAGS (incl. contradicted)",f"{m['hallucination_count']} ({m.get('contradicted_count',0)})"),
            (d,"CERTAINTY INDICATOR",f"{m['certainty_score']}%"),
        ]
        for col,label,value in metrics:
            with col: st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>",unsafe_allow_html=True)
        st.subheader("Other audit signals")
        e,f,g = st.columns(3)
        with e: st.metric("Emotional / manipulation signal",f"{m['emotional_manipulation_score']}%", "Signals found" if m["emotional_manipulation_detected"] else "None matched")
        with f: st.metric("Bias signal",f"{m['bias_score']}%", "Indicators found" if m["bias_detected"] else "No indicators found")
        with g: st.metric("Unverified statistics",m["unverified_stats_count"])
        if m["manipulation_types"]: st.warning("Possible manipulation categories: " + ", ".join(m["manipulation_types"]))
        st.success(result["summary"])
        st.subheader("Original text · inline audit heatmap")
        st.caption("🔴 Hallucination / absolute  🟡 Unverified statistic  🟣 Emotional  🟠 Bias  🟢 Citation present. Click a numbered marker to jump to its finding.")
        colors = {"red":"#FECACA", "yellow":"#FEF3C7", "purple":"#E9D5FF", "orange":"#FED7AA", "green":"#BBF7D0"}
        source_text = st.session_state.get("audited_text", "")
        spans = []
        for claim in result["claims"]:
            phrase = claim.get("claim_text", "")
            if not phrase: continue
            start = source_text.find(phrase)
            if start < 0: continue
            end = start + len(phrase)
            if claim.get("has_source_reference"): color, label = colors["green"], "Citation reference"
            elif claim.get("status") == "Contradicted" or re.search(r"\b(always|never|guaranteed|100%|completely|impossible)\b", phrase, re.I): color, label = colors["red"], "Possible hallucination / absolute"
            elif claim.get("has_statistical_claim"): color, label = colors["yellow"], "Unverified statistic"
            elif claim.get("emotional_terms") or claim.get("manipulation_types"): color, label = colors["purple"], "Emotional / manipulation signal"
            elif claim.get("bias_terms"): color, label = colors["orange"], "Possible bias"
            else: continue
            spans.append((start, end, color, claim.get("id", 0), label))
        out, cursor = [], 0
        for start, end, color, cid, label in sorted(spans, key=lambda x:(x[0], -(x[1]-x[0]))):
            if start < cursor: continue
            out.append(html.escape(source_text[cursor:start]))
            out.append(f'<a href="#claim-{cid}" title="{html.escape(label)}" style="background:{color};color:#242424;padding:2px 3px;border-radius:4px;text-decoration:none">{html.escape(source_text[start:end])} <sup>[{cid}]</sup></a>')
            cursor = end
        out.append(html.escape(source_text[cursor:]))
        st.markdown("<div style='background:#202833;color:#f8fafc;padding:18px;border-radius:12px;line-height:2;white-space:pre-wrap'>"+"".join(out)+"</div>", unsafe_allow_html=True)
        st.subheader("Statement-by-statement audit")
        for claim in result["claims"]:
            icon = {"Contradicted": "❌", "Flagged": "🚩", "Needs review": "🟠", "Matches known fact": "✅"}.get(claim["status"], "🟢")
            st.markdown(f"<div id='claim-{claim['id']}'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(f"**{icon} Statement {claim['id']} — {claim['status']} — {claim['confidence']*100:.0f}% review indicator**")
                st.write("**Text:**", claim["claim_text"])
                st.write("**Why:**", claim["reason"])
                if claim["manipulation_types"]: st.write("**Manipulation patterns:**", ", ".join(claim["manipulation_types"]))
        st.caption(result["limitations"])

        # External evidence lookups
        external = result.get("external_checks", {})
        google = external.get("google_fact_check", {})
        wikidata = external.get("wikidata", {})
        st.subheader("🌐 Real-time external evidence")
        with st.expander("Google Fact Check Tools", expanded=True):
            st.info(google.get("message", "External fact-check data was not requested."))
            for review in google.get("reviews", []):
                st.markdown(f"**{review.get('title') or 'Fact-check review'}**")
                st.write("**Publisher:**", review.get("publisher", "Unknown publisher"))
                st.write("**Rating:**", review.get("rating", "Not supplied"))
                if review.get("claim_text"):
                    st.write("**Reviewed claim:**", review["claim_text"])
                if review.get("review_date"):
                    st.caption("Review date: " + review["review_date"])
                if review.get("url"):
                    st.markdown("[Open original fact-check](" + review["url"] + ")")
                st.divider()
            if google.get("error"):
                st.caption("Lookup detail: " + google["error"])
        with st.expander("Wikidata entity references"):
            st.info(wikidata.get("message", "Entity context was not returned."))
            for entity in wikidata.get("entities", []):
                label = entity.get("label") or entity.get("id")
                description = entity.get("description") or "No description supplied"
                st.markdown(f"**[{label}]({entity.get('url', '#')})** — {description}")
                st.caption("Matched text: " + entity.get("searched_name", ""))
            if not wikidata.get("entities"):
                st.caption("No matching entity references were returned.")
            if wikidata.get("error"):
                st.caption("Lookup detail: " + wikidata["error"])
        st.caption("External lookups are evidence discovery, not an automatic truth verdict. No Google match means 'not found', not 'true'.")
        st.divider()
        st.subheader("✨ AI writing tools")
        provider = st.session_state.get("llm_provider", "Groq")
        model = st.session_state.get("model_"+provider, PROVIDERS[provider]["model"])
        key = st.session_state.get("key_"+provider, "")
        if st.button("🪄 Rewrite with Objective Phrasing", use_container_width=True):
            try:
                with st.spinner(f"Requesting rewrite from {provider}…"):
                    st.session_state.neutralized_text = generate(provider, neutralize_prompt(source_text), key, model, base_url=st.session_state.get("ollama_url") if provider == "Ollama (local)" else None)
            except Exception as exc: st.error(str(exc))
        if st.session_state.get("neutralized_text"):
            st.text_area("Objective rewrite · review before using", st.session_state.neutralized_text, height=220)
            st.download_button("Download rewritten text", st.session_state.neutralized_text, "factshield_objective_rewrite.txt", "text/plain")
        st.subheader("⚖️ Model comparison mode")
        compare_text = st.text_area("Prompt / text to compare across models", value=source_text, height=110, key="compare_prompt")
        compare_providers = st.multiselect("Choose models", ["OpenAI", "Anthropic", "Google Gemini", "Groq", "Ollama (local)"], default=["OpenAI", "Anthropic", "Google Gemini"])
        if st.button("Run side-by-side model audit", use_container_width=True):
            st.session_state.model_comparison = {}
            for name in compare_providers:
                try:
                    compare_key = st.session_state.get("key_"+name, "")
                    compare_model = st.session_state.get("model_"+name, PROVIDERS[name]["model"])
                    with st.spinner(f"Auditing with {name}…"):
                        st.session_state.model_comparison[name] = generate(name, audit_prompt(compare_text), compare_key, compare_model, base_url=st.session_state.get("ollama_url") if name == "Ollama (local)" else None)
                except Exception as exc: st.session_state.model_comparison[name] = "ERROR: " + str(exc)
        if st.session_state.get("model_comparison"):
            cols = st.columns(max(1, len(st.session_state.model_comparison)))
            for col, (name, response) in zip(cols, st.session_state.model_comparison.items()):
                with col:
                    st.markdown("**"+name+"**")
                    st.write(response)
        if st.button("Audit another statement"):
            st.session_state.current_page = "🔍 AI Text Analyzer"; st.rerun()

elif page == "📄 Detailed Reports":
    st.header("📄 Detailed Audit Report")
    result = st.session_state.current_result
    if not result:
        st.info("Run an audit first to generate a report.")
    else:
        st.write("**Audited input**")
        st.code(st.session_state.get("audited_text", ""))
        st.write("**Summary**",result["summary"])
        st.json(result["metrics"])
        st.subheader("Detailed claim findings")
        for claim in result["claims"]:
            st.markdown(f"**{claim['id']}. {claim['status']}** — {claim['claim_text']}")
            st.caption(claim["reason"])
        st.warning(result["limitations"])
        report_json = json.dumps(result, indent=2, ensure_ascii=False)
        report_md = "# FactShield AI Audit Report\n\n" + f"**Trust screening score:** {result['overall_trust_score']}%\n\n" + result["summary"] + "\n\n## Metrics\n\n" + "\n".join(f"- **{k.replace('_',' ').title()}:** {v}" for k,v in result["metrics"].items()) + "\n\n## Claims\n\n" + "\n".join(f"### {c['id']}. {c['status']}\n\n{c['claim_text']}\n\n{c['reason']}\n" for c in result["claims"])
        d1,d2,d3 = st.columns(3)
        with d1: st.download_button("⬇️ JSON", report_json, "factshield_audit_report.json", "application/json", use_container_width=True)
        with d2: st.download_button("⬇️ Markdown", report_md, "factshield_audit_report.md", "text/markdown", use_container_width=True)
        with d3:
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib.units import mm
                import io
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
                styles = getSampleStyleSheet()
                def pdf_safe(value):
                    return html.escape(str(value)).encode("latin-1", "replace").decode("latin-1")
                story = [Paragraph("FactShield AI Audit Report", styles["Title"]), Spacer(1,8), Paragraph(f"Trust screening score: {result['overall_trust_score']}%", styles["Heading2"]), Paragraph(pdf_safe(result["summary"]), styles["BodyText"]), Spacer(1,10)]
                for cclaim in result["claims"]:
                    story.extend([Paragraph(f"{cclaim['id']}. {pdf_safe(cclaim['status'])}", styles["Heading3"]), Paragraph(pdf_safe(cclaim['claim_text']), styles["BodyText"]), Paragraph(pdf_safe(cclaim['reason']), styles["BodyText"]), Spacer(1,8)])
                doc.build(story)
                st.download_button("⬇️ PDF", pdf_buffer.getvalue(), "factshield_audit_report.pdf", "application/pdf", use_container_width=True)
            except ImportError: st.caption("Install reportlab to enable PDF export.")
            except Exception as pdf_error: st.warning("PDF export could not be generated: " + str(pdf_error))
        score = result['overall_trust_score']
        badge_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="64" role="img"><rect width="300" height="64" rx="10" fill="#202833"/><text x="16" y="27" font-family="Arial" font-size="15" fill="#fff">FactShield Trust Score</text><text x="16" y="49" font-family="Arial" font-size="18" font-weight="bold" fill="#86efac">'+str(score)+'%</text></svg>'
        badge_html = '<a href="https://kritee-chhabra.github.io/Factshield/" title="FactShield audit badge">'+badge_svg+'</a>'
        st.subheader("🏷️ Shareable trust badge")
        st.markdown(badge_svg, unsafe_allow_html=True)
        st.download_button("Download SVG badge", badge_svg, "factshield_trust_badge.svg", "image/svg+xml")
        st.download_button("Download embed HTML", badge_html, "factshield_badge_embed.html", "text/html")

elif page == "📜 Audit History":
    st.header("📜 Audit History")
    history = st.session_state.audit_history
    if not history:
        st.info("No audits in this session yet.")
    else:
        for idx,item in enumerate(history,1):
            st.markdown(f"<div class='audit-card'><b>Audit #{idx}</b> · {item['time']}<br><b>Trust screening score:</b> {item['score']}% · <b>Statements:</b> {item['claims']}<br>{item['preview']}</div>",unsafe_allow_html=True)
