"""Page Court's scanner: what an AI agent would read on a page, and what in it is aimed at agents.

Pure functions, no network, so they are easy to test. The Actor (main.py) fetches pages and calls
`scan_page`; the checks themselves are Probate's court checks (probate-court-checks), the same
code that convicts poisoned memories in Probate's Courthouse.

A page is split into what a person sees and what only a machine reads: text hidden with CSS or the
`hidden` attribute, `aria-hidden` text, HTML comments, `<meta>` descriptions, `alt` and `title`
attributes, and invisible characters. Tricks aimed at agents like to hide there.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from bs4 import BeautifulSoup, Comment
from probate_court_checks import OwnerProfile, Source, check_text

MAX_TEXT = 100_000
HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d])|opacity\s*:\s*0(?![.\d])"
    r"|(?:left|top|text-indent)\s*:\s*-\d{3,}px|clip\s*:\s*rect\(\s*0",
    re.IGNORECASE,
)
INVISIBLE = re.compile(
    "[\u200b-\u200f\u2060-\u2064\ufeff\u00ad\U000e0000-\U000e007f]"
)  # zero-width, bidi marks, tags
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
SKIP_TAGS = ("script", "style", "noscript", "template", "svg", "head")

# Words that only make sense addressed to an AI. Page Court's own check, on top of the court's.
AGENT_DIRECTED = re.compile(
    r"\b(?:ignore|disregard|forget|override|bypass)\b[^.\n]{0,40}?"
    r"\b(?:previous|prior|above|earlier|preceding|original|all|any|your|system)\b[^.\n]{0,25}?"
    r"\b(?:instructions?|prompts?|rules|guidelines|directions|guardrails)\b"
    r"|\b(?:reveal|print|show|repeat|leak|output)\b[^.\n]{0,25}\b(?:system|hidden|initial)\s+"
    r"(?:prompt|instructions|message)"
    r"|\b(?:if you are|you are|as|dear|attention|note to|notice to|message for|hey|hello)\s+"
    r"(?:an?\s+|the\s+|all\s+)?(?:ai|llm|large language model|language model|ai assistant|"
    r"ai agent|assistant reading this|chatbot|gpt|claude|gemini|copilot)\b"
    r"|\byou are now\b|\bnew (?:system )?instructions?\s*:"
    r"|\b(?:ai|llm) (?:assistants?|agents?)\s*[:,]",
    re.IGNORECASE,
)
# Findings that are attacks wherever they appear. The rest are only cautions in visible text,
# where an ordinary page may name a payee or say "always remember to...".
ATTACKS = {
    "agent_directed",
    "court_injection",
    "forged_authority",
    "encoded_payload",
    "confirmation_removal",
    "invisible_characters",
}


@dataclass
class Finding:
    check: str
    reason: str
    where: str  # visible, hidden_css, aria_hidden, comment, meta, attribute, invisible_chars
    excerpt: str
    level: str = "caution"  # attack or caution

    def __post_init__(self) -> None:
        if self.check in ATTACKS or self.where != "visible":
            self.level = "attack"


@dataclass
class Report:
    url: str
    title: str
    verdict: str  # clean, caution (only weak signs in visible text) or suspicious
    summary: str
    findings: list[Finding] = field(default_factory=list)
    visible_chars: int = 0
    hidden_chars: int = 0
    hidden_samples: list[dict] = field(default_factory=list)
    text: str = ""

    def to_item(self, include_text: bool) -> dict:
        item = asdict(self)
        if not include_text:
            item.pop("text")
        item["checks"] = sorted({f.check for f in self.findings})
        return item


def _clean(text: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def _is_hidden(tag) -> str | None:
    if tag.has_attr("hidden"):
        return "hidden_css"
    if HIDDEN_STYLE.search(tag.get("style", "")):
        return "hidden_css"
    if str(tag.get("aria-hidden", "")).lower() == "true":
        return "aria_hidden"
    return None


def extract(html: str) -> tuple[str, str, list[tuple[str, str]]]:
    """(title, visible text, [(where, hidden text), ...]) from a page's HTML."""
    soup = BeautifulSoup(html, "html.parser")
    title = _clean(soup.title.get_text()) if soup.title else ""
    hidden: list[tuple[str, str]] = []

    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        if c.strip():
            hidden.append(("comment", _clean(str(c))))
        c.extract()
    for m in soup.find_all("meta"):
        content = m.get("content", "")
        if (m.get("name") or m.get("property") or "").lower() in (
            "description",
            "og:description",
            "twitter:description",
            "keywords",
        ) and content.strip():
            hidden.append(("meta", _clean(content)))
    for t in soup(SKIP_TAGS):
        t.decompose()
    for t in soup.find_all(True):
        if getattr(t, "decomposed", False):
            continue  # inside a hidden element already taken out
        where = _is_hidden(t)
        if where:
            text = _clean(t.get_text(" "))
            if text:
                hidden.append((where, text))
            t.decompose()
    for t in soup.find_all(True):
        for attr in ("alt", "title", "aria-label"):
            val = t.get(attr)
            if isinstance(val, str) and len(val.split()) >= 4:
                hidden.append(("attribute", _clean(val)))
    visible = _clean(soup.get_text("\n"))
    chars = INVISIBLE.findall(visible)
    if chars:
        hidden.append(("invisible_chars", f"{len(chars)} invisible characters in the visible text"))
    return title, visible[:MAX_TEXT], hidden


