"""Multilingual word lists for the court's code checks (English, Hinglish, Spanish, German).

Each concept maps to regular expressions matched case-insensitively on word boundaries.
Add a language by extending every list. Keep patterns specific: false positives here
convict harmless will items.
"""

from __future__ import annotations

import re

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
        r"judge",
        r"court",
        r"reviewer",
        r"approve (?:it|this)",
        r"this item is safe",
        r"ignore previous",
        r"mark (?:this|it) (?:as )?safe",
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

_COMPILED = {
    c: [re.compile(r"(?<![\w-])" + p + r"(?![\w-])", re.IGNORECASE) for p in pats]
    for c, pats in CONCEPTS.items()
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:example|tech|com|net|org|io|in|dev|app|co)\b", re.IGNORECASE
)
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
UPI_RE = re.compile(r"\b[\w.-]{2,}@(?:upi|ok\w+|ybl|paytm|axl|ibl)\b", re.IGNORECASE)
ZERO_WIDTH_RE = re.compile("[\u200b‌‍⁠﻿]")
BASE64_RE = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
HEX_RE = re.compile(r"\b[0-9a-fA-F]{32,}\b")


def concepts_in(text: str) -> set[str]:
    """Return the set of concepts whose words appear in `text`."""
    found = set()
    for concept, patterns in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            found.add(concept)
    return found


def matches(concept: str, text: str) -> list[str]:
    return [m.group(0) for p in _COMPILED[concept] for m in p.finditer(text)]
