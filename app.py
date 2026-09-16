"""
AI Design Companion — Usability Feedback Summarizer + Screen & Flow Review
Turns raw usability-test feedback into a visual dashboard of themed,
prioritized, actionable design insight, and reviews a flow's screens for
end-to-end gaps and the clarifying questions to ask engineering/product
before it ships.

Run locally:   streamlit run app.py
Deploy free:   push this folder (with .streamlit/config.toml) to a public
               GitHub repo, then "New app" at https://share.streamlit.io
               and point it at app.py. Takes about 3 minutes.
"""

import base64
import csv
import json
import re

import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Design tokens (mirrors the Material-inspired palette in the live artifact)
# ---------------------------------------------------------------------------

SEV_ORDER = ["Critical", "High", "Medium", "Low"]
SEV_COLOR = {"Critical": "#D03B3B", "High": "#EC835A", "Medium": "#FAB219", "Low": "#0CA30C"}
SEV_TINT = {"Critical": "#FBE7E5", "High": "#FCEEE5", "Medium": "#FDF1D8", "Low": "#E4F5E3"}
CAT_COLOR = {"Engineering": "#2A78D6", "Product": "#EB6834"}
CAT_TINT = {"Engineering": "#E4EEFB", "Product": "#FCEBE2"}
TEXT = "#15201B"
TEXT_MUTED = "#5B6961"
SURFACE = "#FFFFFF"
SURFACE_2 = "#F6F8F4"
SURFACE_TONAL = "#E3EFE8"
LINE = "#DEE6DE"
PRIMARY = "#1F6E58"
GRAD_A = "linear-gradient(135deg,#0F5C46 0%,#3FA66B 100%)"
GRAD_B = "linear-gradient(135deg,#C4451F 0%,#E88A3F 100%)"

# ---------------------------------------------------------------------------
# Tool 1: Usability Feedback Summarizer
# ---------------------------------------------------------------------------

SUMMARIZER_PROMPT = """You are an AI Design Companion helping a product design team turn raw
usability-test feedback into fast, actionable insight. Cluster the quotes
into 4-6 themes (plain-language names, not jargon). For each theme: list
which participants raised it, quote the most representative line, rate
severity (Critical/High/Medium/Low) by real-world impact on the task
(wasted trips, failed payments, safety > frustration > friction > polish),
and propose ONE concrete, specific fix (an actual copy/control/interaction
change, not "improve clarity"). Treat localization, RTL, currency and
dark-mode issues as first-class findings, not footnotes, whenever the
feedback raises them. Order themes most severe first. Close with 2-3
Quick Wins: low-effort, high-impact fixes doable this sprint.

Return ONLY strict JSON, no prose, matching exactly:
{"themes":[{"name":string,"severity":"Critical"|"High"|"Medium"|"Low",
"participants":[string],"quote":string,"fix":string}],
"quickWins":[string]}
"""

DEMO_RESULT = {
    "themes": [
        {"name": "Localization isn't applied consistently", "severity": "Critical",
         "participants": ["P02", "P03", "P09", "P10"],
         "quote": "Half the settings menu flipped to RTL but the bottom nav icons stayed left-to-right ordered — felt broken, not intentional. (P09)",
         "fix": "Audit every screen against one RTL checklist (icon mirroring, nav order, directional icons). Add a single locale-aware formatter for digits and currency so a screen never mixes Arabic-Indic/Western numerals or USD/AED."},
        {"name": "Live tracking loses the rider's trust", "severity": "Critical",
         "participants": ["P05", "P06", "P18"],
         "quote": "My connection dropped mid-ride and when it came back, the map hadn't updated — I couldn't tell if the ride was still being tracked correctly. (P18)",
         "fix": "Add a \"reconnecting / last updated Xs ago\" state on the map instead of freezing silently. Explain material ETA jumps instead of just changing the number. Raise dark-mode road-vs-background contrast to a 3:1 minimum."},
        {"name": "Payment moments lack confirmation and transparency", "severity": "Critical",
         "participants": ["P07", "P08", "P13"],
         "quote": "My saved card failed silently — the app just sat on a spinner. I didn't know if I should try again or if I'd already been charged. (P07)",
         "fix": "Give every payment attempt an explicit success/fail state. Show an itemized fare breakdown. Disclose any cancellation fee before the user confirms canceling, not after."},
        {"name": "Risky actions aren't visually differentiated", "severity": "High",
         "participants": ["P04", "P11"],
         "quote": "The 'Confirm ride' and 'Cancel' buttons are right next to each other in almost the same color — I nearly canceled by mistake. (P04)",
         "fix": "Give primary (Confirm) and destructive (Cancel) actions distinct color, weight and spacing. Enlarge star-rating tap targets."},
        {"name": "Onboarding overwhelms and under-explains", "severity": "Medium",
         "participants": ["P16", "P17"],
         "quote": "The permission requests for location, notifications and contacts all came at once — I just tapped 'allow' on everything without reading. (P16)",
         "fix": "Request permissions contextually instead of all at launch. Define \"Captain\" with a one-line tooltip the first time it appears."},
        {"name": "Missing features for real-world ride context", "severity": "Medium",
         "participants": ["P12", "P14", "P15"],
         "quote": "There's no way to book a ride for a family member and share live tracking with them — I had to send screenshots over WhatsApp. (P15)",
         "fix": "Add \"Book for someone else\" with a shareable live-tracking link. Replace the blank post-cancellation screen with a clear confirmation state. Add quick feedback tags alongside the rating."},
    ],
    "quickWins": [
        "Disclose the cancellation fee before the user confirms canceling, not after.",
        "Fix bottom-nav icon order and digit formatting when the app is in Arabic/RTL.",
        "Add an explicit success/fail state to every payment attempt.",
    ],
}

