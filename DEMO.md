# 3-minute demo script

**Recorded version:** [demo/shadowbuyer-demo.mp4](demo/shadowbuyer-demo.mp4).

**Setup:** open the app at 1080p, **Presenter ~75s** selected, light ("Paper") theme. Phone on the left, command center on the right. The backup recording is the same run in Fast mode.

---

### 0:00–0:20 · The money being lost

> "This is Maria. She owns Mario's Trattoria in Brooklyn and does about $1.2 million a year on cards, at a 3 to 4 percent margin. The 2 to 3 percent she pays on every swipe is about as much as she keeps in profit. And this week a lender texted her a '$40,000 in 24 hours, simple 1.35 factor' offer."

> "She doesn't need another dashboard. She needs someone to fight for her, over text."

### 0:20–0:40 · She texts a photo

Click **Run demo: Mario's Trattoria** (or "Send October statement photo" on the phone).

> "She texts a photo of her October statement. That's the whole interface."

Point at the **scan line** on the photo and the **line items peeling** into *The statement, line by line*.

### 0:40–1:00 · Hidden fees, stamped

Point at the **Hidden fees** column as the stamps land, and the hero tile **Fees you can fight**.

> "Twelve lines. The Fee Hunter stamps the ones she can fight: tier surcharges, a made-up 'regulatory' fee, a PCI non-compliance fee she pays until she fills out a free questionnaire. **$1,204 a month.** Her all-in rate is **3.28%**." *(hero tile: You pay today)*

### 1:00–1:20 · What fair looks like

Point at **What a fair price looks like**.

> "The Rate Scout benchmarks her against fair interchange-plus pricing and two competitor quotes. These are labeled illustrative, with source and date. Switching to Harbor looks best on paper, but hold that thought."

### 1:20–1:55 · The negotiation duel

Point at the two lanes streaming, and the **tug-of-war knots** moving right.

> "Two negotiators work her processor's retention rep at the same time. Hardball uses the competitor quote and threatens to switch. Diplomat leans on loyalty and growth. The rep pushes back, and every offer it makes is priced by our calculator, not by the model."

Referee card lands:

> "The Referee compares four options on first-year dollars. **Switching costs $11,090 in exit traps**: liquidated damages, an ETF, and a lease she can't cancel. That leaves her **$316 behind**. Hardball got **2.49%** with the exit traps waived: **$9,454 a year**, nothing up front."

### 1:55–2:25 · The cash advance, translated

Point at the **split-flap** flipping from `1.35x` to **93% APR** (hero tile and panel) and the paydown chart drawing in.

> "That 'simple 1.35 factor'? It takes $197 out of her account every single day, and she only receives $38,800. The real cost is **about 93% APR**. That's an IRR on the daily cash flows, checked against a spreadsheet in our tests."

Point at **Contract traps, marked up**: strike-throughs and rewrites, **$ at risk** tag.

> "The Contract Exposer marks up both documents: a confession of judgment, a blanket lien, the auto-renewal. Every one comes with replacement language she can ask for."

### 2:25–2:50 · YES → money moves

Point at the phone. The 3-line summary has arrived:

> "Found $1,204/mo… that offer is really ~93% APR… I got Keystone down to 2.49% = $9,454/yr back. Reply YES."

> "Nothing leaves the building until she says so."

Optional: type a question like "what does this mean?" first. It isn't treated as a yes or a no; ShadowBuyer re-asks and the deal stays open.

Tap **YES** on the phone.

Point at **Your YES, and the money moves**: the receipts ($48.20 ticket: **$1.58 → $1.20**), the coin moving **Processor fees → Back in your pocket → Tax & Rainy-Day reserve**, and the **$787.83** sandbox sweep.

> "Month one's savings, $787.83, sweeps into her rainy-day reserve. It's sandboxed today, Stripe test mode with a key and a labeled mock without one, with FedNow instant payments as the production rail. And she gets this."

Click **Download lender-ready PDF**.

### 2:50–3:00 · Close

> "One text in, one YES back. $9,454 a year, and a 93% APR loan she didn't sign. Every number you saw came from tested code, not from a model."

---

## "How is this different from an expense tracker?" (20 seconds)

> "An expense tracker shows Maria where her money went. ShadowBuyer gets it back. It reads the statement, finds the fees she can fight, negotiates with the processor, exposes the true APR before she signs, and after one YES by text it moves the money and hands her a lender-ready report. There's no dashboard for her to learn, no categories, no charts to interpret. The outcome is $9,454 a year back in her account."

## Backup plan

- **Zero keys needed.** If wifi or an API key fails, everything runs on deterministic fixtures with the same numbers. Header chips show `mock`.
- **Fast mode** (~10 s) for a quick re-run; **New run** resets.
- The PDF is generated server-side and works offline.
