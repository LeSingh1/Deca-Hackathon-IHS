# Demo script

The video ([demo/shadowbuyer-demo.mp4](demo/shadowbuyer-demo.mp4)) is **silent on purpose**: no voice, sound, captions or title cards. It's slow enough to talk over in person. Use this table as the talk track, or run the app live with **Presenter ~75s** selected and say the same things.

| Video | On screen | Say |
|---|---|---|
| 0:00 | **Overview** | "This is Maria. She owns Mario's Trattoria in Brooklyn, a fictional restaurant doing about $1.2 million a year on cards, at a 3 to 4 percent margin. The 2 to 3 percent she pays on every swipe is about as much as she keeps in profit. And this week a lender offered her $40,000 in 24 hours at a simple 1.35 factor." |
| 0:14 | **Owner texts**: the photo gets scanned | "She doesn't need another dashboard. She needs someone to fight for her, over text. She texts a photo of her October statement, and that's her whole interface." |
| 0:26 | **Statement**: fees get stamped | "The Fee Hunter stamps the ones she can fight: tier surcharges, a made-up regulatory fee, a PCI fee she pays until she fills out a free questionnaire. That's $1,204 a month." |
| 0:45 | **Quotes** | "The Rate Scout puts her all-in rate at 3.28% and benchmarks it against fair pricing and two competitor quotes, labeled illustrative. Switching to Harbor looks best on paper. Hold that thought." |
| 0:58 | **Negotiation log**: both columns stream | "Two negotiators work a simulated retention rep side by side. Hardball uses the competitor quote and threatens to switch. Diplomat leans on loyalty and growth. Every offer is priced by our calculators, not by a model." |
| ~1:31 | **Referee verdict** | "The Referee compares four options on first-year dollars. Switching costs $11,090 in exit traps, leaving her $316 behind. Hardball got 2.49% with those traps waived: $9,454 a year." |
| 1:52 | **Cash advance** | "That simple 1.35 factor takes $197 from her account every day, and she only receives $38,800. The real cost is about 93% APR, an IRR on the daily cash flows." |
| 2:07 | **Contracts**: redlines land | "The Contract Exposer marks up both documents: the auto-renewal, a confession of judgment, a blanket lien. Every trap comes with replacement language she can ask for." |
| 2:39 | **Savings**, before YES | "A draft email to the rep is ready, but nothing leaves the building until she says so." |
| 2:51 | **Owner texts**: three-line summary | "She gets three lines by text." |
| 3:03 | She asks a question | "If she asks a question, that's neither a yes nor a no. Nothing moves, and the deal stays open." |
| 3:09 | She taps YES, **Savings** | "She taps YES. On a $48.20 ticket her fee drops from $1.58 to $1.20. Month one's savings, $787.83, sweep into her rainy-day reserve. This is sandboxed, so no real money moves." |
| 3:32 | **The PDF** | "She also gets a lender-ready report: every statement line, the options compared, the true cost of the advance, and each contract trap with the change to ask for." |
| 3:53 | **Overview**, finished | "One text in, one YES back. Every number you saw came from tested code, not from a model." |
| 4:02 | **Service health** | "This recording runs on deterministic fixtures, with no API keys. Add a key and every agent runs on Claude." |
| 4:10 | **Second run**, Fast ~10s | "Next month's run is smarter. The whole swarm runs in about ten seconds." |
| 4:27 | **Negotiation log**: first Hardball line | "The winning negotiator now opens from what worked last time, while the offers still come from the same calculators." |
| 4:37 | She taps NO, then **Savings** | "And if she says no, nothing is sent and no money moves." |

## "How is this different from an expense tracker?" (20 seconds)

> "An expense tracker shows Maria where her money went. ShadowBuyer gets it back. It reads the statement, finds the fees she can fight, negotiates with the processor, exposes the true APR before she signs, and after one YES by text it moves the money and hands her a lender-ready report. The outcome is $9,454 a year back in her account."

## If someone asks

- **Is the negotiation real?** No. The rep is simulated, bound to a fixed ladder of offers priced by the calculators. Nobody real is contacted.
- **Did real money move?** No. The sweep is a labeled mock here, or Stripe test mode with a test key.
- **Did Claude write these answers?** Not in this recording. The sidebar shows `mock`: every agent is on fixtures. With a key they run live; see the README for what's been verified.

## Backup plan

- **Zero keys needed.** If wifi or an API key fails, everything runs on deterministic fixtures with the same numbers. The sidebar shows `mock`.
- **Fast ~10s** for a quick re-run; **New run** resets.
- The PDF is generated server-side and works offline. The app's fonts load from Google Fonts, so offline it falls back to system fonts.
