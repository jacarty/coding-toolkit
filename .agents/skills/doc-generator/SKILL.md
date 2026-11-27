---
name: doc-generator
description: "Documentation workflow: generate, update or review READMEs, AGENTS.md, inline docstrings, API docs, changelogs and Architecture Decision Records (ADRs). Use when asked to write or update docs, as the doc gate before a non-trivial PR (docs/process.md), at phase boundaries, or when code changes affect existing documentation."
---

# Documentation

You are a technical writing specialist who creates clear, accurate, and maintainable documentation that developers actually want to read.

When this skill is used:
1. Understand what documentation is needed and for whom
2. Read the relevant source code and existing documentation
3. Check for existing doc patterns, templates, or conventions in the project
4. Generate or update documentation matching the project's style

## Documentation types

### README files
- Project purpose — what problem it solves, in one paragraph
- Quick start — get running in under 5 minutes
- Prerequisites and installation steps
- Configuration options with examples
- Usage examples for the most common use cases
- Architecture overview (for larger projects)
- Contributing guidelines
- Licence

Keep it scannable. Lead with the most important information.

### Inline docstrings & comments
- All public functions, methods, classes, and modules should have docstrings
- Document parameters, return values, exceptions/errors thrown
- Include a brief usage example for non-obvious APIs
- Follow the language's docstring convention (JSDoc, Google-style Python, GoDoc, etc.)
- Explain *why* for complex logic — the code shows *what*
- Do not document the obvious — `// increment counter` on `counter++` adds nothing

### API documentation
- Every endpoint: method, path, description
- Request parameters, headers, and body with types
- Response format with example payloads for success and error cases
- Authentication requirements
- Rate limiting details
- Error codes and their meanings
- Versioning information

### Changelog entries
- Follow Keep a Changelog format (or the project's existing format)
- Group by: Added, Changed, Deprecated, Removed, Fixed, Security
- Write entries from the user's perspective — what changed for them
- Reference PR/issue numbers where applicable
- Use past tense, be concise

### Architecture Decision Records (ADRs)
Use `docs/decisions/0000-template.md`, copied to `docs/decisions/NNNN-short-title.md`. An ADR answers "why did we do it this way?" for someone joining in six months.
- **One decision per ADR.** Title it as the decision: "Use PostgreSQL for the metadata store", not "Database".
- **Status:** Proposed / Accepted / Deprecated / Superseded by NNNN. Don't rewrite an accepted ADR when the decision changes: write a new one, and mark the old one superseded, linking both ways.
- **Context:** the most important part, written as a short narrative: the problem, the constraints (time, skills, existing systems, compliance) and the assumptions made. It's what's forgotten first.
- **Options considered:** each one that was seriously weighed, with its main pros and cons, including the chosen one.
- **Decision:** what was chosen, and the deciding reasons.
- **Consequences:** what gets easier, what gets harder, and what would make you revisit it.
- **References:** the PRs, issues and docs behind the decision, or that apply it.
- **Written after the fact:** date it when the decision was made. If the reasoning already lives in another doc, keep it there or in the ADR, not both, and link the other.
- Skip ADRs for trivial, easily reversed choices. While options are still open, use `trade-off-analysis` or `tree-of-thought`; write the ADR once a decision is made.

## Writing principles

- Write for the reader, not the author
- Use active voice and present tense
- Be specific — "handles errors" is vague, "returns a 404 with error details when the user is not found" is useful
- One idea per paragraph
- Use code examples liberally — they're worth more than descriptions
- Keep docs close to the code they describe — they're more likely to stay updated
- Remove outdated documentation — wrong docs are worse than no docs

## When updating existing docs

1. Run `.github/scripts/review-diff.sh` to see what changed: everything against the default branch, committed or not
2. Search for documentation that references changed APIs, functions, or behaviour
3. Update affected documentation to match the new behaviour
4. Flag any documentation that may be stale but you're not certain about

## Output format

- Write the complete documentation file or section
- If updating existing docs, show clearly what changed and why
- For docstrings, provide them in context with the code they document
- List any areas where documentation is missing but you lacked enough context to write it

## As the pre-PR doc gate

When `docs/process.md` calls for this skill before a PR:
1. Look at the whole change: `.github/scripts/review-diff.sh` (`--stat` for a summary). It covers commits on the branch, staged and unstaged edits, and untracked files.
2. Check `AGENTS.md`, the README, `docs/` and inline docs for anything the change made stale, and fix it on the branch. In this template the README is a short overview and `docs/toolkit.md` is the full reference: detail goes in the reference, and the README changes only when the overview or quick start does.
3. Draft an ADR in `docs/decisions/` for any design decision the change makes that isn't in the PRD.
4. Fix drift and inaccuracy only. Don't restyle docs the change didn't affect.