DEFAULT_CSV_PATH = "feedback_dummy.csv"


def load_default_feedback() -> str:
    try:
        with open(DEFAULT_CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            lines = []
            for row in reader:
                lines.append(
                    f"[{row['participant_id']}] Task: {row['task']} — "
                    f"\"{row['feedback_text']}\""
                )
            return "\n".join(lines)
    except FileNotFoundError:
        return ""


# ---------------------------------------------------------------------------
# Tool 2: Screen & Flow Review
# ---------------------------------------------------------------------------

FLOW_PROMPT = """You are an AI Design Companion acting as a QA-minded UX reviewer for a
multi-vertical super app. You are shown screens (as images, and/or short
text descriptions) from ONE user flow, in order — step 1 is the first
thing the user sees, the last step is where the flow ends.

DO THIS:
1. For each screen, note concrete usability issues (labeling, hierarchy,
   affordance, consistency, missing states) — specific to what's actually
   shown, never generic advice. Always call out anything localization-,
   RTL-, currency- or dark-mode-related that you can tell from the screen
   or that's worth verifying.
2. Thinking about the WHOLE flow end-to-end, list GAPS: states or screens
   this specific flow is plausibly missing (error, empty, loading, offline,
   permission-denied, timeout, already-completed, cancellation) — only
   ones that make sense for THIS flow, not a generic checklist.
3. List CLARIFYING QUESTIONS a designer should ask before this ships,
   split into "engineering" (technical/data/state/edge-case questions) and
   "product" (business-rule/scope questions). Each must be specific to
   something ambiguous or unshown in these screens.

Return ONLY strict JSON, no prose, matching exactly:
{"screens":[{"step":number,"label":string,"findings":[string]}],
"gaps":[string],"questions":{"engineering":[string],"product":[string]}}
"""

DEMO_FLOW_RESULT = {
    "screens": [
        {"step": 1, "label": "Set pickup & dropoff", "findings": [
            "No visible way to swap pickup and dropoff once both are set.",
            "If this screen ships in Arabic/RTL, the mic icon and any directional map controls need explicit mirroring rules verified — don't assume the layout flip covers them."]},
        {"step": 2, "label": "Choose ride type & confirm", "findings": [
            "Prices aren't shown with a currency symbol next to each option — easy to misread when scanning quickly.",
            "No estimated wait time shown before the ride starts, only price."]},
        {"step": 3, "label": "Track captain en route", "findings": [
            "\"Cancel ride\" is a plain text link — easy to miss, or worse, easy to tap by accident.",
            "No \"last updated\" timestamp on the captain's live location — the same trust gap the ETA-jump feedback surfaced."]},
    ],
    "gaps": [
        "No state shown for the captain canceling or being reassigned after the ride is confirmed.",
        "No offline/reconnecting state if the network drops during tracking.",
        "No RTL-specific QA checkpoint anywhere in this flow — mirroring needs verifying screen by screen.",
        "No screen for what happens if no captains are available near the pickup point.",
    ],
    "questions": {
        "engineering": [
            "If the assigned captain cancels after confirmation, does the app auto-search for a new one, or does the user rebook from scratch?",
            "Is captain location pushed or polled, and what's the expected staleness on a weak connection?",
            "Does the RTL layout mirror per-component automatically, or does each screen need explicit rules for directional elements?",
        ],
        "product": [
            "Should a price estimate show before step 1 is even complete, or only once both pins are set?",
            "What's the policy when a ride is significantly delayed by captain reassignment?",
            "Is \"book for someone else\" in scope for this flow, or a separate entry point?",
        ],
    },
}

DEFAULT_FLOW_TEXT = """\
1. Set pickup & dropoff — map with two pins, search bar with mic icon, "Confirm locations" button
2. Choose ride type & confirm — list of ride options (Economy/Business) with prices, "Confirm ride" button
3. Track captain en route — live map, captain photo/name/plate, ETA, a plain-text "Cancel ride" link
"""

SCREEN_ICON_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="26" height="26">'
    '<rect x="4" y="2" width="16" height="20" rx="2.5" stroke="#1F6E58" stroke-width="1.6"/>'
    '<line x1="7" y1="7" x2="17" y2="7" stroke="#1F6E58" stroke-width="1.6"/>'
    '<line x1="7" y1="11" x2="14" y2="11" stroke="#1F6E58" stroke-width="1.6"/>'
    '<rect x="7" y="15" width="10" height="4" rx="1" stroke="#1F6E58" stroke-width="1.6"/>'
    "</svg>"
)


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def image_to_data_url(uploaded_file) -> str:
    raw = uploaded_file.getvalue()
    b64 = base64.b64encode(raw).decode("utf-8")
    mime = uploaded_file.type or "image/png"
    return f"data:{mime};base64,{b64}"


