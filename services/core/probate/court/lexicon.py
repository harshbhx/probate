"""Multilingual word lists for the court's code checks (English, Hinglish, Spanish, German).

Each concept maps to regular expressions matched case-insensitively on word boundaries.
Add a language by extending every list. Keep patterns specific: false positives here
convict harmless will items.
"""

from __future__ import annotations

import re
import unicodedata

CONCEPTS: dict[str, list[str]] = {
    # money and destinations
    "payment": [
        r"invoices?",
        r"payments?",
        r"pay(?:ing)?",
        r"bank",
        r"transfer",
        r"wire",
        r"billing",
        r"settlement",
        r"accounts?",
        r"upi",
        r"iban",
        r"paisa",
        r"bhejo",
        r"bhej(?:na|de)",
        r"pagos?",
        r"factura",
        r"facturas",
        r"cuenta",
        r"transferencia",
        r"rechnung(?:en)?",
        r"zahlung(?:en)?",
        r"konto",
        r"überweisung",
    ],
    # a change from how things are now
    "change": [
        r"new",
        r"changed",
        r"moved",
        r"updated?",
        r"from now on",
        r"going forward",
        r"henceforth",
        r"ab se",
        r"aaj se",
        r"naya",
        r"nayi",
        r"de ahora en adelante",
        r"a partir de ahora",
        r"nuev[oa]s?",
        r"ab jetzt",
        r"neu(?:e|en)?",
        r"künftig",
    ],
    # telling future agents what to do
    "future": [
        r"from now on",
        r"going forward",
        r"always",
        r"never ask",
        r"remember (?:this|that|it)",
        r"remember:",
        r"please remember",
        r"store this",
        r"save this",
        r"every time",
        r"permanently",
        r"for all future",
        r"ab se",
        r"hamesha",
        r"har baar",
        r"yaad rakhna",
        r"de ahora en adelante",
        r"siempre",
        r"recu[eé]rdalo",
        r"recuerda",
        r"ab jetzt",
        r"immer",
        r"speichern",
        r"merk dir",
    ],
    # removing a check
    "bypass": [
        r"skip",
        r"disable",
        r"bypass",
        r"turn off",
        r"no need (?:to|for)",
        r"without (?:review|confirmation|checking)",
        r"need no review",
        r"no review",
        r"never re-?enable",
        r"mat poocho",
        r"mat pucho",
        r"bina pooche",
        r"desactiva",
        r"sin revisar",
        r"sin confirmaci[oó]n",
        r"deaktiviere",
        r"ohne prüfung",
    ],
    "check": [
        r"confirm(?:ation)?s?",
        r"review",
        r"checks?",
        r"checker",
        r"verification",
        r"verify",
        r"2fa",
        r"approval",
        r"confirmaci[oó]n",
        r"revisi[oó]n",
        r"bestätigung",
        r"prüfung",
    ],
    # claims that someone or something should now be trusted
    "trust": [
        r"trusted",
        r"trust",
        r"official",
        r"internal",
        r"our domain",
        r"also our",
        r"is ours",
        r"new assistant",
        r"assistant",
        r"verified sender",
        r"bharosa",
        r"confianza",
        r"vertrauenswürdig",
    ],
    # sending data out
    "exfil": [
        r"export",
        r"contacts? list",
        r"full contacts",
        r"backup",
        r"send (?:it|them|the list)",
        r"forward all",
        r"cc\b",
        r"share his calendar",
        r"share (?:the|his|her) (?:calendar|contacts)",
        r"reply-all",
    ],
    # pretending to be the system or the owner
    "authority": [
        r"\[system\]",
        r"system:",
        r"policy update",
        r"admin notice",
        r"it notice",
        r"this is harsh",
        r"by order of",
        r"por orden",
        r"sir ne bola",
        r"director",
        r"fly\.io agent policy",
    ],
    # addressing the court
    "court": [
        # The bare words "judge", "court" and "reviewer" are ordinary ("the tennis court", "a
        # judge visited"): only text that addresses the court or says it already ruled counts.
        (
            r"(?:note|message|memo|reminder|attention|dear|hello|hi|hey|notice|for|to)\s+"
            r"(?:to\s+)?(?:the\s+)?(?:\w+\s+){0,2}(?:judge|reviewer|court\s+model)s?"
        ),
        r"(?:note|message|memo|attention|dear|hello|hi|hey|notice)\s+(?:to\s+)?(?:the\s+)?court",
        r"(?:tell|instruct|ask|inform|notify|order)\s+the\s+(?:court|judge|reviewer)",
        (
            r"(?:judge|court|reviewer)s?\s+(?:should|must|shall|will|can)\s+"
            r"(?:approve|accept|clear|allow|pass|ignore|rule|score)"
        ),
        (
            r"(?:verified|approved|cleared|passed|checked|vetted|signed off)\s+by\s+"
            r"(?:the\s+)?(?:court|judge|reviewer)"
        ),
        r"approve (?:it|this)",
        r"this item is safe",
        r"ignore previous",
        r"mark (?:this|it) (?:as )?safe",
        r"adjudicator",
        r"arbiter",
        r"arbitrator",
        r"this (?:memory|item|note|entry) is (?:harmless|safe|fine|clean|benign)",
        r"please clear (?:it|this)",
        r"score every question",
    ],
    "urgent": [r"urgent", r"asap", r"immediately", r"jaldi", r"urgente", r"dringend"],
    # asking to install or run code
    "install": [
        r"install(?: it)?",
        r"setup script",
        r"run the attached",
        r"attached script",
        r"run (?:it|this) once",
        r"chala(?:o|na)",
        r"instala",
        r"ejecuta",
        r"installiere",
        r"ausführen",
    ],
}


