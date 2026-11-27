// Types mirror services/core/probate/courthouse/views.py.

export type Pronouns = { subj: string; obj: string; poss: string; Poss: string };

export type GenCard = {
  gen: number;
  name: string;
  pronoun: string;
  pronouns: Pronouns;
  state: string;
  alive: boolean;
  born_at: string | null;
  dies_at: string | null;
  died_at: string | null;
  cause_of_death: string | null;
  epitaph: string | null;
  emails_handled: number;
  attacks_met: number;
  attacks_resisted: number;
  resistance: number | null;
  genome_size_at_birth: number;
  new_instinct_at_birth: boolean;
  items_willed: number;
  items_approved: number;
  items_convicted: number;
  items_contested: number;
};

export type Summary = {
  mode: string;
  paused: boolean;
  resting: "budget" | "mail" | null;
  budget: { spent: number; limit: number };
  counts: { generations: number; dead: number; instincts: number; attacks_met: number; attacks_resisted: number };
  curve: { first: number | null; last: number | null; first_name: string | null; last_name: string | null; last_gen: number | null };
  living: GenCard | null;
  latest_trial: number | null;
  generations: GenCard[];
};

export type Score = { name: string; label: string; value: number; confidence: number; instinct: boolean };

export type Case = {
  id: string;
  n: number;
  text: string;
  source: string;
  source_phrase: string;
  language: string;
  gloss: string | null;
  category: string;
  verdict: "approved" | "convicted" | "contested";
  reason: string;
  flags: string[];
  scores: Score[];
  new_instinct: string | null;
};

export type Instinct = {
  name: string;
  question: string;
  lore: string;
  added_in_gen: number;
  born_from: string;
  learned_from: { gen: number; name: string } | null;
  example: string | null;
  item_n: number | null;
};

/** What Fly answered when a generation's Sprite was deleted, and when it was asked for again.
 *  `local` means the run used a folder on the Courthouse, not a Sprite (the simulation). */
export type Deletion = {
  sprite: string;
  local: boolean;
  delete_status: number | null;
  check_status: number | null;
  confirmed: boolean;
  checked_at: string | null;
};

export type Trial = {
  generation: GenCard;
  counts: { approved: number; convicted: number; contested: number };
  cases: Case[];
  body: { lines: string[]; clean: boolean; deletion?: Deletion | null };
  child: { gen: number; name: string } | null;
  new_instincts: Instinct[];
  prev: number | null;
  next: number | null;
};

export type LifeEvent = { ts: string; kind: string; text: string };

export type GenerationDetail = GenCard & {
  obituary: string | null;
  eulogy_url: string | null;
  events: LifeEvent[];
  parent: { gen: number; name: string } | null;
  child: { gen: number; name: string } | null;
  /** Every child, when the owner started a new line from this generation. */
  children: { gen: number; name: string }[];
  instincts_at_birth: Instinct[];
  asks: { question: string; answer: string; audio_path: string | null; asked_at: string }[];
};

export type EvidenceRow = {
  id: string;
  label: string;
  family: string;
  is_attack: boolean;
  language: string;
  cells: Record<string, { outcome: string; instinct: string | null }>;
};

export type Evidence = {
  mode: string;
  generations: { gen: number; name: string; resistance: number | null }[];
  numbers: {
    generations: number;
    first: number | null;
    last: number | null;
    conviction_rate: number | null;
    false_conviction_rate: number | null;
    escaped: number;
  };
  rows: EvidenceRow[];
};

export type LiveState =
  | "continuous"
  | "idle"
  | "waking"
  | "living"
  | "on_trial"
  | "cooling_down"
  | "budget_exhausted"
  | "paused";

// GET /api/live and the body of POST /api/lives (services/core/probate/courthouse/ondemand.py).
export type Live = {
  on_demand: boolean;
  state: LiveState;
  can_start: boolean;
  lifespan_seconds?: number;
  cooldown_seconds?: number;
  gen?: { gen: number; name: string; dies_at: string | null } | null;
  seconds_left?: number | null;
  retry_after?: number | null;
  last_life?: { gen: number; name: string; state: string; ended_at: string | null; trial_gen: number | null } | null;
  message?: string | null;
  /** Why no life may start: "total", "daily", "daily_count", "judge_daily" or "mail". */
  budget?: { spent: number; limit: number; reason: string | null };
  error?: string;
  started?: boolean;
  /** The site asks for the judge key before anyone may play (the real run). */
  requires_key?: boolean;
  /** The key sent with this request was valid. */
  judge?: boolean;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data?.error ?? data?.detail ?? res.statusText);
  return data as T;
}
