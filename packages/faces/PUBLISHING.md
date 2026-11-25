# Publishing kinfaces to npm

Nothing has been published. These are the exact steps for you to do by hand. You never
need to give anyone a token: `npm login` stores it on your machine.

## What you need

- An npm account (https://www.npmjs.com/signup) with **2FA enabled** (npm requires it to publish).
- Node 18+ and npm 9+ (`node -v`, `npm -v`).
- The name `kinfaces` was unclaimed when this was prepared (`npm view kinfaces` returned 404).
  Check again right before publishing, since names go to whoever publishes first:

  ```sh
  npm view kinfaces name
  ```

  If it is taken, either pick another name, or use a scope you own, e.g. `@your-npm-username/faces`
  (then edit `name` in `package.json`, the self-imports in `test/package.test.mjs`, the `kinfaces`
  imports in `apps/`, and publish with `--access public`).

## Steps

From a fresh checkout of the merged `main` (so the tarball matches what is on GitHub):

```sh
git checkout main && git pull
npm ci

# 1. Prove it works
npm test -w kinfaces
npm run lint -w @probate/web
npm run lint -w @probate/site

# 2. Look at exactly what will be published (should be dist/, README, LICENSE, CHANGELOG, gallery, package.json)
cd packages/faces
npm pack --dry-run

# 3. Log in (opens a browser or asks for your password + one-time code)
npm login
npm whoami

# 4. Publish. Scoped packages need --access public; unscoped ones are public anyway, the flag is harmless.
npm publish --access public
```

`prepublishOnly` runs `npm test` (which builds first), so a broken build cannot be published.
npm asks for your one-time 2FA code during `npm publish`.

Afterwards:

```sh
npm view kinfaces
git tag kinfaces-v0.1.0 && git push origin kinfaces-v0.1.0
```

and change `## [0.1.0] - Unreleased` in `CHANGELOG.md` to the publish date.

## Provenance (optional, needs CI)

npm provenance links the package to the exact GitHub commit and workflow that built it. It only
works from a supported CI provider (GitHub Actions), not from your laptop. If you want it:

1. Add a workflow with `permissions: { contents: read, id-token: write }` that runs
   `npm publish --provenance --access public` from `packages/faces`, using an npm
   *automation* token stored as the repository secret `NPM_TOKEN` (set it yourself in
   GitHub > Settings > Secrets; do not paste it anywhere else).
2. `package.json` already has the `repository` field provenance requires.

For a first release it is fine to publish from your laptop without provenance, and add the
workflow later.

## Later releases

1. Update `CHANGELOG.md`, bump the version: `npm version patch|minor|major -w kinfaces --no-git-tag-version`.
2. The default-family faces are pinned by tests; changing them is a breaking change (major).
3. Repeat steps 1 to 4 above.

## If something goes wrong

- `npm unpublish kinfaces@0.1.0` works only within 72 hours (and only if nothing depends on it);
  prefer publishing a fixed patch and `npm deprecate`.
- `E403` on publish: you are not logged in, 2FA is off, or the name is taken by someone else.
- `E402`: scoped package without `--access public`.
