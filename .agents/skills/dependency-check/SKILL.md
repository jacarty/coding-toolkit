---
name: dependency-check
description: "Check a dependency before adding or bumping it: the current major release, at least 7 days old (the supply-chain cool-down in AGENTS.md), pinned exactly. Use when adding or upgrading any package, GitHub Action, container image, runtime or pre-commit hook, when setting up a new repo from the template, or when asked whether a version is safe to use."
---

# Dependency check

`AGENTS.md` sets the rule: current major releases only, nothing released in the last 7 days, pinned exactly. A compromised release is usually caught and pulled within days, so the wait is the defence.

## Steps

1. **Look up the release date; never recall it.** Use the registry or GitHub, in this session:
   - GitHub (actions, pre-commit hooks): `gh api 'repos/OWNER/REPO/releases?per_page=100' -q '.[] | select((.draft or .prerelease) | not) | "\(.tag_name) \(.published_at)"'`
   - npm: `npm view PACKAGE time --json`
   - PyPI: `https://pypi.org/pypi/PACKAGE/json`: each version under `releases`, with its files' `upload_time_iso_8601` (skip `yanked` files)
   - Go: go.dev/doc/devel/release

   Use the release's published date, not its commit date. If a project has tags but no releases, it can't be dated reliably: ask.

   These are the public defaults. If the project uses its own registry, see **Private registries and proxies** below first.
2. **Choose the newest release at least 7 days old on the current major.** Skip pre-releases. A newer major is its own change, not a side effect of a bump.
3. **Pin it exactly:**
   - GitHub Actions: `uses: owner/action@<sha> # v1.2.3 (YYYY-MM-DD)`.
   - pre-commit hooks: `rev: <sha>  # frozen: v1.2.3 (YYYY-MM-DD)`.

     For both, `<sha>` is the commit of the exact release tag (`v1.2.3`, never a moving `v1`): `gh api repos/OWNER/REPO/git/ref/tags/v1.2.3 -q .object`. If its `type` is `commit`, that `sha` is it. If it's `tag` (an annotated tag), the commit is `.object.sha` of `gh api repos/OWNER/REPO/git/tags/<that sha>`.
   - Packages: an exact version, with the lockfile committed. Set the tool's cool-down **before** installing (uv `exclude-newer`, pnpm `minimumReleaseAge`, Dependabot `cooldown`): pinning a package doesn't pin what it pulls in, and the lockfile would otherwise take transitive releases under 7 days old.
   - Runtimes: an exact patch. Images: the exact tag and its digest, `image:1.2.3@sha256:<digest>`.
4. **Check it still works.** For hooks: `pre-commit run --all-files`. Otherwise the project's tests.

## Private registries and proxies

Many organisations put a gateway or artifact repository (Artifactory, Nexus, AWS CodeArtifact, Azure Artifacts, Google Artifact Registry, a GitHub or GitLab package registry) in front of the public ones. When a project uses one, that registry is the source: it's where installs come from, and it may block or hold back releases on its own policy.

1. **Find out which registry the project uses**, from the project's config and the tool itself, not by reading credential files:
   - npm and pnpm: `.npmrc` in the project (`registry=`, `@scope:registry=`), or `npm config get registry`.
   - Python: `[[tool.uv.index]]` or `[[tool.poetry.source]]` in `pyproject.toml`, `UV_INDEX_URL` or `PIP_INDEX_URL`, or `pip config list`.
   - Go: `go env GOPROXY`. Containers: the registry in the image name. GitHub Actions and pre-commit hooks: the `uses:` or `repo:` URL, which may point at a mirror.

   Registry URLs and config can carry tokens (`https://user:token@…`, `_authToken=`). Never print, log or commit them; quote only the host. User-level credential files (`~/.npmrc`, `~/.pypirc`, `~/.docker/config.json`) are off limits.
2. **Look versions and dates up through that registry,** with the project's own tooling, which already uses it: `npm view PACKAGE time --json`, `pip index versions PACKAGE`, `uv pip install --dry-run`, or the registry's own UI or API.
3. **Know what the date means.** A proxy can show the date it cached a package, not the date it was published. For a public package, the upstream registry's publish date is the one that counts for the 7 days, so check it there if the proxy doesn't show it. Say which one you used.
4. **Never go around the registry.** Don't pass `--registry`, `--index-url` or another `GOPROXY` to get a version the gateway doesn't offer. If it blocks or quarantines a release, that's its policy: tell the user and ask.
5. **Never send internal package names to a public registry.** Looking up a private package on npmjs.com or pypi.org leaks its name, and a public package with the same name is how dependency-confusion attacks work. Internal packages are looked up only in the internal registry.

## Don't

- **Don't run `pre-commit autoupdate`.** It takes the newest release, however new.
- **Don't take a release under 7 days old**, even for a fix you need. Tell the user its date and what it fixes, and ask.
- **Don't update past a moved tag.** If a pinned tag no longer points at the pinned commit, stop and tell the user: it can mean a compromised release.