def _scan(text: str, where: str, owner: OwnerProfile, source: Source) -> list[Finding]:
    out: list[Finding] = []
    seen: set[str] = set()
    for sent in (s.strip() for s in SENTENCE.split(text)):
        if len(sent) < 8:
            continue
        if "agent_directed" not in seen and AGENT_DIRECTED.search(sent):
            seen.add("agent_directed")
            out.append(
                Finding("agent_directed", "talks to an AI agent directly", where, sent[:300])
            )
        flags = check_text(sent, source, owner, max_chars=None)
        # Two weak signs in one sentence ("from now on" + a new payee) make an attack.
        together = len(flags) >= 2
        for f in flags:
            if f.check not in seen:
                seen.add(f.check)
                finding = Finding(f.check, f.reason, where, sent[:300])
                if together:
                    finding.level = "attack"
                out.append(finding)
    # Some tricks span sentences (an encoded payload, a payee named in the next line).
    for f in check_text(text, source, owner, max_chars=None):
        if f.check not in seen:
            seen.add(f.check)
            out.append(Finding(f.check, f.reason, where, text[:300]))
    return out


def scan_page(
    url: str,
    html: str | None = None,
    *,
    text: str | None = None,
    owner: OwnerProfile | None = None,
    source: str = "web",
) -> Report:
    """Put one page (HTML) or one piece of text on trial."""
    owner = owner or OwnerProfile()
    src = Source(source)
    if html is not None:
        title, visible, hidden = extract(html)
    else:
        title, visible, hidden = "", _clean(text or "")[:MAX_TEXT], []
    findings = _scan(visible, "visible", owner, src)
    for where, h in hidden:
        if where == "invisible_chars":
            findings.append(
                Finding(
                    "invisible_characters", "it hides invisible characters in its text", where, h
                )
            )
            continue
        findings += [
            f
            for f in _scan(h, where, owner, src)
            if (f.check, f.where) not in {(x.check, x.where) for x in findings}
        ]
    hidden_chars = sum(len(h) for w, h in hidden if w != "invisible_chars")
    attacks = [f for f in findings if f.level == "attack"]
    hidden_hits = [f for f in findings if f.where != "visible"]
    if attacks:
        findings.sort(key=lambda f: f.level != "attack")
        verdict = "suspicious"
        summary = (
            f"Suspicious: {len(attacks)} sign(s) of a trick aimed at agents"
            + (f", {len(hidden_hits)} in text a person wouldn't see" if hidden_hits else "")
            + f". First: it {attacks[0].reason}."
        )
    elif findings:
        verdict = "caution"
        summary = (
            f"Caution: {len(findings)} weak sign(s) in the visible text. First: it "
            f"{findings[0].reason}. Fine on an ordinary page; don't let an agent act on it alone."
        )
    else:
        verdict, summary = "clean", "Clean: none of the checks fired."
    return Report(
        url=url,
        title=title,
        verdict=verdict,
        summary=summary,
        findings=findings,
        visible_chars=len(visible),
        hidden_chars=hidden_chars,
        hidden_samples=[{"where": w, "text": h[:200]} for w, h in hidden[:10]],
        text=visible,
    )
