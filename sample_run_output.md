# Sample runs

Dataset: `feedback_dummy.csv` — 18 self-created dummy usability-test quotes
for a fictional Middle-East ride-hailing app, across 9 tasks (booking,
payment, tracking, cancellation, Arabic/RTL language switch, onboarding,
network drop).

## Run 1 — Feedback Summarizer

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

## Run 2 — Screen & Flow Review

Input: a 3-step ride-booking flow (text description; the live tool also
accepts real screenshots).

1. Set pickup & dropoff — map with two pins, search bar with mic icon, "Confirm locations" button
2. Choose ride type & confirm — list of ride options (Economy/Business) with prices, "Confirm ride" button
3. Track captain en route — live map, captain photo/name/plate, ETA, a plain-text "Cancel ride" link

**Per-screen findings**

- *Step 1:* No visible way to swap pickup and dropoff once both are set. If this ships in Arabic/RTL, the mic icon and any directional map controls need explicit mirroring rules verified — don't assume the layout flip covers them.
- *Step 2:* Prices aren't shown with a currency symbol next to each option. No estimated wait time shown before the ride starts, only price.
- *Step 3:* "Cancel ride" is a plain text link — easy to miss, or worse, easy to tap by accident. No "last updated" timestamp on the captain's live location — the same trust gap the ETA-jump feedback surfaced.

**Flow gaps**
- No state for the captain canceling or being reassigned after confirmation.
- No offline/reconnecting state if the network drops during tracking.
- No RTL-specific QA checkpoint anywhere in this flow — mirroring needs verifying screen by screen.
- No screen for "no captains available near this pickup point."

**Questions for engineering**
- If the assigned captain cancels after confirmation, does the app auto-search for a new one, or does the user rebook from scratch?
- Is captain location pushed or polled, and what's the expected staleness on a weak connection?
- Does the RTL layout mirror per-component automatically, or does each screen need explicit rules for directional elements like the car's heading indicator?

**Questions for product**
- Should a price estimate show before step 1 is even complete, or only once both pins are set?
- What's the policy when a ride is significantly delayed by captain reassignment — refund, discount, or nothing?
- Is "book for someone else" in scope for this flow, or a separate entry point?

---
*Generated from the prompts in `design_companion_prompt.md`. Both are shown live in the artifact demo and as "Demo Mode" in the Streamlit app.*
