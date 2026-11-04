# Backup video storyboard

**Hard requirement from the project doc:** record this at 3:30 PM. If the live demo crashes on stage, cut in at the 90-second mark. **Do not skip this step.**

**This file replaces the live demo entirely.** It must stand alone — no voice-over edits, no second takes. Record clean, end-to-end, once. ~2 minutes 30 seconds of screen time, optional voice-over.

---

## Tools

- **macOS:** QuickTime → File → New Screen Recording → record selection. Or `Cmd+Shift+5` → "Record Selected Portion." Pick the browser window only.
- **Linux:** OBS Studio, single window source, 1080p, 30fps.
- **Windows:** `Win+G` (Xbox Game Bar) → Record. Or OBS.
- **Output:** MP4, H.264, 1080p, 30fps. File size <100 MB. Save to `~/Desktop/shadowbuyer-backup-demo.mp4`.

## Pre-record setup

1. **Backend up.** `curl https://<LIVE_URL>/healthz` returns `{"ok": true, ...}`. If not, use `cd ~/Claude/projects/shadowbuyer && uvicorn src.app:app --port 8000` locally and point the frontend at `localhost`.
2. **Frontend up.** `cd ~/Claude/projects/visual-procurement-studio && bun dev`. Open `http://localhost:5173/swarm` in a clean Chrome window. Close all other tabs.
3. **Window size.** Maximize the browser. Force `F11` fullscreen if QuickTime captures chrome. Hide the bookmark bar (`Cmd+Shift+B`).
4. **Browser zoom.** `Cmd+0` to reset. Then `Cmd+=` twice (110% zoom) so text reads on a projector.
5. **Network throttling off.** Open DevTools → Network → "No throttling." Close DevTools before recording.
6. **Sponsor health pre-check.** Verify `https://<LIVE_URL>/api/sponsor-health` returns `all_eleven_wired: true`. Sponsor chips on `/swarm` will light up correctly.
7. **Test run.** Click "Run the swarm →" once before recording to warm the backend cache and make sure all turns stream in.

---

## Shot list (exact clicks + timing)

| Time | Action | What's on screen | Voice-over (optional) |
|---|---|---|---|
| **0:00–0:05** | Start recording. Hero already on screen, status dot dark. | `ShadowBuyer · ready` header, tagline "Six weeks of demos and contract games. Collapsed to six hours." visible. | "ShadowBuyer. Six weeks of B2B procurement collapsed to six hours with six agents." |
| **0:05–0:08** | Move cursor to **"Run the swarm →"** button. | Cursor visible, button highlighted. | (silence — let the next beat carry) |
| **0:08** | **Click "Run the swarm →"** | Status dot turns mint and pulses. Pipeline pill "Scout" lights up. | "Watch." |
| **0:08–0:18** | Don't move. Pipeline pills fire: Scout → Quote Hunter → Negotiator. Stats row populates: Datadog, New Relic, 500 hosts, $195 list. | Live target ticker animates from $175.50 with a spring. | "Scout pulls five observability vendors from Bright Data. Quote Hunter has Datadog's AE quote: $2,340 per host per year." |
| **0:18–0:30** | **Hardball Round 1** card slides in on left. Read the headline visually. | Red coral card, headline "Open with competitor on the table," body cites New Relic at $160. Live ticker drops to $160. | "Hardball plays the competitor card." |
| **0:30–0:42** | **Diplomat Round 1** card slides in on right. Mint green. | Ticker drops to $158. | "Diplomat plays the partnership card. Three-year deal, reference customer." |
| **0:42–0:52** | **Hardball R2** and **Diplomat R2** stream in. | Ticker walks down through $158.50 → $155. | "Hardball escalates: CFO froze SaaS spend. Diplomat sweetens: case study, conference slot." |
| **0:52–1:08** | **Hardball R3** and **Diplomat R3**. | Ticker lands at $157.50. | "Hardball closes: deadline Friday or we sign with New Relic. Diplomat counters: 36 months, price-lock, expansion rights." |
| **1:08–1:18** | **Referee verdict** card scales in (amber, full-width). Scroll down only slightly to keep it framed. | Verdict: "HARDBALL opens, DIPLOMAT closes." 4 metric tiles: $157.50 / 19.2% / $225,000 / hardball. | "Referee picks the winning play. Hardball opens, Diplomat closes. Final: $157.50 per host. $225,000 saved." |
| **1:18–1:38** | **Scroll down slowly** to the email card. Pause for 3 seconds with the email card centered. | Email to morgan.chen@datadog.com, subject "Datadog — closing by Friday at $157.50/host," body in mono. | "And email goes to the AE. Subject, body, leverage points. Dry-run on stage. One click to send." |
| **1:38–2:08** | **Scroll down** to Contract Diff panel. Stop with the top 3 high-severity rows in frame. | 15 redlines counter, severity pills (high 7, med 6, low 2). Top rows: Auto-Renewal (high), Data Deletion on Termination (high). | "Contract Diff: 15 deviations in Datadog's MSA. Auto-renewal trap at 90 days. Missing data-deletion clause. Both high severity. Four seconds." |
| **2:08–2:18** | **Scroll down** past the redlines to the **sponsor strip**. Slow scroll. | All 11 sponsor chips visible. Some green, some neutral. | "Eleven sponsors. Real code references. Audit at slash A-P-I slash sponsor health." |
| **2:18–2:30** | **Stop scrolling.** Hold on sponsor strip + footer for 5 seconds. Stop recording. | Sponsor strip + GitHub link visible. | "Procurement is a $5T market. Would you sign your next software contract with us?" |

