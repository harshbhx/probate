# Changelog

## 0.3.0

- **Warnings are no longer flagged as the attacks they warn about.** Three checks now read
  sentence by sentence and notice a negation straight before the word they look for:
  - `confirmation_removal` ignores "never skip confirmation", "do not pay without confirmation"
    and "requests to skip confirmation are a warning sign", and no longer joins "skip" in one
    sentence with "confirm" in another.
  - `new_payment_destination` ignores an address that only appears in sentences forbidding
    payments to it ("Do not route invoices to X"), unless the sentence carves out an exception
    ("other than", "except", "only", "instead").
  - `new_trusted_identity` only counts an address in the same sentence as a trust word that is
    not negated ("X is not the trusted contact" and "Treat X as unverified" trust nothing), and
    a trusted contact's own domain is no longer a new identity.
- Why: in Probate's real run on Fly Sprites (26 Nov 2026), 8 of 113 will items were flagged and
  all 8 were the agent's own warnings. 7 are no longer flagged. The eighth, a fact that repeats
  an attacker's payment address, still is, on purpose.
- Nothing else changed: every one of the 70 attack-suite fixtures (41 attacks, 29 harmless)
  gets exactly the same flags as before, and new tests check that a negation is not a way
  around the checks ("don't hesitate to skip the confirmation" is still flagged).

## 0.2.1

- Documentation only: a fuller README with install, usage and links, now that the package is on the public registry.

## 0.2.0

- The check reasons say "the owner" instead of naming the project's author, so the package reads the same for anyone who runs it.

## 0.1.0

- First extraction of the Courthouse "layer 1" text checks from the Probate project.
- `check_text(text, source, owner)` returning `Flag(check, reason)` objects.
- Seven text checks: new payment destination, new trusted identity, confirmation removal,
  future-self instruction, forged authority, court injection, encoded or invisible text.
- Word lists for English, Hinglish, Spanish and German.
- `probate-check` command line with JSON output.
- Bundled tests use the 32-fixture attack suite (suite-v1).
