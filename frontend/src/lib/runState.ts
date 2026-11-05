import type {
  ActionExecuted,
  AprRevealed,
  ApprovalReceived,
  ApprovalRequested,
  Draft,
  FeeFlagged,
  Lane,
  LedgerUpdate,
  LineItem,
  Offer,
  OwnerMessage,
  RateComputed,
  Redline,
  RefereeVerdict,
  Speaker,
  Stage,
  Summary,
  SwarmEvent,
} from "./contract";

export const STAGES: { key: Stage; title: string; who: string }[] = [
  { key: "statement_reader", title: "Read statement", who: "Statement Reader" },
  { key: "fee_hunter", title: "Hunt fees", who: "Fee Hunter" },
  { key: "rate_scout", title: "Benchmark", who: "Rate Scout" },
  { key: "negotiator", title: "Negotiate", who: "Hardball · Diplomat · Referee" },
  { key: "contract_exposer", title: "Expose traps", who: "Contract Exposer" },
  { key: "action_drafter", title: "Draft", who: "Action Drafter" },
  { key: "approval", title: "Owner says YES", who: "Owner" },
  { key: "executor", title: "Move money", who: "Executor" },
];

export type StageStatus = "pending" | "active" | "done";
export interface StageState {
  status: StageStatus;
  label?: string;
  model?: string | null;
  live?: boolean;
  note?: string | null;
}

export interface Turn {
  round: number;
  speaker: Speaker;
  text: string;
  done: boolean;
  offer?: Offer | null;
}

export interface RunState {
  runId: string | null;
  status: "idle" | "starting" | "running" | "awaiting" | "done" | "error";
  services: Record<string, string>;
  stages: Record<Stage, StageState>;
  active: Stage | null;
  messages: OwnerMessage[];
  lineItems: LineItem[];
  totalItems: number;
  flagged: FeeFlagged[];
  hiddenTotal: number;
  rate: RateComputed | null;
  lanes: Record<Lane, Turn[]>;
  verdict: RefereeVerdict | null;
  apr: AprRevealed | null;
  redlines: Redline[];
  draft: Draft | null;
  approval: ApprovalRequested | null;
  approvalReceived: ApprovalReceived | null;
  actions: ActionExecuted[];
  ledger: LedgerUpdate | null;
  costTotal: number;
  costLive: boolean;
  agents: Record<string, { model: string; live: boolean; usd: number }>;
  summary: Summary | null;
  error: string | null;
}

const emptyStages = (): Record<Stage, StageState> =>
  Object.fromEntries(STAGES.map((s) => [s.key, { status: "pending" }])) as Record<Stage, StageState>;

export const initialState = (services: Record<string, string> = {}): RunState => ({
  runId: null,
  status: "idle",
  services,
  stages: emptyStages(),
  active: null,
  messages: [],
  lineItems: [],
  totalItems: 12,
  flagged: [],
  hiddenTotal: 0,
  rate: null,
  lanes: { hardball: [], diplomat: [] },
  verdict: null,
  apr: null,
  redlines: [],
  draft: null,
  approval: null,
  approvalReceived: null,
  actions: [],
  ledger: null,
  costTotal: 0,
  costLive: false,
  agents: {},
  summary: null,
  error: null,
});

export type Action =
  | { type: "reset"; services: Record<string, string> }
  | { type: "starting" }
  | { type: "services"; services: Record<string, string> }
  | { type: "notice"; message: string | null }
  | { type: "event"; ev: SwarmEvent };

export function reducer(s: RunState, a: Action): RunState {
  switch (a.type) {
    case "reset":
      return initialState(a.services);
    case "starting":
      return { ...initialState(s.services), status: "starting" };
    case "services":
      return { ...s, services: a.services };
    case "notice":
      return { ...s, error: a.message };
    case "event":
      return applyEvent(s, a.ev);
  }
}

function applyEvent(s: RunState, ev: SwarmEvent): RunState {
  switch (ev.event) {
    case "run_started":
      return { ...s, runId: ev.run_id, status: "running", services: ev.services };
    case "stage_start":
      return {
        ...s,
        active: ev.stage,
        status: ev.stage === "approval" ? "awaiting" : "running",
        stages: { ...s.stages, [ev.stage]: { status: "active", label: ev.label, model: ev.model, live: ev.live } },
      };
    case "stage_done":
      return {
        ...s,
        status: ev.stage === "approval" ? "running" : s.status,
        stages: { ...s.stages, [ev.stage]: { ...s.stages[ev.stage], status: "done", note: ev.note } },
      };
    case "owner_message":
      return { ...s, messages: [...s.messages, ev] };
    case "line_item":
      return { ...s, lineItems: [...s.lineItems, ev.item], totalItems: ev.total_items };
    case "fee_flagged":
      return { ...s, flagged: [...s.flagged, ev], hiddenTotal: ev.hidden_total };
    case "rate_computed":
      return { ...s, rate: ev };
    case "negotiation_turn": {
      const turns = [...s.lanes[ev.lane]];
      const last = turns[turns.length - 1];
      if (last && !last.done && last.round === ev.round && last.speaker === ev.speaker) {
        turns[turns.length - 1] = {
          ...last,
          text: last.text + ev.delta,
          done: ev.done,
          offer: ev.offer ?? last.offer,
        };
      } else {
        turns.push({ round: ev.round, speaker: ev.speaker, text: ev.delta, done: ev.done, offer: ev.offer });
      }
      return { ...s, lanes: { ...s.lanes, [ev.lane]: turns } };
    }
    case "referee_verdict":
      return { ...s, verdict: ev };
    case "apr_revealed":
      return { ...s, apr: ev };
    case "redline":
      return { ...s, redlines: [...s.redlines, ev] };
    case "draft":
      return { ...s, draft: ev };
    case "approval_requested":
      return { ...s, approval: ev, status: "awaiting" };
    case "approval_received":
      return { ...s, approvalReceived: ev, status: "running" };
    case "action_executed":
      return { ...s, actions: [...s.actions, ev] };
    case "ledger_update":
      return { ...s, ledger: ev };
    case "cost_log":
      return {
        ...s,
        costTotal: ev.run_total_usd,
        costLive: s.costLive || ev.live,
        agents: {
          ...s.agents,
          [ev.agent]: { model: ev.model, live: ev.live, usd: (s.agents[ev.agent]?.usd ?? 0) + ev.usd },
        },
      };
    case "summary":
      return { ...s, summary: ev };
    case "done":
      return { ...s, status: ev.ok ? "done" : "error", active: null };
    case "error":
      return { ...s, error: ev.message, status: "error" };
  }
}

/** Latest priced offer per lane (the rep's last offer). */
export function laneOffer(turns: Turn[]): Offer | null {
  for (let i = turns.length - 1; i >= 0; i--) {
    const o = turns[i]?.offer;
    if (o) return o;
  }
  return null;
}
