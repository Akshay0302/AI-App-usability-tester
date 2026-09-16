# AI Design Companion — Usability Feedback Summarizer + Screen & Flow Review

Challenge 1 (Design Companion): an AI prototype that summarizes usability
feedback and reviews a flow's screens — built with a multi-vertical,
Middle-East-market super app in mind, so localization, RTL, currency and
dark-mode gaps are surfaced by default, not on request.

## What's in this folder

| File | What it is |
|---|---|
| `feedback_dummy.csv` | Self-created dummy dataset — 18 usability-test quotes from a fictional ride-hailing app, across 9 tasks (booking, payment, tracking, cancellation, Arabic/RTL switch, onboarding, network drop). |
| `design_companion_prompt.md` | Both prompts in full, plus the reasoning behind each instruction. |
| `sample_run_output.md` | Both prompts' output when run — themes/severity/fixes for the feedback tool, and per-screen findings/gaps/questions for the flow tool. |
| `app.py` / `requirements.txt` | A Streamlit app with two tabs: **Feedback Summarizer** and **Screen & Flow Review** (upload real screenshots or describe steps as text). Both ship with a no-key "Demo mode" and a "Live mode" that calls your own OpenAI or Anthropic key, vision included. |

**Live, working demo (no setup, no API key):** a browser version of both
tools, published as a Claude artifact — it calls Claude directly from the
page, including live image analysis when you upload screenshots. This is
the fastest way for a reviewer to actually try it.

## Running the Streamlit app locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploying it publicly (free, ~3 minutes)

1. Push this folder to a public GitHub repo.
2. Go to https://share.streamlit.io → "New app" → point it at the repo and `app.py`.
3. Deploy. You'll get a public `*.streamlit.app` URL to submit.

Demo mode works immediately with no configuration. Live mode just needs
you (or a reviewer) to paste an API key into the app — it's never stored
anywhere, only used for that session's request. `design_companion.zip` in
this folder bundles everything here into one file if that's easier to
upload to GitHub or attach to an application.

## What each tool does

**Feedback Summarizer** — pastes in raw usability-test quotes, clusters
them into 4–6 themes, rates each by real-world severity, and proposes one
concrete fix per theme, plus a "quick wins" list. Localization/RTL/
currency/dark-mode issues are called out as first-class findings whenever
the feedback raises them, not folded into generic "polish" notes.

**Screen & Flow Review** — takes a flow's screens (real screenshots, or a
text description of each step) and returns per-screen usability findings,
an end-to-end gap list (missing states a real product needs — offline,
reassignment, no-availability, etc.), and clarifying questions split
between what to ask engineering vs. product before it ships. This is the
part aimed at shipping *complete* flows — states, edge cases and
localization considered by default, the way a senior designer's handoff
should read.

## Submission summary (100 words)

AI Design Companion turns raw usability feedback and flow screenshots into
fast, shippable design action for a multi-vertical super app. One tool
clusters usability-test feedback into severity-ranked themes with concrete
fixes; the other reviews a flow's screens end-to-end, surfacing missing
states (offline, reassignment, no-availability) and the exact questions to
ask engineering vs. product before it ships — with localization, RTL,
currency and dark-mode gaps treated as first-class findings throughout,
not edge cases. Built two ways: a live in-browser demo (calls Claude
directly, zero setup, images included) and a Streamlit app with a
swappable OpenAI/Anthropic key.
