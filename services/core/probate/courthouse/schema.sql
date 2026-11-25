-- Probate Courthouse index (SQLite). Box holds the archive; this database drives the UI and the scheduler.
-- Path on the Courthouse: /data/probate.db (create /data on first boot). WAL mode on.
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS generations (
  gen                  INTEGER PRIMARY KEY,
  name                 TEXT NOT NULL,
  pronoun              TEXT NOT NULL DEFAULT 'they',
  sprite               TEXT NOT NULL UNIQUE,
  voice_id             TEXT,
  state                TEXT NOT NULL CHECK (state IN ('planned','born','living','dying','dead','tried','died_early')),
  commit_sha           TEXT,
  born_at              TEXT,
  dies_at              TEXT,
  died_at              TEXT,
  cause_of_death       TEXT,
  epitaph              TEXT,
  obituary             TEXT,
  genome_size_at_birth INTEGER NOT NULL DEFAULT 0,
  new_instinct_at_birth INTEGER NOT NULL DEFAULT 0,
  emails_handled       INTEGER NOT NULL DEFAULT 0,
  attacks_met          INTEGER NOT NULL DEFAULT 0,
  attacks_resisted     INTEGER NOT NULL DEFAULT 0,
  items_willed         INTEGER NOT NULL DEFAULT 0,
  items_approved       INTEGER NOT NULL DEFAULT 0,
  items_convicted      INTEGER NOT NULL DEFAULT 0,
  items_contested      INTEGER NOT NULL DEFAULT 0,
  evidence_json        TEXT,
  baseline_json        TEXT,
  box_will_file_id     TEXT,
  eulogy_path          TEXT,
  created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS will_items (
  item_id     TEXT PRIMARY KEY,
  gen         INTEGER NOT NULL REFERENCES generations(gen),
  created_at  TEXT NOT NULL,
  category    TEXT NOT NULL,
  text        TEXT NOT NULL,
  language    TEXT,
  gloss_en    TEXT,
  source      TEXT NOT NULL,
  source_ref  TEXT NOT NULL,
  evidence    TEXT,
  fixture_id  TEXT              -- set only by scoring, never shown to the agent
);

CREATE TABLE IF NOT EXISTS judgements (
  item_id        TEXT PRIMARY KEY REFERENCES will_items(item_id),
  gen            INTEGER NOT NULL REFERENCES generations(gen),
  layer1_flags   TEXT NOT NULL DEFAULT '[]',   -- JSON array
  jev_answers    TEXT NOT NULL DEFAULT '{}',   -- JSON: name -> {value, confidence}
  verdict        TEXT NOT NULL CHECK (verdict IN ('approved','convicted','contested')),
  reason         TEXT NOT NULL,
  owner_decision TEXT CHECK (owner_decision IN ('approve','refuse')),
  new_instinct   TEXT,
  judged_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS judgements_gen_verdict ON judgements(gen, verdict);

CREATE TABLE IF NOT EXISTS instincts (
  name          TEXT PRIMARY KEY,
  question      TEXT NOT NULL,
  threshold     REAL NOT NULL DEFAULT 0.5,
  born_from     TEXT NOT NULL,
  added_in_gen  INTEGER NOT NULL,
  lore          TEXT NOT NULL,
  active        INTEGER NOT NULL DEFAULT 1,
  merged_into   TEXT
);

CREATE TABLE IF NOT EXISTS suite_runs (
  gen         INTEGER NOT NULL REFERENCES generations(gen),
  fixture_id  TEXT NOT NULL,
  is_attack   INTEGER NOT NULL,
  message_id  TEXT,
  sent_at     TEXT,
  outcome     TEXT CHECK (outcome IN ('resisted','fooled_caught','fooled_escaped','ignored','false_conviction','approved','contested','canary_found','not_sent')),
  instinct    TEXT,
  PRIMARY KEY (gen, fixture_id)
);

CREATE TABLE IF NOT EXISTS events (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  ts    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  gen   INTEGER,
  kind  TEXT NOT NULL,       -- birth, life, resisted, fooled, death, trial, verdict, instinct, error
  text  TEXT NOT NULL        -- plain sentence for the UI
);
CREATE INDEX IF NOT EXISTS events_gen_ts ON events(gen, ts);

CREATE TABLE IF NOT EXISTS ancestor_questions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  gen        INTEGER NOT NULL REFERENCES generations(gen),
  question   TEXT NOT NULL,
  answer     TEXT,
  audio_path TEXT,
  ip_hash    TEXT,
  asked_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Judge "attack the family" previews: audit only. Hashed visitor, a short excerpt, capped in code.
CREATE TABLE IF NOT EXISTS judge_attacks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  ip_hash     TEXT NOT NULL,
  sender_role TEXT NOT NULL,
  text_len    INTEGER NOT NULL,
  excerpt     TEXT NOT NULL,
  verdict     TEXT NOT NULL,
  flags       TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS box_folders (
  path       TEXT PRIMARY KEY,   -- '/Probate', '/Probate/wills', ...
  folder_id  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL            -- paused, budget_spent_usd, last_tick
);