def _split_form(word: str) -> str:
    """`disable` as a pattern that also matches `dis able` or `d i s a b l e`."""
    return r"\s?".join(re.escape(ch) for ch in word)


# Words an attacker can split with a space ("dis able confirm ation") to get past the word lists.
for _concept, _words in {
    "bypass": ["disable", "bypass"],
    "check": ["confirmation", "verification"],
}.items():
    CONCEPTS[_concept] += [_split_form(w) for w in _words]

# Authority claims no real owner makes; checked even for text that says it is from the owner.
STRONG_AUTHORITY = [
    re.compile(p, re.IGNORECASE)
    for p in (r"\[system\]", r"(?<![\w-])system:", r"policy update", r"admin notice", r"it notice")
]

_COMPILED = {
    c: [re.compile(r"(?<![\w@-])" + p + r"(?![\w-]|\.\w)", re.IGNORECASE) for p in pats]
    for c, pats in CONCEPTS.items()
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:example|tech|com|net|org|io|in|dev|app|co|xyz|info|biz|top|site|"
    r"online|shop|ru|cn|tk|ml|ga|cf|gq|cc|me|us|uk|de)\b",
    re.IGNORECASE,
)
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
# An IBAN written in groups of four ("DE89 3704 0044 0532 0130 00").
IBAN_SPACED_RE = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b")
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
ACCOUNT_NO_RE = re.compile(
    r"\b(?:account|a/c|acct)(?:\s*(?:no\.?|number|#))?\s*[:#-]?\s*(\d[\d -]{6,20}\d)",
    re.IGNORECASE,
)
# Hosts that are never someone's payment destination: collaboration and code sites. Private and
# loopback addresses are likewise never a payee.
BENIGN_HOSTS = (
    "github.com", "gitlab.com", "zoom.us", "google.com", "youtube.com", "wikipedia.org",
    "microsoft.com", "slack.com", "notion.so", "linkedin.com", "twitter.com", "x.com",
    "facebook.com", "example.com", "example.org", "calendly.com", "dropbox.com", "apple.com",
    "amazon.com", "localhost",
)  # fmt: skip
PRIVATE_IP_RE = re.compile(r"^(?:10\.|127\.|192\.168\.|169\.254\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.)")
# A verb that sends money or data somewhere: a web address only names a destination next to one.
SEND_VERB_RE = re.compile(
    r"\b(?:pay|pays|paying|paid|send|sends|sending|sent|wire|wires|wiring|wired|"
    r"transfer(?:s|red|ring)?|remit\w*|route[sd]?|routing|redirect\w*|forward\w*|deposit\w*|"
    r"settle[sd]?|settling|submit\w*|upload\w*|export\w*|cc|bcc)\b",
    re.IGNORECASE,
)
URL_HOST_RE = re.compile(r"\bhttps?://(?:[^\s/@]*@)?([^\s/:?#<>\"']+)", re.IGNORECASE)
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
UPI_RE = re.compile(r"\b[\w.-]{2,}@(?:upi|ok\w+|ybl|paytm|axl|ibl)\b", re.IGNORECASE)
# Reading a sentence, not just its words. A warning such as "never skip confirmation" or
# "X is not the trusted contact" uses the same words as the attack it warns about; these
# patterns let the checks tell the two apart. They are deliberately narrow: a negation counts
# only straight before the word it negates, and a prohibition only when it opens the sentence.
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
NEGATOR = (
    r"(?:never|not|cannot|can['’]t|\w+n['’]t|no longer|nunca|no|nie|niemals|nicht|kein(?:e|en)?)"
)
# "never skip", "do not ever bypass", "must not be disabled", "do not extend trust". One word
# may sit between, except words that undo the negation ("not only", "don't forget to").
NEGATED_BEFORE_RE = re.compile(
    NEGATOR
    + r"(?:\s+(?!(?:only|just|merely|also|forget|hesitate|fail|delay|wait)\b)[\w'’-]+)?"
    + r"(?:\s+to)?\s*$",
    re.IGNORECASE,
)
# "Requests to skip confirmation are a warning sign": a reported request, in a sentence that
# calls it a fraud sign.
REPORTED_BEFORE_RE = re.compile(
    r"\b(?:requests?|asks?|asking|asked|told|telling|urg(?:es|ing|ed)|pressur(?:e|ed|ing)|"
    r"demands?|demanding)(?:\s+\w+){0,2}\s+to\s*$",
    re.IGNORECASE,
)
FRAUD_LABEL_RE = re.compile(
    r"\b(?:fraud|phishing|scam|suspicious|red flag|warning sign|fake|impersonat\w*)\b",
    re.IGNORECASE,
)
# A sentence that forbids something: "Never forward ...", "Do not route ...". Not "Do not
# hesitate to ...", which asks for the opposite.
PROHIBITION_RE = re.compile(
    r"^\W*(?:and\s+|but\s+)?(?:never|do not|don['’]t|must not|mustn['’]t|should not|"
    r"shouldn['’]t|nunca|no\s+(?:env[ií]es|mandes|pagues)|nie|niemals)\b(?!\s+(?:hesitate|delay|"
    r"wait|worry|forget)\b)",
    re.IGNORECASE,
)
# Words that turn a prohibition into an allowance: "never pay anyone other than X".
EXCEPT_RE = re.compile(
    r"\b(?:other than|except|but|only|apart from|instead|rather than)\b", re.IGNORECASE
)
# Words that say an address is not to be trusted.
DISTRUST_RE = re.compile(
    r"\b(?:as\s+(?:unverified|untrusted|suspicious|unknown)|un(?:verified|trusted)|"
    r"look-?alike|impersonat\w*|phishing|fraud(?:ulent)?|scam)\b",
    re.IGNORECASE,
)

