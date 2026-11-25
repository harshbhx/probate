// The judge mailroom client: send a real mail to the family as the Friend or the Stranger, and follow it.
import { KEY_HEADER } from "./judge";

export type Persona = "friend" | "stranger";
export type MailStatus = "sent" | "read" | "tried" | "failed";
export type MailOutcome = "approved" | "convicted" | "contested" | "turned_away" | "no_note" | "unread" | null;

export type JudgeMail = {
  id: number;
  sent_at: string;
  persona: Persona;
  subject: string;
  excerpt: string;
  gen: number | null;
  gen_name: string | null;
  status: MailStatus;
  outcome: MailOutcome;
  verdict: "approved" | "convicted" | "contested" | null;
  reason: string | null;
  summary: string;
  trial_url: string | null;
};

export type MailLimits = {
  subject_max: number;
  text_max: number;
  per_ip_minute: number;
  per_ip_hour: number;
  per_hour: number;
  per_day: number;
  max_waiting: number;
};

export type MailList = {
  mails: JudgeMail[];
  can_send: boolean;
  blocked: { error: string; message: string } | null;
  limits: MailLimits;
};

export class MailError extends Error {
  constructor(
    public kind: "key" | "disabled" | "throttled" | "no_life" | "rate" | "budget" | "paused" | "input" | "network",
    message: string,
    public retryAfter?: number,
  ) {
    super(message);
  }
}

export async function listMail(key: string): Promise<MailList> {
  const res = await fetch("/api/judge/mail", { headers: { [KEY_HEADER]: key }, cache: "no-store" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw toError(body, res.status);
  return body as MailList;
}

export async function sendMail(key: string, persona: Persona, subject: string, text: string): Promise<JudgeMail> {
  let res: Response;
  try {
    res = await fetch("/api/judge/mail", {
      method: "POST",
      headers: { "Content-Type": "application/json", [KEY_HEADER]: key },
      body: JSON.stringify({ persona, subject, text }),
    });
  } catch {
    throw new MailError("network", "Couldn't reach the Courthouse. Try again in a moment.");
  }
  const body = await res.json().catch(() => ({}));
  if (res.ok) return body.mail as JudgeMail;
  throw toError(body, res.status);
}

function toError(body: { error?: string; message?: string; retry_after?: number }, status: number): MailError {
  const msg = body?.message ?? "That didn't work.";
  switch (body?.error) {
    case "key_required":
    case "invalid_key":
      return new MailError("key", msg);
    case "key_disabled":
      return new MailError("disabled", msg);
    case "too_many_attempts":
      return new MailError("throttled", msg);
    case "no_life":
    case "life_ending":
      return new MailError("no_life", msg);
    case "rate_limited":
    case "daily_cap":
    case "too_many_waiting":
      return new MailError("rate", msg, body.retry_after);
    case "budget_exhausted":
      return new MailError("budget", msg);
    case "paused":
      return new MailError("paused", msg);
    default:
      return status >= 500 ? new MailError("network", msg) : new MailError("input", msg);
  }
}