**Total recording length:** ~2:30. The pitch script is ~2:50. **The video is shorter than the live pitch on purpose** so you can cut in at the 90-second mark and still finish on time.

---

## What NOT to do

- ❌ Don't open DevTools mid-recording. Network panel reveals which calls are mocked.
- ❌ Don't click anything else on the page (no scrolling away, no clicking sponsor chips, no opening links).
- ❌ Don't speak over the negotiation streams. Let the price ticker animation breathe.
- ❌ Don't try to record voice-over and screen in the same pass unless you've practiced. Record silent, add VO in a second pass via QuickTime → Edit → Add Audio if needed.
- ❌ Don't include the URL bar in the recording if it leaks env vars or admin paths.

---

## Final-pass checklist

After recording, watch the full thing once before saving:

- [ ] Plays from black, ends on black. No frames of "Recording stopped" overlay.
- [ ] Status dot pulses live throughout.
- [ ] Every Hardball card and every Diplomat card streams in fully.
- [ ] Live price ticker reaches **$157.50** by the time the Referee card appears.
- [ ] Referee verdict shows **$225,000 annual savings** clearly.
- [ ] Email card shows **morgan.chen@datadog.com** and the **$157.50** body line.
- [ ] Contract Diff shows **15** redlines, **7 high**, with auto-renewal AND data-deletion visible.
- [ ] Sponsor strip shows **all 11** names.
- [ ] Final file: MP4, <100 MB, plays in QuickTime + VLC.

---

## Where to put it

- On the **demo laptop**: `~/Desktop/shadowbuyer-backup-demo.mp4`. Pin to dock.
- Pre-load in a **second browser tab**: drag the file onto Chrome → tab plays inline.
- **Scrub to 0:00** before the live pitch starts. If live crashes, switch tabs and press space.

---

## Where to cut in if live breaks

| Live crash point | Cut to backup video at |
|---|---|
| Backend down before "Run the swarm" click | **0:00** — start from the top |
| Backend up but SSE disconnects mid-negotiation | **0:45** — Hardball R2 |
| Negotiator works but email card 500s | **1:18** — start of email |
| Contract Diff panel renders empty | **1:38** — start of Contract Diff |
| Everything renders but page freezes mid-pitch | **whatever is on screen now** — cut to the matching beat |

The video's beats are timed to match the live pitch. Wherever you cut in, the script keeps working.