def parse_json_loose(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except Exception:
            pass
    start = min([i for i in [text.find("{"), text.find("[")] if i != -1] or [-1])
    end = max(text.rfind("}"), text.rfind("]"))
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    raise ValueError("Could not parse a JSON object from the model's reply.")


def call_openai(api_key: str, prompt: str, text: str, images=None) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    content = [{"type": "text", "text": text}]
    for img in images or []:
        content.append({"type": "image_url", "image_url": {"url": image_to_data_url(img)}})
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": content}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return parse_json_loose(resp.choices[0].message.content)


def call_anthropic(api_key: str, prompt: str, text: str, images=None) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    content = [{"type": "text", "text": text}]
    for img in images or []:
        raw = img.getvalue()
        b64 = base64.b64encode(raw).decode("utf-8")
        mime = img.type or "image/png"
        content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}})
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        system=prompt,
        messages=[{"role": "user", "content": content}],
    )
    return parse_json_loose(resp.content[0].text)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def inject_base_style():
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700;900&family=Roboto+Mono:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
        html, body, [class*="css"]  { font-family: 'Roboto', sans-serif; }
        .dc-card{
            background:#FFFFFF; border:1px solid #DEE6DE; border-radius:20px;
            padding:18px 20px; box-shadow:0 1px 2px rgba(15,25,20,.05), 0 1px 3px rgba(15,25,20,.07);
            margin-bottom:14px;
        }
        .dc-stat{
            border-radius:20px; padding:20px; color:#fff; min-height:118px;
            display:flex; flex-direction:column; justify-content:space-between;
            box-shadow:0 2px 6px rgba(15,25,20,.06), 0 10px 24px -12px rgba(15,25,20,.2);
        }
        .dc-stat .lbl{ font-size:12.5px; font-weight:600; opacity:.92; }
        .dc-stat .num{ font-size:36px; font-weight:900; line-height:1; }
        .dc-stat .sub{ font-size:11px; opacity:.8; margin-top:4px; }
        .dc-chip{
            display:inline-flex; align-items:center; gap:6px; font-size:11px; font-weight:700;
            padding:4px 10px 4px 8px; border-radius:100px; color:#15201B;
        }
        .dc-chip .dot{ width:8px; height:8px; border-radius:50%; }
        .dc-tag{
            font-family:'Roboto Mono',monospace; font-size:10.5px; color:#5B6961;
            background:#F6F8F4; border:1px solid #DEE6DE; border-radius:6px; padding:2px 7px; margin-right:5px;
        }
        .dc-quote{ font-size:13px; font-style:italic; color:#5B6961; padding-left:10px; border-left:2px solid #DEE6DE; margin:8px 0; }
        .dc-fix{ font-size:13px; line-height:1.55; background:#E3EFE8; border-radius:10px; padding:10px 12px; }
        .dc-fix b{ color:#1F6E58; font-family:'Roboto Mono',monospace; font-size:10.5px; letter-spacing:.03em; text-transform:uppercase; }
        .dc-gaps{ background:#FBE7E5; border-radius:16px; padding:16px 18px; }
        .dc-qcol{ background:#FFFFFF; border:1px solid #DEE6DE; border-radius:16px; padding:14px 16px; height:100%; }
        .dc-chipwin{ background:#FFFFFF; border:1px solid #DEE6DE; border-radius:10px; padding:9px 12px; font-size:13px; margin-bottom:8px; }
        div.stButton > button[kind="primary"]{ border-radius:100px; font-weight:700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def stat_tile(label, number, sub, gradient):
    st.markdown(
        f'<div class="dc-stat" style="background:{gradient}">'
        f'<div class="lbl">{label}</div>'
        f'<div><div class="num">{number}</div><div class="sub">{sub}</div></div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def donut_figure(labels, values, colors, center_text):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.66,
                marker=dict(colors=colors, line=dict(color=SURFACE, width=2)),
                textinfo="none",
                sort=False,
                hovertemplate="%{label}: %{value}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", font=dict(size=12, color=TEXT), x=1, y=0.5),
        margin=dict(l=0, r=0, t=0, b=0),
        height=170,
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=center_text, x=0.5, y=0.5, font=dict(size=20, color=TEXT, family="Roboto"), showarrow=False)],
    )
    return fig


def bar_figure(names, values, colors, unit_label):
    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker=dict(color=colors),
            text=[f"{v} {unit_label}" for v in values],
            textposition="outside",
            hovertemplate="%{y}: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=60, t=6, b=6),
        height=max(180, 46 * len(names)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12.5, color=TEXT)),
        font=dict(family="Roboto"),
    )
    return fig


def sev_chip_html(sev):
    color = SEV_COLOR.get(sev, TEXT_MUTED)
    tint = SEV_TINT.get(sev, SURFACE_2)
    return f'<span class="dc-chip" style="background:{tint}"><span class="dot" style="background:{color}"></span>{sev}</span>'


def render_feedback_dashboard(result: dict, meta: str):
    themes = result.get("themes", [])
    quick_wins = result.get("quickWins", [])

    st.markdown(f"##### Results &nbsp;·&nbsp; <span style='font-family:monospace;font-size:12px;color:#5B6961'>{meta}</span>", unsafe_allow_html=True)

    participants = set()
    for t in themes:
        participants.update(t.get("participants", []))
    urgent = sum(1 for t in themes if t.get("severity") in ("Critical", "High"))
    counts = {s: 0 for s in SEV_ORDER}
    for t in themes:
        if t.get("severity") in counts:
            counts[t["severity"]] += 1

    c1, c2, c3 = st.columns([1, 1, 1.3])
    with c1:
        stat_tile("Themes identified", len(themes), f"across {len(participants)} participants", GRAD_A)
    with c2:
        stat_tile("Need attention now", urgent, "critical + high severity", GRAD_B)
    with c3:
        labels = [s for s in SEV_ORDER if counts[s] > 0]
        values = [counts[s] for s in labels]
        colors = [SEV_COLOR[s] for s in labels]
        if values:
            st.plotly_chart(donut_figure(labels, values, colors, str(len(themes))), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No themes to chart yet.")

    with st.container(border=True):
        st.markdown("**Participants affected, by theme**")
        if themes:
            names = [t.get("name", "Untitled") for t in themes]
            counts_p = [len(t.get("participants", [])) for t in themes]
            colors_p = [SEV_COLOR.get(t.get("severity"), TEXT_MUTED) for t in themes]
            st.plotly_chart(bar_figure(names, counts_p, colors_p, "ppl"), use_container_width=True, config={"displayModeBar": False})

    for t in themes:
        tags = "".join(f'<span class="dc-tag">{p}</span>' for p in t.get("participants", []))
        st.markdown(
            f"""
            <div class="dc-card">
              <div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:6px;">
                <strong style="font-size:14.5px;">{t.get('name','')}</strong>
                {sev_chip_html(t.get('severity','Medium'))}
              </div>
              <div style="margin-bottom:8px;">{tags}</div>
              <div class="dc-quote">&ldquo;{t.get('quote','')}&rdquo;</div>
              <div class="dc-fix"><b>Fix</b><br>{t.get('fix','')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if quick_wins:
        chips = "".join(f'<div class="dc-chipwin">{q}</div>' for q in quick_wins)
        st.markdown(
            f'<div class="dc-card" style="background:#F3E6D2;"><strong style="font-size:12px;letter-spacing:.03em;text-transform:uppercase;color:#6B451A;">Quick wins — this sprint</strong>'
            f'<div style="margin-top:10px;">{chips}</div></div>',
            unsafe_allow_html=True,
        )


def render_flow_dashboard(result: dict, meta: str, images=None):
    screens = result.get("screens", [])
    gaps = result.get("gaps", [])
    questions = result.get("questions", {})
    eng_q = questions.get("engineering", [])
    prod_q = questions.get("product", [])

    st.markdown(f"##### End-to-end review &nbsp;·&nbsp; <span style='font-family:monospace;font-size:12px;color:#5B6961'>{meta}</span>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1.3])
    with c1:
        stat_tile("Screens reviewed", len(screens), "in this flow", GRAD_A)
    with c2:
        stat_tile("Flow gaps found", len(gaps), "states likely missing", GRAD_B)
    with c3:
        vals = [len(eng_q), len(prod_q)]
        if sum(vals) > 0:
            st.plotly_chart(
                donut_figure(["Engineering", "Product"], vals, [CAT_COLOR["Engineering"], CAT_COLOR["Product"]], str(sum(vals))),
                use_container_width=True, config={"displayModeBar": False},
            )
        else:
            st.info("No questions raised.")

    for i, s in enumerate(screens):
        cols = st.columns([1, 5])
        with cols[0]:
            if images and i < len(images):
                st.image(images[i].getvalue(), width=64)
            else:
                st.markdown(f'<div style="width:52px;height:52px;border-radius:12px;background:#E3EFE8;display:flex;align-items:center;justify-content:center;">{SCREEN_ICON_SVG}</div>', unsafe_allow_html=True)
        with cols[1]:
            findings = "".join(f"<li>{f}</li>" for f in s.get("findings", []))
            st.markdown(
                f"<div class='dc-card' style='margin-bottom:8px;'><strong>Step {s.get('step', i+1)} · {s.get('label','')}</strong>"
                f"<ul style='margin:6px 0 0;padding-left:18px;'>{findings}</ul></div>",
                unsafe_allow_html=True,
            )

    if gaps:
        items = "".join(f"<li>{g}</li>" for g in gaps)
        st.markdown(
            f'<div class="dc-gaps"><strong style="font-size:12px;letter-spacing:.03em;text-transform:uppercase;">Flow gaps — states this flow is likely missing</strong>'
            f'<ul style="margin:10px 0 0;padding-left:20px;">{items}</ul></div>',
            unsafe_allow_html=True,
        )

    qc1, qc2 = st.columns(2)
    with qc1:
        items = "".join(f"<li>{q}</li>" for q in eng_q)
        st.markdown(
            f'<div class="dc-qcol"><strong style="font-size:11.5px;letter-spacing:.03em;text-transform:uppercase;color:{CAT_COLOR["Engineering"]};">● Ask engineering</strong>'
            f'<ul style="margin:9px 0 0;padding-left:18px;">{items}</ul></div>',
            unsafe_allow_html=True,
        )
    with qc2:
        items = "".join(f"<li>{q}</li>" for q in prod_q)
        st.markdown(
            f'<div class="dc-qcol"><strong style="font-size:11.5px;letter-spacing:.03em;text-transform:uppercase;color:{CAT_COLOR["Product"]};">● Ask product</strong>'
            f'<ul style="margin:9px 0 0;padding-left:18px;">{items}</ul></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.set_page_config(page_title="AI Design Companion", page_icon="🧭", layout="wide")
inject_base_style()

st.title("AI Design Companion")
st.caption(
    "Summarize usability feedback into prioritized fixes, or review a flow's screens "
    "for end-to-end gaps — localization, RTL and dark-mode issues included by default."
)

tab1, tab2 = st.tabs(["Usability Feedback", "Screens & Flow"])

# --- Tab 1: Feedback Summarizer ---
with tab1:
    with st.container(border=True):
        with st.expander("Show the prompt this tool runs"):
            st.code(SUMMARIZER_PROMPT, language="text")

        uploaded_txt = st.file_uploader("Drop a .txt or .csv of feedback (optional)", type=["txt", "csv"], key="fb_file")
        if uploaded_txt is not None and st.session_state.get("_fb_file_name") != uploaded_txt.name:
            st.session_state["feedback_text"] = uploaded_txt.getvalue().decode("utf-8", errors="ignore")
            st.session_state["_fb_file_name"] = uploaded_txt.name
        if "feedback_text" not in st.session_state:
            st.session_state["feedback_text"] = load_default_feedback()

        feedback_text = st.text_area("Or paste/edit feedback (one quote per line)", height=200, key="feedback_text")

        mode = st.radio("Mode", ["Demo mode (no API key needed)", "Live mode (use your own API key)"], horizontal=True, key="mode1")
        if mode.startswith("Live"):
            provider1 = st.selectbox("Provider", ["OpenAI", "Anthropic"], key="provider1")
            api_key1 = st.text_input(f"{provider1} API key", type="password", key="key1")
        run1 = st.button("Analyze feedback", type="primary", key="run1")

    if run1:
        if mode.startswith("Demo"):
            render_feedback_dashboard(DEMO_RESULT, "sample run · precomputed")
            st.info("Pre-computed sample so anyone viewing this demo sees real output with no API key. Switch to Live mode to run it for real.")
        elif not st.session_state.get("key1"):
            st.error("Add an API key to run live mode, or switch to Demo mode.")
        elif not feedback_text.strip():
            st.error("Paste some feedback first.")
        else:
            with st.spinner("Analyzing feedback..."):
                try:
                    fn = call_openai if provider1 == "OpenAI" else call_anthropic
                    result = fn(api_key1, SUMMARIZER_PROMPT, feedback_text)
                    render_feedback_dashboard(result, "live · just now")
                except Exception as e:
                    st.error(f"Something went wrong calling {provider1}: {e}")
    else:
        render_feedback_dashboard(DEMO_RESULT, "sample run · precomputed")

# --- Tab 2: Screen & Flow Review ---
with tab2:
    with st.container(border=True):
        with st.expander("Show the prompt this tool runs"):
            st.code(FLOW_PROMPT, language="text")

        uploaded_imgs = st.file_uploader(
            "Drop screenshots here, in order (optional)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="flow_imgs",
        )
        if uploaded_imgs:
            thumb_cols = st.columns(min(len(uploaded_imgs), 8))
            for i, img in enumerate(uploaded_imgs):
                with thumb_cols[i % len(thumb_cols)]:
                    st.image(img.getvalue(), width=70, caption=f"{i+1}")

        flow_text = st.text_area("Or describe each step (one per line)", value=DEFAULT_FLOW_TEXT, height=130, key="flow_text")

        mode2 = st.radio("Mode", ["Demo mode (no API key needed)", "Live mode (use your own API key)"], horizontal=True, key="mode2")
        if mode2.startswith("Live"):
            provider2 = st.selectbox("Provider", ["OpenAI", "Anthropic"], key="provider2")
            api_key2 = st.text_input(f"{provider2} API key", type="password", key="key2")
        run2 = st.button("Review this flow", type="primary", key="run2")

    if run2:
        if mode2.startswith("Demo"):
            render_flow_dashboard(DEMO_FLOW_RESULT, "sample run · precomputed", images=None)
            st.info("Pre-computed sample on the default 3-step flow above. Switch to Live mode to run it for real on your own flow or screenshots.")
        elif not st.session_state.get("key2"):
            st.error("Add an API key to run live mode, or switch to Demo mode.")
        elif not flow_text.strip() and not uploaded_imgs:
            st.error("Describe your flow or upload screenshots first.")
        else:
            note = (
                f"{len(uploaded_imgs)} screenshot(s) attached, in order — use them as the primary source; the text below is context."
                if uploaded_imgs
                else "No screenshots attached — rely on the text description below."
            )
            with st.spinner("Reviewing flow..."):
                try:
                    fn = call_openai if provider2 == "OpenAI" else call_anthropic
                    result = fn(api_key2, FLOW_PROMPT, f"{note}\n\n{flow_text}", images=uploaded_imgs)
                    render_flow_dashboard(result, "live · just now", images=uploaded_imgs)
                except Exception as e:
                    st.error(f"Something went wrong calling {provider2}: {e}")
    else:
        render_flow_dashboard(DEMO_FLOW_RESULT, "sample run · precomputed", images=None)

st.divider()
st.caption(
    "Prototype for a design-tooling application challenge. Feedback and flow content shown "
    "by default are self-created dummy examples for a fictional Middle-East ride-hailing app "
    "(no real user, company or product data)."
)
