# Security policy

Probate is a **hackathon project** built for Fly.io Hacksgiving 2026. It is a research demo of
how to screen an agent's memory before the next generation inherits it, not a hardened product.
It has had no external audit. Please do not rely on it to protect real data.

## Supported versions

Only the latest commit on `main` is supported. There are no tagged releases and no backports.

## Reporting a vulnerability

Please report privately. Do not open a public issue or pull request for a vulnerability.

1. Go to the [Security tab](https://github.com/harshbhx/probate/security) of this repository.
2. Choose **Report a vulnerability** (GitHub private vulnerability reporting).
3. Describe what you found, how to reproduce it, and what you think the impact is.

If that option is not available, open a public issue that says only that you have a security
report to share (no details), and the maintainer will arrange a private channel.

This is a one-person project. Expect an acknowledgement within about a week and a fix or a
written assessment on a best-effort basis. Reporters are credited in the fix unless they prefer not to be.

## What is in scope

Scope follows the project's own threat model, [`docs/12-THREAT-MODEL.md`](docs/12-THREAT-MODEL.md).
Reports are welcome about:

- A way to get a poisoned will item **approved** by the court (layer 1 code checks or layer 2 Jev questions),
  or a way to make the court fail open instead of closed (contested).
- A way to weaken or poison the family genome (instincts).
- Court injection: text inside a will item that steers the judge.
- Leaks or injection through the public site, including "Ask an ancestor" (data leaks, instruction following, rate-limit bypass).
- Anyone other than the owner being able to approve or reject held items by email.
- Secrets, tokens or personal addresses committed to the repository, or reachable from a generation Sprite.
- Vulnerabilities in the code of the Courthouse API (`services/core`) or the web apps.

## Out of scope

As stated in the threat model:

- A compromised Fly.io, TypeSafe, Box, Pinecone or AgentMail account, and physical access.
- Supply-chain attacks on PyPI or npm packages, and vulnerabilities in third-party services themselves
  (report those to the vendor).
- The fixed attack suite in `fixtures/` working as intended: those emails are deliberate, harmless test data.
- Denial of service by volume against the public demo, and social engineering of the maintainer.
- Findings that need a model to behave differently from its documented limits (see "Limits" in the README).

## Testing rules

Test only against your own local copy (`make sim`, `PROBATE_FAKE=1`) or your own accounts.
Do not send attack emails to the live family inbox, to the maintainer's addresses, or to any third party.
