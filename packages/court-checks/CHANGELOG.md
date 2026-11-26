# Changelog

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