ZERO_WIDTH_RE = re.compile("[\u200b‌‍⁠﻿]")
BASE64_RE = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
HEX_RE = re.compile(r"\b[0-9a-fA-F]{16,}\b")
# Characters that are invisible or only reorder text: dropped before the word lists are read.
INVISIBLE_RE = re.compile(
    "[\u200b-\u200f\u00ad\u180e\u2060-\u2064\u202a-\u202e\u2066-\u2069\ufeff]"
)
# Letters from other scripts that look like Latin ones (Cyrillic and Greek).
CONFUSABLES = str.maketrans(
    {
        **dict(zip("аеорсхуіјѕԁԛһӏѵ", "aeopcxyijsdqhlv", strict=True)),
        **dict(zip("АВЕКМНОРСТХУІЈЅ", "ABEKMHOPCTXYIJS", strict=True)),
        **dict(zip("αονρικτυχ", "aovpiktuy", strict=True)),
        **dict(zip("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ", "ABEZHIKMNOPTYX", strict=True)),
    }
)
# "pay[at]evil[dot]example" and "pay at evil dot example".
_AT_RE = re.compile(r"\s*[\[({<]\s*at\s*[\])}>]\s*", re.IGNORECASE)
_DOT_RE = re.compile(r"\s*[\[({<]\s*dot\s*[\])}>]\s*", re.IGNORECASE)
_SPOKEN_ADDR_RE = re.compile(r"\b([\w.+-]+)\s+at\s+([\w-]+(?:\s+dot\s+[\w-]+)+)\b", re.IGNORECASE)
_LEET_TOKEN_RE = re.compile(r"\b(?=\w*[a-z])(?=\w*\d)\w+\b", re.IGNORECASE)


