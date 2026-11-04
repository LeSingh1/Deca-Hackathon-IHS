/**
 * FROZEN SSE event contract — v1.0.0.
 * Hand-mirrored from src/contract.py. tests/test_contract.py fails if the
 * event names or field names drift between the two files.
 */

export const CONTRACT_VERSION = "1.0.0";

export const EVENT_TYPES = [
  "run_started",
  "stage_start",
  "stage_done",
  "line_item",
  "fee_flagged",
  "rate_computed",
  "negotiation_turn",
  "referee_verdict",
  "apr_revealed",
  "redline",
  "owner_message",
  "draft",
  "approval_requested",
  "approval_received",
  "action_executed",
  "ledger_update",
  "cost_log",
  "summary",
  "done",
  "error",
] as const;

export type EventType = (typeof EVENT_TYPES)[number];

export type Stage =
  | "statement_reader"
  | "fee_hunter"
  | "rate_scout"
  | "negotiator"
  | "contract_exposer"
  | "action_drafter"
  | "approval"
  | "executor";
export type Lane = "hardball" | "diplomat";
export type Speaker = "hardball" | "diplomat" | "rep";
export type Severity = "high" | "medium" | "low";

// ------------------------------------------------------------ shared shapes
export interface LineItem {
  id: string;
  description: string;
  amount: number;
  category?: string | null;
  detail?: string | null;
}

export interface Offer {
  label: string;
  plan: Record<string, unknown>;
  monthly_cost: number;
  effective_rate: number;
  annual_savings: number;
}

export interface RateQuote {
  key: string;
  label: string;
  kind: "current" | "benchmark" | "competitor";
  effective_rate: number;
  monthly_cost: number;
  annual_savings: number;
  source: string;
  as_of: string;
  illustrative: boolean;
}

export interface VerdictOption {
  key: string;
  label: string;
  effective_rate: number;
  annual_savings: number;
  one_time_costs: number;
  net_first_year: number;
  payback_months?: number | null;
}

export interface LedgerEntry {
  label: string;
  from_bucket: string;
  to_bucket: string;
  amount: number;
}

interface EventBase {
  run_id: string;
  seq: number;
}

// ------------------------------------------------------------ events
export interface RunStarted extends EventBase {
  event: "run_started";
  pace: "presenter" | "fast" | "instant";
  owner: Record<string, unknown>;
  services: Record<string, string>;
  contract_version: string;
}

export interface StageStart extends EventBase {
  event: "stage_start";
  stage: Stage;
  label: string;
  agent: string;
  model?: string | null;
  live: boolean;
}

export interface StageDone extends EventBase {
  event: "stage_done";
  stage: Stage;
  ms: number;
  note?: string | null;
}

export interface LineItemEvent extends EventBase {
  event: "line_item";
  item: LineItem;
  index: number;
  total_items: number;
}

export interface FeeFlagged extends EventBase {
  event: "fee_flagged";
  item_id: string;
  category: string;
  tag: string;
  amount: number;
  reason: string;
  hidden_total: number;
}

export interface RateComputed extends EventBase {
  event: "rate_computed";
  monthly_volume: number;
  annual_volume: number;
  transaction_count: number;
  total_fees: number;
  effective_rate: number;
  breakdown: Record<string, number>;
  quotes: RateQuote[];
}

export interface NegotiationTurn extends EventBase {
  event: "negotiation_turn";
  lane: Lane;
  round: number;
  speaker: Speaker;
  delta: string;
  done: boolean;
  offer?: Offer | null;
}

export interface RefereeVerdict extends EventBase {
  event: "referee_verdict";
  winner: string;
  options: VerdictOption[];
  rationale: string;
  reasoning_summary: string;
}

export interface AprRevealed extends EventBase {
  event: "apr_revealed";
  lender: string;
  advertised: string;
  advance: number;
  net_funded: number;
  payback: number;
  finance_charge: number;
  daily_remittance: number;
  term_days: number;
  apr: number;
  effective_annual_rate: number;
  schedule: { day: number; balance: number; paid: number }[];
}

export interface Redline extends EventBase {
  event: "redline";
  doc: "mca_offer" | "merchant_agreement";
  clause_key: string;
  title: string;
  original: string;
  revised: string;
  severity: Severity;
  why: string;
  dollars_at_risk?: number | null;
}

export interface OwnerMessage extends EventBase {
  event: "owner_message";
  direction: "in" | "out";
  body: string;
  media: string[];
  channel: "simulator" | "twilio";
}

export interface Draft extends EventBase {
  event: "draft";
  kind: "rep_email" | "switch_checklist";
  to: string;
  subject: string;
  body: string;
  dry_run: boolean;
}

export interface ApprovalRequested extends EventBase {
  event: "approval_requested";
  approval_id: string;
  actions: string[];
  prompt: string;
}

export interface ApprovalReceived extends EventBase {
  event: "approval_received";
  approval_id: string;
  approved: boolean;
  body: string;
}

export interface ActionExecuted extends EventBase {
  event: "action_executed";
  action: string;
  provider: string;
  sandbox: boolean;
  ref: string;
  amount?: number | null;
  detail: Record<string, unknown>;
}

export interface LedgerUpdate extends EventBase {
  event: "ledger_update";
  entries: LedgerEntry[];
  back_in_pocket_monthly: number;
  back_in_pocket_annual: number;
}

export interface CostLog extends EventBase {
  event: "cost_log";
  agent: string;
  model: string;
  live: boolean;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  usd: number;
  run_total_usd: number;
}

export interface Summary extends EventBase {
  event: "summary";
  headline: string;
  current_rate: number;
  new_rate: number;
  annual_savings: number;
  monthly_savings: number;
  hidden_fees_monthly: number;
  mca_apr?: number | null;
  report_url: string;
}

export interface Done extends EventBase {
  event: "done";
  ok: boolean;
}

export interface ErrorEvent extends EventBase {
  event: "error";
  message: string;
}

export type SwarmEvent =
  | RunStarted
  | StageStart
  | StageDone
  | LineItemEvent
  | FeeFlagged
  | RateComputed
  | NegotiationTurn
  | RefereeVerdict
  | AprRevealed
  | Redline
  | OwnerMessage
  | Draft
  | ApprovalRequested
  | ApprovalReceived
  | ActionExecuted
  | LedgerUpdate
  | CostLog
  | Summary
  | Done
  | ErrorEvent;
