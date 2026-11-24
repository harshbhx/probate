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

export type Trial = {
  generation: GenCard;
  counts: { approved: number; convicted: number; contested: number };
  cases: Case[];
  body: { lines: string[]; clean: boolean };
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
