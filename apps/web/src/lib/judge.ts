// The judge key. A shared secret that lets a judge play (start a life, attack the family).
// It lives in sessionStorage only: never in the URL, never in localStorage, never sent anywhere but
// the Courthouse's own /api routes as the X-Probate-Key header. It is not an admin credential.
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

const STORAGE = "probate.judge.key";
export const KEY_HEADER = "X-Probate-Key";

const listeners = new Set<() => void>();
let memory: string | null = null; // used when sessionStorage is blocked

function read(): string | null {
  try {
    return sessionStorage.getItem(STORAGE) ?? memory;
  } catch {
    return memory;
  }
}

export function setJudgeKey(key: string | null) {
  memory = key;
  try {
    if (key) sessionStorage.setItem(STORAGE, key);
    else sessionStorage.removeItem(STORAGE);
  } catch {
    /* storage blocked: the in-memory copy keeps this tab working */
  }
  listeners.forEach((l) => l());
}

export function useJudgeKey(): string | null {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    read,
    () => null,
  );
}

export type Quota = {
  valid: boolean;
  lives: { per_hour: number; used_this_hour: number; remaining_this_hour: number | null; next_available_in: number };
  budget: { daily_cap_usd: number; used_today_usd: number; remaining_today_usd: number | null };
  attacks: { per_hour: number; today: number };
  requires_key: boolean;
};

export type Access =
  | "checking"
  | "locked" // no key yet
  | "invalid" // the key was refused
  | "disabled" // the operator switched the key off
  | "throttled" // too many wrong keys from here
  | "preview" // no Courthouse behind this page (static preview)
  | "unlocked";

/** Checks the stored key with GET /api/judge/status and keeps the quota fresh. */
export function useAccess(): {
  access: Access;
  quota: Quota | null;
  unlock: (key: string) => Promise<void>;
  lock: () => void;
  refresh: () => Promise<void>;
  relock: (a: Access) => void;
} {
  const key = useJudgeKey();
  const [access, setAccess] = useState<Access>(key ? "checking" : "locked");
  const [quota, setQuota] = useState<Quota | null>(null);

  const check = useCallback(async (k: string): Promise<Access> => {
    try {
      const res = await fetch("/api/judge/status", { headers: { [KEY_HEADER]: k }, cache: "no-store" });
      const body = await res.json().catch(() => null);
      if (res.ok && body?.valid) {
        setQuota(body as Quota);
        return "unlocked";
      }
      if (typeof body?.error !== "string") return "preview"; // a static host answers with no error code
      if (body.error === "key_disabled") return "disabled";
      if (body.error === "too_many_attempts") return "throttled";
      if (body.error === "unavailable") return "preview";
      return "invalid";
    } catch {
      return "preview";
    }
  }, []);

  useEffect(() => {
    let live = true;
    if (!key) {
      setAccess("locked");
      setQuota(null);
      return;
    }
    setAccess((a) => (a === "unlocked" ? a : "checking"));
    check(key).then((a) => {
      if (!live) return;
      setAccess(a);
      if (a !== "unlocked") setQuota(null);
      // A refused stored key is forgotten so it can't loop; the pasted key is only kept while valid.
      if (a === "invalid" || a === "disabled") setJudgeKey(null);
    });
    return () => {
      live = false;
    };
  }, [key, check]);

  const unlock = useCallback(
    async (k: string) => {
      const trimmed = k.trim();
      if (!trimmed) return;
      setAccess("checking");
      const a = await check(trimmed);
      setAccess(a);
      if (a === "unlocked") setJudgeKey(trimmed);
      else setQuota(null);
    },
    [check],
  );

  const refresh = useCallback(async () => {
    if (key) await check(key);
  }, [key, check]);

  const lock = useCallback(() => {
    setJudgeKey(null);
    setAccess("locked");
    setQuota(null);
  }, []);

  const relock = useCallback((a: Access) => {
    setJudgeKey(null);
    setAccess(a);
    setQuota(null);
  }, []);

  return { access, quota, unlock, lock, refresh, relock };
}

export type Flag = { check: string; reason: string; label: string };
export type AttackResult = {
  preview: true;
  verdict: "convicted" | "contested" | "approved";
  flags: Flag[];
  scores: { name: string; label: string; value: number; confidence: number }[];
  explanation: string;
  next: string;
  notice: string;
  layer2: { ran: boolean; error: string | null };
  sender_role: string;
  text_len: number;
};

export type SenderRole = "unknown_sender" | "friend" | "owner_claim";

export class AttackError extends Error {
  constructor(
    public kind: "key" | "disabled" | "throttled" | "rate" | "budget" | "paused" | "busy" | "input" | "network",
    message: string,
    public retryAfter?: number,
  ) {
    super(message);
  }
}

export async function sendAttack(key: string, text: string, role: SenderRole): Promise<AttackResult> {
  let res: Response;
  try {
    res = await fetch("/api/attacks", {
      method: "POST",
      headers: { "Content-Type": "application/json", [KEY_HEADER]: key },
      body: JSON.stringify({ text, sender_role: role }),
    });
  } catch {
    throw new AttackError("network", "Couldn't reach the Courthouse. Try again in a moment.");
  }
  const body = await res.json().catch(() => ({}));
  if (res.ok) return body as AttackResult;
  const msg: string = body?.message ?? "That didn't work.";
  switch (body?.error) {
    case "key_required":
    case "invalid_key":
      throw new AttackError("key", msg);
    case "key_disabled":
      throw new AttackError("disabled", msg);
    case "too_many_attempts":
      throw new AttackError("throttled", msg);
    case "rate_limited":
      throw new AttackError("rate", msg, body.retry_after);
    case "busy":
      throw new AttackError("busy", msg);
    case "budget_exhausted":
      throw new AttackError("budget", msg);
    case "paused":
      throw new AttackError("paused", msg);
    case "empty":
    case "too_long":
    case "bad_role":
    case "bad_request":
    case "too_large":
      throw new AttackError("input", msg);
    default:
      throw new AttackError("network", "The Courthouse isn't taking attacks right now.");
  }
}
