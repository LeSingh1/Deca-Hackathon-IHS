import { EVENT_TYPES, type SwarmEvent } from "./contract";

export type Pace = "presenter" | "fast";
export const DEMO_PHONE = "+1 (718) 555-0142";

export async function getServices(): Promise<Record<string, string>> {
  try {
    const r = await fetch("/api/services");
    return r.ok ? ((await r.json()) as Record<string, string>) : {};
  } catch {
    return {};
  }
}

export async function startDemo(pace: Pace): Promise<string | null> {
  try {
    const r = await fetch(`/api/demo/start?pace=${pace}`, { method: "POST" });
    if (!r.ok) return null;
    const j = (await r.json()) as { run_id: string | null };
    return j.run_id;
  } catch {
    return null;
  }
}

/** Replies carry the run id: everyone on a shared demo has the same phone number. */
export async function sendSms(body: string, runId: string | null): Promise<boolean> {
  try {
    const r = await fetch("/api/sms/inbound", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from: DEMO_PHONE, body, run_id: runId }),
    });
    return r.ok;
  } catch {
    return false;
  }
}

/** Subscribe to a run's SSE stream. Returns an unsubscribe function. */
export function subscribe(runId: string, onEvent: (ev: SwarmEvent) => void): () => void {
  const es = new EventSource(`/api/runs/${runId}/events`);
  const handler = (e: MessageEvent<string>) => {
    const ev = JSON.parse(e.data) as SwarmEvent;
    onEvent(ev);
    if (ev.event === "done") es.close();
  };
  for (const t of EVENT_TYPES) es.addEventListener(t, handler as EventListener);
  return () => es.close();
}
