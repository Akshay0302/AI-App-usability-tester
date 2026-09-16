"""
AI Design Companion — Usability Feedback Summarizer + Screen & Flow Review
Turns raw usability-test feedback into themed, prioritized, actionable
design insight, and reviews a flow's screens for end-to-end gaps and the
clarifying questions to ask engineering/product before it ships.

Run locally:   streamlit run app.py
Deploy free:   push this folder to a public GitHub repo, then
               "New app" at https://share.streamlit.io and point it
               at app.py. Takes about 3 minutes.
"""

import base64
import csv

import streamlit as st

# ---------------------------------------------------------------------------
# Tool 1: Usability Feedback Summarizer
# ---------------------------------------------------------------------------

SUMMARIZER_PROMPT = """You are an AI Design Companion helping a product design team turn raw
usability-test feedback into fast, actionable insight. You think like a
senior UX researcher: you look for patterns across multiple participants,
not just individual complaints, and you always translate a problem into
a concrete next step a designer or PM could act on this week.

INPUT: A list of usability feedback quotes. Each quote includes the
participant ID, the task they were doing, and their verbatim comment.

DO THIS:
1. Cluster the quotes into 4-6 THEMES (recurring pain points). Give each
   theme a short, plain-language name — not a UX jargon label.
2. For each theme, list which participants raised it and quote the most
   representative line.
3. Rate each theme's SEVERITY as Critical / High / Medium / Low, based on:
   - Critical: blocks the core task or causes real-world harm (e.g. wasted
     trips, failed payments, safety risk)
   - High: causes significant frustration or task abandonment for some users
   - Medium: adds friction but users work around it
   - Low: minor polish issue
4. For each theme, propose ONE concrete, specific fix — not "improve
   clarity," but the actual copy, control, or interaction change.
5. Treat localization, RTL, currency and dark-mode issues as first-class
   findings, not footnotes, whenever the feedback raises them.
6. Output a PRIORITIZED list (most severe / highest-impact first) with:
   theme name, severity, participants affected, representative quote,
   and the proposed fix.
7. End with a "Quick Wins" section: 2-3 fixes from the list above that
   are Low-effort / High-impact, callable out for a designer with 30
   minutes and no engineering time this sprint.

FORMAT: Markdown. Use a table for the prioritized list. Keep the whole
response scannable in under 60 seconds — this is meant to be read by a
designer between meetings, not studied like a research report.

Do not invent feedback that isn't in the input. If a theme only has one
data point, still include it but flag it as "single report — validate
before acting."
"""

DEMO_OUTPUT = """\
| # | Theme | Severity | Participants | Representative quote | Proposed fix |
|---|-------|----------|--------------|----------------------|--------------|
| 1 | Localization isn't applied consistently | **Critical** | P02, P03, P09, P10 | "Half the settings menu flipped to RTL but the bottom nav icons stayed left-to-right ordered — felt broken, not intentional." (P09) | Audit every screen against one RTL checklist (icon mirroring, nav order, directional icons). Add a single locale-aware formatter for digits and currency so a screen never mixes Arabic-Indic/Western numerals or USD/AED. |
| 2 | Live tracking loses the rider's trust | **Critical** | P05, P06, P18 | "My connection dropped mid-ride and when it came back, the map hadn't updated — I couldn't tell if the ride was still being tracked correctly." (P18) | Add a "reconnecting / last updated Xs ago" state on the map instead of freezing silently. Explain material ETA jumps instead of just changing the number. Raise dark-mode road-vs-background contrast to a 3:1 minimum. |
| 3 | Payment moments lack confirmation and transparency | **Critical** | P07, P08, P13 | "My saved card failed silently — the app just sat on a spinner. I didn't know if I should try again or if I'd already been charged." (P07) | Give every payment attempt an explicit success/fail state. Show an itemized fare breakdown. Disclose any cancellation fee before the user confirms canceling, not after. |
| 4 | Risky actions aren't visually differentiated | High | P04, P11 | "The 'Confirm ride' and 'Cancel' buttons are right next to each other in almost the same color — I nearly canceled by mistake." (P04) | Give primary (Confirm) and destructive (Cancel) actions distinct color, weight and spacing. Enlarge star-rating tap targets. |
| 5 | Onboarding overwhelms and under-explains | Medium | P16, P17 | "The permission requests for location, notifications and contacts all came at once — I just tapped 'allow' on everything without reading." (P16) | Request permissions contextually instead of all at launch. Define "Captain" with a one-line tooltip the first time it appears. |
| 6 | Missing features for real-world ride context | Medium | P12, P14, P15 | "There's no way to book a ride for a family member and share live tracking with them — I had to send screenshots over WhatsApp." (P15) | Add "Book for someone else" with a shareable live-tracking link. Replace the blank post-cancellation screen with a clear confirmation state. Add quick feedback tags alongside the rating. |

**Quick wins (this sprint, no engineering lift):**
1. Disclose the cancellation fee before the user confirms canceling, not after.
2. Fix bottom-nav icon order and digit formatting when the app is in Arabic/RTL.
3. Add an explicit success/fail state to every payment attempt.
"""

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
   split into "Engineering" (technical/data/state/edge-case questions) and
   "Product" (business-rule/scope questions). Each must be specific to
   something ambiguous or unshown in these screens.

