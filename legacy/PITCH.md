# ShadowBuyer — 3-minute demo script

**Target length:** 2:50 spoken, ≤3:00 total. **Rehearse out loud at least twice.** Time it.

**Browser setup before stage:**
- Single tab, full-screen, open to `https://<LIVE_URL>/swarm` (or `https://<LIVE_URL>/` if Zeabur deploy still pending).
- Backend running (Zeabur or fallback localhost). If both down, the frontend plays the deterministic mock — demo still works. Tag in header reads "demo · mock fallback" — that's fine.
- Second tab pre-loaded to `https://<LIVE_URL>/api/sponsor-health` for the sponsor question if a judge asks.
- Backup video ready in a third tab, scrubbed to 0:00.

**Stage left/right notes:** point at the screen on every dollar figure. The numbers do the work.

---

## 0:00 – 0:20 · Open *(memorize verbatim)*

> "Buying B2B software today is six weeks of demos, RFPs, security questionnaires, and pricing games.
>
> We collapsed it to six hours, with six agents.
>
> Category: observability tools. Demo vendor: Datadog. Watch."

**Stage action:** click **"Run the swarm →"** at 0:18. The status dot turns mint and starts pulsing. Pipeline pills light up.

---

## 0:20 – 0:50 · Scout + Quote Hunter

> "Agent one — **Scout**, running on Qwen via TokenRouter — pulled five observability vendors from Bright Data. G2 ratings, recent funding, outage history.
>
> Agent two — **Quote Hunter**, running through Actionbook — already filled the Contact Sales form. Datadog's AE Morgan Chen quoted us **$2,340 per host per year** with a ten percent discount. New Relic came back at **$1,920**.
>
> Every vendor on the planet trash-talks their competitors. We capture it. Datadog's AE called Honeycomb 'a toy that falls over above a hundred hosts.' That's a quote. We use it."

**Stage action:** point at the Datadog vendor stats row as numbers populate. Hosts 500. List $195. Live target ticks down from $175.50.

---

## 0:50 – 1:40 · Adversarial negotiator *(the highlight — give it air)*

> "Now the part you haven't seen before.
>
> Two agents disagree on stage about how to negotiate.
>
> On the left — **Hardball**, running Qwen3-Max. Plays the leverage game. Cheaper quote on the table, quarter-end clock, fallback POC at Honeycomb already provisioned.
>
> On the right — **Diplomat**, running Z.ai's GLM-5.1. Plays the partnership angle. Three-year deal, reference customer, conference speaking slot.
>
> Watch the price walk down round by round."

**Stage action:** **wait.** Let the three rounds of Hardball/Diplomat cards stream in. The live target ticker should walk from $175.50 down to $157.50 over the streamed turns. Don't talk over it.

> "Three rounds. Six turns. The **Referee** — also Qwen — picks the winning play.
>
> Hardball opens, Diplomat closes. Lock the price with leverage; lock the term with partnership.
>
> Final number: **$157.50 per host per month**, down from $195 list. **Twenty-five-point-two thousand dollars saved annually at five hundred hosts.** Nineteen percent off list."

**Stage action:** point at the amber Referee verdict card's 4-metric grid. Read "Annual savings: $225,000" out loud.

---

## 1:40 – 2:10 · Email goes to the AE

> "And email goes to the AE."

**Stage action:** scroll down to reveal the email card. Pause. Let judges read the subject line.

> "We didn't just decide the price internally. We drafted the email Morgan is opening on Monday morning. Subject line: *'Datadog — closing by Friday at $157.50 per host.'* Body cites the New Relic offer, the quarter-end deadline, the Honeycomb fallback. Every leverage point the Referee picked, in the actual outbound text.
>
> Dry-run on stage. One click to send."

---

## 2:10 – 2:40 · Contract Diff

> "Last agent — **Contract Diff**, Qwen plus Nosana embeddings.
>
> Datadog sends their MSA. Our agent compares it to our standard template.
>
> **Fifteen deviations** flagged. Severity coded. Recommended counter-text for every one.
>
> Including — and this is the one — **a ninety-day auto-renewal trap** instead of our thirty. And **a missing data-deletion clause** entirely. Both flagged high severity. In four seconds.
>
> A procurement lawyer charges nine hundred dollars an hour to find these. We do it before lunch."

**Stage action:** scroll to Contract Diff panel. Point at the two high-severity rows: auto-renewal and data-deletion.

---

## 2:40 – 3:00 · Close *(memorize verbatim)*

> "Procurement is a five trillion dollar market.
>
> Every CFO in this room has lost a quarter to this.
>
> Question for the judges: how many software contracts did you sign last year?
>
> Would you sign the next one with us?"

**Stage action:** stop talking. Hold the verdict card on screen until the moderator signals.

---

## If something breaks

| Situation | Move |
|---|---|
| Backend down, frontend shows "demo · mock fallback" tag | Keep going. The mock plays identical numbers. Don't mention it. |
| Frontend won't load at all | Switch to the **backup video** tab. Cut in at 0:30 of the recording. |
| Live URL 500 / Zeabur red | Backup video, full play. Don't try to fix on stage. |
| Judge interrupts mid-pitch with sponsor question | Open `/api/sponsor-health` tab. "All 11 wired. Every LLM call routes through TokenRouter, memory in Evermind, embeddings on Nosana, deployed on Zeabur. Built with Qoder. Source on GitHub." |
| Judge asks "is this real or fake" | Show `/api/sponsor-health`. Show the GitHub repo. Show the live URL. "Mock fallback exists so the demo cannot crash, but the live path is fully wired — drop one env var and Hardball is calling Qwen Cloud through TokenRouter for real." |

---

## Phrasing rules

- Read every dollar figure **slowly**. Numbers are the only thing judges remember.
- Pause for two beats after "$225,000." Let them feel it.
- Never apologize. Never say "as you can see" or "obviously."
- If you mess up a number, **don't correct yourself.** Keep going. Nobody will remember.
- Eye contact at the close. Look at one judge per sentence.

## Three things to hammer

1. **Six weeks → six hours.** Open with it.
2. **Two agents disagree on stage.** That's the innovation.
3. **$225,000 saved on one deal.** That's the ask.

Everything else is texture.
