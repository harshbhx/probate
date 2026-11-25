# Publishing probate-client (npm)

Run these yourself. Nothing here needs a token in the repo.

1. Check the name is still free: `npm view probate-client` should say 404.
2. From the repo root: `npm ci`, then `npm run lint -w probate-client` and `npm test -w probate-client`.
3. Set the version in `packages/client/package.json` and move the CHANGELOG entry from "unreleased" to a date.
4. Look at what will ship: `cd packages/client && npm pack --dry-run` (expect `dist/`, README, LICENSE, CHANGELOG).
5. Log in: `npm login` (follow the browser or OTP prompt; enable 2FA on the account).
6. Publish: `npm publish --access public`
   (`prepack` rebuilds `dist/` first).
7. Verify: `npm view probate-client version`, then in a scratch folder `npm i probate-client` and import it.
8. Tag: `git tag client-v0.1.0 && git push origin client-v0.1.0`.

A mistake can be undone within 72 hours with `npm unpublish probate-client@0.1.0`; after that publish a new patch version.