FORMAT: Markdown, organized as:
### Per-screen findings
(one subsection per step)
### Flow gaps
(bulleted list)
### Questions for engineering
(bulleted list)
### Questions for product
(bulleted list)

Do not invent detail you can't see or infer reasonably; note it as
"unclear from this screen" instead.
"""

DEMO_FLOW_OUTPUT = """\
### Per-screen findings

**Step 1 — Set pickup & dropoff**
- No visible way to swap pickup and dropoff once both are set.
- If this screen ships in Arabic/RTL, the search bar's mic icon and any directional map controls need explicit mirroring rules verified — don't assume the layout flip covers them.

**Step 2 — Choose ride type & confirm**
- Prices aren't shown with a currency symbol next to each option — easy to misread when scanning quickly, and ambiguous the moment this ships beyond one currency.
- No estimated wait time shown before the ride starts, only price.

**Step 3 — Track captain en route**
- "Cancel ride" is a plain text link — easy to miss, or worse, easy to tap by accident given its position.
- No "last updated" timestamp on the captain's live location — the same trust gap the ETA-jump feedback surfaced in usability testing.

### Flow gaps
- No state shown for the captain canceling or being reassigned after the ride is confirmed.
- No offline/reconnecting state if the network drops during tracking.
- No RTL-specific QA checkpoint anywhere in this flow — mirroring needs verifying screen by screen, not assumed from layout direction alone.
- No screen for what happens if no captains are available near the pickup point.

### Questions for engineering
- If the assigned captain cancels after confirmation, does the app auto-search for a new one, or does the user rebook from scratch?
- Is captain location pushed or polled, and what's the expected staleness on a weak connection?
- Does the RTL layout mirror per-component automatically, or does each screen need explicit rules for directional elements like the car's heading indicator?

