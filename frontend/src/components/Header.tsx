import type { Pace } from "../lib/api";

export type Theme = "system" | "light" | "dark";
const SERVICE_LABEL: Record<string, string> = { claude: "Claude", stripe: "Stripe", twilio: "Twilio", memory: "Memory" };

export function Header({
  services,
  pace,
  setPace,
  theme,
  setTheme,
  cost,
  costLive,
  canRestart,
  onRestart,
}: {
  services: Record<string, string>;
  pace: Pace;
  setPace: (p: Pace) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  cost: number;
  costLive: boolean;
  canRestart: boolean;
  onRestart: () => void;
}) {
  const nextTheme: Theme = theme === "system" ? "dark" : theme === "dark" ? "light" : "system";
  return (
    <header className="top">
      <div className="brand">
        <b>ShadowBuyer</b>
        <span>for Main Street</span>
      </div>
      <div className="chips" aria-label="Service status">
        {Object.entries(services).map(([k, v]) => (
          <span key={k} className={`chip ${v === "live" ? "live" : ""}`} title={`${SERVICE_LABEL[k] ?? k}: ${v}`}>
            <i aria-hidden="true" />
            {SERVICE_LABEL[k] ?? k} · {v}
          </span>
        ))}
      </div>
      <span className="cost" aria-live="off">
        Run cost <span className="num">${cost.toFixed(4)}</span> {costLive ? "" : "(mock)"}
      </span>
      <div className="seg" role="group" aria-label="Pacing">
        <button aria-pressed={pace === "presenter"} onClick={() => setPace("presenter")}>Presenter ~75s</button>
        <button aria-pressed={pace === "fast"} onClick={() => setPace("fast")}>Fast ~10s</button>
      </div>
      <button className="iconbtn" onClick={() => setTheme(nextTheme)} aria-label={`Theme: ${theme}. Switch to ${nextTheme}`}>
        {theme === "system" ? "Auto" : theme === "dark" ? "Ink" : "Paper"}
      </button>
      {canRestart && (
        <button className="iconbtn" onClick={onRestart}>New run</button>
      )}
    </header>
  );
}
