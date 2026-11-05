# Demo script

The video ([demo/shadowbuyer-demo.mp4](demo/shadowbuyer-demo.mp4)) is **silent on purpose**: no voice, sound, captions or title cards. It's slow enough to talk over in person, and it's recorded with real Claude on every agent. Use this table as the talk track, or run the app live with **Presenter** selected and say the same things.

| Video | On screen | Say |
|---|---|---|
| 0:00 | **Overview** | "This is Maria. She owns Mario's Trattoria in Brooklyn, a fictional restaurant doing about $1.2 million a year on cards, at a 3 to 4 percent margin. The 2 to 3 percent she pays on every swipe is about as much as she keeps in profit. And this week a lender offered her $40,000 in 24 hours at a simple 1.35 factor." |
| 0:14 | **Owner texts**: the photo gets scanned | "She doesn't need another dashboard. She needs someone to fight for her, over text. She texts a photo of her October statement, and that's her whole interface." |
| 0:28 | **Statement**: fees get stamped | "The Fee Hunter stamps the ones she can fight: tier surcharges, a made-up regulatory fee, a PCI fee she pays until she fills out a free questionnaire. That's $1,204 a month." |
| 0:47 | **Quotes** | "The Rate Scout puts her all-in rate at 3.28% and benchmarks it against fair pricing and two competitor quotes, labeled illustrative. Switching to Harbor looks best on paper. Hold that thought." |
| 1:00 | **Negotiation log**: both columns stream | "Two negotiators work a simulated retention rep side by side. Hardball uses the competitor quote and threatens to switch. Diplomat leans on loyalty and growth. Every offer is priced by our calculators, not by a model." |
| 1:16 | **Referee verdict** | "The Referee compares four options on first-year dollars. Switching costs $11,090 in exit traps, leaving her $316 behind. Hardball got 2.49% with those traps waived: $9,454 a year." |
| 1:37 | **Cash advance** | "That simple 1.35 factor takes $197 from her account every day, and she only receives $38,800. The real cost is about 93% APR, an IRR on the daily cash flows." |
| 1:52 | **Contracts**: redlines land | "The Contract Exposer marks up both documents: the auto-renewal, a confession of judgment, a blanket lien. Every trap comes with replacement language she can ask for." |
| 2:24 | **Savings**, before YES | "A draft email to the rep is ready, but nothing leaves the building until she says so." |
| 2:36 | **Owner texts**: three-line summary | "She gets three lines by text." |
| 2:48 | She asks a question | "If she asks a question, that's neither a yes nor a no. Nothing moves, and the deal stays open." |
| 2:54 | She taps YES, **Savings** | "She taps YES. On a $48.20 ticket her fee drops from $1.58 to $1.20. Month one's savings, $787.83, sweep into her rainy-day reserve. This is sandboxed, so no real money moves." |
| 3:17 | **The PDF** | "She also gets a lender-ready report: every statement line, the options compared, the true cost of the advance, and each contract trap with the change to ask for." |
| 3:37 | **Overview**, finished | "One text in, one YES back. Every number you saw came from tested code, not from a model." |
| 3:47 | **Service health** | "Every agent in this recording ran live on Claude. Stripe and Twilio are sandboxed. With no keys at all, the app still runs on fixtures with the same numbers." |
| 3:54 | **Second run**, Fast | "Next month's run is smarter." (The video skips about a minute of waiting on the API at 4:09.) |
| 4:16 | **Negotiation log**: first Hardball line | "Hardball now opens with what it remembers: Keystone already offered 2.49% last time. The offers still come from the same calculators." |
| 4:25 | She taps NO, then **Savings** | "And if she says no, nothing is sent and no money moves." |

## "How is this different from an expense tracker?" (20 seconds)

> "An expense tracker shows Maria where her money went. ShadowBuyer gets it back. It reads the statement, finds the fees she can fight, negotiates with the processor, exposes the true APR before she signs, and after one YES by text it moves the money and hands her a lender-ready report. The outcome is $9,454 a year back in her account."

## If someone asks

- **Is the negotiation real?** No. The rep is simulated, bound to a fixed ladder of offers priced by the calculators. Nobody real is contacted.
- **Did real money move?** No. The sweep is a labeled mock here, or Stripe test mode with a test key.
- **Did Claude write these answers?** Yes. Every agent ran live on Claude in this recording, and the sidebar shows `Claude · live`. Stripe and Twilio show `mock`: they're sandboxed. The money figures come from the calculators, not the models.

## Backup plan

- **Zero keys needed.** If wifi or an API key fails, everything runs on deterministic fixtures with the same numbers. The sidebar shows `mock`. A live run needs `ANTHROPIC_API_KEY` set and takes about 80 seconds more for the API calls.
- **Fast ~10s** for a quick re-run; **New run** resets.
- The PDF is generated server-side and works offline. The app's fonts load from Google Fonts, so offline it falls back to system fonts.