### Questions for product
- Should a price estimate show before step 1 is even complete, or only once both pins are set?
- What's the policy when a ride is significantly delayed by captain reassignment — refund, discount, or nothing?
- Is "book for someone else" in scope for this flow, or a separate entry point?
"""

DEFAULT_FLOW_TEXT = """\
1. Set pickup & dropoff — map with two pins, search bar with mic icon, "Confirm locations" button
2. Choose ride type & confirm — list of ride options (Economy/Business) with prices, "Confirm ride" button
3. Track captain en route — live map, captain photo/name/plate, ETA, a plain-text "Cancel ride" link
"""


def image_to_data_url(uploaded_file) -> str:
    raw = uploaded_file.getvalue()
    b64 = base64.b64encode(raw).decode("utf-8")
    mime = uploaded_file.type or "image/png"
    return f"data:{mime};base64,{b64}"


def call_openai(api_key: str, prompt: str, text: str, images=None) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    content = [{"type": "text", "text": text}]
    for img in images or []:
        content.append(
            {"type": "image_url", "image_url": {"url": image_to_data_url(img)}}
        )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content


def call_anthropic(api_key: str, prompt: str, text: str, images=None) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    content = [{"type": "text", "text": text}]
    for img in images or []:
        raw = img.getvalue()
        b64 = base64.b64encode(raw).decode("utf-8")
        mime = img.type or "image/png"
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": b64},
            }
        )
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        system=prompt,
        messages=[{"role": "user", "content": content}],
    )
    return resp.content[0].text


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="AI Design Companion", page_icon="🧭", layout="wide")

st.title("🧭 AI Design Companion")
st.caption(
    "Summarize usability feedback into prioritized fixes, or review a flow's "
    "screens for end-to-end gaps — localization, RTL and dark-mode issues "
    "included by default."
)

tab1, tab2 = st.tabs(["Feedback Summarizer", "Screen & Flow Review"])

# --- Tab 1 ---
with tab1:
    with st.expander("Show the prompt this tool runs", expanded=False):
        st.code(SUMMARIZER_PROMPT, language="text")

    st.subheader("1. Feedback input")
    default_text = load_default_feedback()
    feedback_text = st.text_area(
        "Paste usability feedback (one quote per line), or use the pre-loaded "
        "dummy dataset from a fictional Middle-East ride-hailing app usability test:",
        value=default_text,
        height=220,
        key="feedback_text",
    )

    st.subheader("2. Run the Design Companion")
    mode = st.radio(
        "Mode",
        ["Demo mode (no API key needed)", "Live mode (use your own API key)"],
        horizontal=True,
        key="mode1",
    )

    if mode.startswith("Demo"):
        if st.button("Analyze feedback", type="primary", key="run1_demo"):
            st.markdown(DEMO_OUTPUT)
            st.info(
                "This is a pre-computed sample run so anyone viewing this demo "
                "can see real output without needing an API key. Switch to "
                "Live mode to run the prompt for real on your own text."
            )
    else:
        provider = st.selectbox("Provider", ["OpenAI", "Anthropic"], key="provider1")
        api_key = st.text_input(f"{provider} API key", type="password", key="key1")
        if st.button("Analyze feedback", type="primary", key="run1_live"):
            if not api_key:
                st.error("Add an API key to run live mode, or switch to Demo mode.")
            elif not feedback_text.strip():
                st.error("Paste some feedback first.")
            else:
                with st.spinner("Analyzing feedback..."):
                    try:
                        if provider == "OpenAI":
                            result = call_openai(api_key, SUMMARIZER_PROMPT, feedback_text)
                        else:
                            result = call_anthropic(api_key, SUMMARIZER_PROMPT, feedback_text)
                        st.markdown(result)
                    except Exception as e:
                        st.error(f"Something went wrong calling {provider}: {e}")

# --- Tab 2 ---
with tab2:
    st.subheader("1. Describe the flow, and/or upload screenshots")
    st.caption(
        "Add your screens in order below (as text), or upload real screenshots "
        "in order — screenshots are used instead of the text once you add any."
    )
    with st.expander("Show the prompt this tool runs", expanded=False):
        st.code(FLOW_PROMPT, language="text")

    flow_text = st.text_area(
        "Flow steps (one per line)",
        value=DEFAULT_FLOW_TEXT,
        height=140,
        key="flow_text",
    )
    uploaded_images = st.file_uploader(
        "Screenshots, in order (optional)",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="flow_images",
    )
    if uploaded_images:
        st.image(uploaded_images, width=120)

    st.subheader("2. Run the review")
    mode2 = st.radio(
        "Mode",
        ["Demo mode (no API key needed)", "Live mode (use your own API key)"],
        horizontal=True,
        key="mode2",
    )

    if mode2.startswith("Demo"):
        if st.button("Review this flow", type="primary", key="run2_demo"):
            st.markdown(DEMO_FLOW_OUTPUT)
            st.info(
                "This is a pre-computed sample run on the default 3-step ride "
                "flow above, so anyone viewing this demo sees real output "
                "without an API key or vision model access. Switch to Live "
                "mode to run it for real on your own flow or screenshots."
            )
    else:
        provider2 = st.selectbox("Provider", ["OpenAI", "Anthropic"], key="provider2")
        api_key2 = st.text_input(f"{provider2} API key", type="password", key="key2")
        if st.button("Review this flow", type="primary", key="run2_live"):
            if not api_key2:
                st.error("Add an API key to run live mode, or switch to Demo mode.")
            elif not flow_text.strip() and not uploaded_images:
                st.error("Describe your flow or upload screenshots first.")
            else:
                note = (
                    f"{len(uploaded_images)} screenshot(s) attached, in order — "
                    "use them as the primary source; the text below is context."
                    if uploaded_images
                    else "No screenshots attached — rely on the text description below."
                )
                user_text = f"{note}\n\n{flow_text}"
                with st.spinner("Reviewing flow..."):
                    try:
                        if provider2 == "OpenAI":
                            result = call_openai(
                                api_key2, FLOW_PROMPT, user_text, images=uploaded_images
                            )
                        else:
                            result = call_anthropic(
                                api_key2, FLOW_PROMPT, user_text, images=uploaded_images
                            )
                        st.markdown(result)
                    except Exception as e:
                        st.error(f"Something went wrong calling {provider2}: {e}")

st.divider()
st.caption(
    "Prototype for a design-tooling application challenge. Feedback and flow "
    "content shown by default are self-created dummy examples for a fictional "
    "Middle-East ride-hailing app (no real user, company or product data)."
)