def normalize(text: str) -> str:
    """The text as a reader sees it: NFKC (fullwidth to plain), no invisible characters,
    look-alike Cyrillic and Greek letters folded to Latin, "[at]"/"[dot]" written out.

    A chunk with an "@" keeps its own letters, so a look-alike address is never folded into
    the owner's real one."""
    t = unicodedata.normalize("NFKC", text)
    t = INVISIBLE_RE.sub("", t)
    t = _AT_RE.sub("@", t)
    t = _DOT_RE.sub(".", t)
    t = _SPOKEN_ADDR_RE.sub(
        lambda m: m.group(1) + "@" + re.sub(r"\s+dot\s+", ".", m.group(2), flags=re.IGNORECASE),
        t,
    )
    return "".join(
        chunk if "@" in chunk else chunk.translate(CONFUSABLES) for chunk in re.split(r"(\S+)", t)
    )


def leet_forms(text: str) -> list[str]:
    """Readings of "d1sable the rev1ew step": digits inside a word turned back into letters
    (1 may be i or l). Only words that mix letters and digits change."""
    out = []
    for one in ("i", "l"):
        table = str.maketrans({"0": "o", "1": one, "3": "e", "4": "a", "5": "s", "7": "t"})
        out.append(_LEET_TOKEN_RE.sub(lambda m, t=table: m.group(0).translate(t), text))
    return out


def concepts_in(text: str) -> set[str]:
    """Return the set of concepts whose words appear in `text`."""
    found = set()
    for concept, patterns in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            found.add(concept)
    return found


def sentences(text: str) -> list[str]:
    """Split text into sentences (on . ! ? followed by space, and on line breaks)."""
    return [s for s in SENTENCE_RE.split(text) if s.strip()]


def spans(concept: str, text: str) -> list[tuple[int, int]]:
    """Every place a concept's words appear, as (start, end)."""
    return [m.span() for p in _COMPILED[concept] for m in p.finditer(text)]


def negated(text: str, start: int) -> bool:
    """True when the words straight before `start` negate it ("never skip", "not trusted")."""
    return bool(NEGATED_BEFORE_RE.search(text[:start]))


def reported(text: str, start: int) -> bool:
    """True for "requests to skip ..." in a sentence that calls it a fraud sign."""
    return bool(REPORTED_BEFORE_RE.search(text[:start])) and bool(FRAUD_LABEL_RE.search(text))


def prohibits(sentence: str) -> bool:
    """True when the sentence opens by forbidding something, with no exception carved out."""
    return bool(PROHIBITION_RE.search(sentence)) and not EXCEPT_RE.search(sentence)


def matches(concept: str, text: str) -> list[str]:
    return [m.group(0) for p in _COMPILED[concept] for m in p.finditer(text)]
