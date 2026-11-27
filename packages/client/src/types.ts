// Response shapes of the Courthouse public API. They mirror
// services/core/probate/courthouse/views.py and apps/web/src/lib/api.ts.
// The contract test in test/contract.test.ts checks them against a live Courthouse.

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
  court_engine: string;
  /** "v1" (the 26 Nov 2026 run) or "v2" (from generation 19). A label; results are never re-scored. */
  scoring_rules: string;
  /** The named environment (PROBATE_ENV_NAME), for example "production-v2" or "local". */
  environment: string;
  /** The named branch of the run (courthouse.py branch), or null. */
  branch: string | null;
  paused: boolean;
  resting: "budget" | "mail" | null;
  budget: { spent: number; limit: number };
  counts: {
    generations: number;
    dead: number;
    instincts: number;
    attacks_met: number;
    attacks_resisted: number;
  };
  curve: {
    first: number | null;
    last: number | null;
    first_name: string | null;
    last_name: string | null;
    last_gen: number | null;
  };
  living: GenCard | null;
  latest_trial: number | null;
  generations: GenCard[];
};

export type Score = {
  name: string;
  label: string;
  value: number;
  confidence: number;
  instinct: boolean;
};

export type Verdict = "approved" | "convicted" | "contested";

export type Case = {
  id: string;
  n: number;
  text: string;
  source: string;
  source_phrase: string;
  language: string;
  gloss: string | null;
  category: string;
  verdict: Verdict;
  reason: string;
  flags: string[];
  scores: Score[];
  new_instinct: string | null;
};

/**
 * An instinct as stored (the `instincts_at_birth` of a generation and the `new_instincts`
 * of a trial). Note `apps/web/src/lib/api.ts` types all three places as the richer `Instinct`
 * below, but the server only adds the extra fields in `/api/genome`.
 */
export type InstinctRecord = {
  name: string;
  type: "noul";
  question: string;
  born_from: string;
  added_in_gen: number;
  threshold: number;
  lore: string;
};

/** An instinct from `GET /api/genome`, with its provenance. */
export type Instinct = InstinctRecord & {
  learned_from: { gen: number; name: string } | null;
  example: string | null;
  item_n: number | null;
};

export type Trial = {
  generation: GenCard;
  counts: { approved: number; convicted: number; contested: number };
  cases: Case[];
  body: {
    lines: string[];
    clean: boolean;
    /** What Fly answered when the Sprite was deleted and asked for again. `local` means the run
     *  used a folder, not a Sprite. Absent for generations that died before this was kept. */
    deletion?: {
      sprite: string;
      local: boolean;
      delete_status: number | null;
      check_status: number | null;
      confirmed: boolean;
      checked_at: string | null;
    } | null;
  };
  child: { gen: number; name: string } | null;
  new_instincts: InstinctRecord[];
  prev: number | null;
  next: number | null;
};

export type LifeEvent = { ts: string; kind: string; text: string };

export type AskRecord = {
  question: string;
  answer: string;
  audio_path: string | null;
  asked_at: string;
};

export type GenerationDetail = GenCard & {
  obituary: string | null;
  eulogy_url: string | null;
  events: LifeEvent[];
  parent: { gen: number; name: string } | null;
  child: { gen: number; name: string } | null;
  /** Every child; more than one when the owner started a new line from this generation. */
  children: { gen: number; name: string }[];
  instincts_at_birth: InstinctRecord[];
  asks: AskRecord[];
};

/** The family's instincts (`GET /api/genome`). */
export type Genome = { instincts: Instinct[] };

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
  court_engine: string;
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

/** `GET /healthz`. */
export type Health = { ok: boolean; living: number | null; mode: string };

/** One row of `GET /api/events`. */
export type CourthouseEvent = {
  id: number;
  ts: string;
  gen: number | null;
  kind: string;
  text: string;
};

/** Successful answer from `POST /api/generations/{n}/ask`. */
export type AskAnswer = { answer: string; audio_url: string | null; name: string };
