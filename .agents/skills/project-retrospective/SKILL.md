---
name: project-retrospective
description: "Run a short, structured retrospective on finished work: goal against outcome, what went well and what didn't (to root cause), and at most three follow-ups worth acting on. It's a draft until the user has confirmed each item; only what they confirm is saved. Use only when the user asks for a retro, post-mortem or lessons learned, or at the end of a build-guide phase or project. Not after every PR."
---

# Project retrospective

Capture what happened, why, and the few changes worth making. A retro is worth reading only if it's short and changes something: one page, and at most three follow-ups.

## When

- When the user asks for one.
- At the end of a build-guide phase or a project (`docs/process.md`, phase boundaries).

Not after every PR or review round: a bad PR is material for the next retro, not a reason for one. Not while the work is still in progress.

## 1. Gather the evidence

Work from the record, not memory:
- **the goal:** the PRD section, build-guide phase or tracked issue. If none was written down, rebuild it from the PRs' "Why" sections, and say in the retro that it wasn't recorded;
- **what happened:** `git log` and the merged PRs for the period (`gh pr list --state merged`, then `gh pr view N` for each body). If `gh` can't run (no network, or a sandbox), use `git log` alone and say so in the retro. The PR bodies are the richest record: the **Testing**, **Known gaps** and gate sections. Also look at how many review rounds each PR took, and at reverted or reset work;
- **what was written down on the way:** `docs/tech-debt.md`, `docs/decisions/`, earlier retros in `docs/retrospectives/`;
- **the user's view:** ask 2–3 questions about what isn't in the record (what felt slow, what surprised them). If they can't be asked, say so, and mark anything you infer instead as "not confirmed".

## 2. Write it up

Keep the draft to one page: if it runs longer, cut items rather than shorten them. At the top: the work in one sentence, the goal, the outcome, and the period. Then **up to 3 items per section** (skip a section if nothing fits; don't pad):

- **What went well:** what happened, and why it worked.
- **What didn't go well:** what happened, the root cause (ask "why?" until it's a cause, not a symptom), and what it cost. Name the system, not a person: "no test covered rounding", not "X broke it".
- **Surprises:** what wasn't expected, and the early sign to watch for next time. On a success, ask what almost went wrong.

Be concrete, and cite the PR, commit or issue behind each item. "Communicate better" changes nothing; "run the change once before opening the PR" does.

Write as if the repo will be public, from the first draft: no credentials, environment values, account IDs, project numbers, internal hostnames, emails, request bodies or raw logs. If the tracker is private and the repo isn't, describe an issue rather than linking it.

## 3. Follow-ups

**At most three**, and only for something that happened more than once or cost real rework (a reset, a repeated review round, a bug that shipped). Everything else stays in the retro as a note. Rank by cost, and cut the rest.

For each follow-up, say what it is and recommend one way to do it, with the alternatives in a line:
- a change to the process or rules (`docs/process.md`, `AGENTS.md`, a skill), proposed as a PR;
- a known gap: a row in `docs/tech-debt.md`;
- work: a tracked issue, or, with no tracker, a line in the retro's follow-ups.

The user decides which to take (`AGENTS.md`); don't change the process in the retro itself.

## 4. Review it with the user

Everything so far is a draft: keep it in the conversation or a scratch file outside the repo, never in `docs/retrospectives/`. Show it to the user and go through it with them before anything is saved. The "not confirmed" marks show them what to check first:
- each item: keep, correct or drop. Anything they don't confirm comes out, including every "not confirmed" inference;
- each follow-up: take it, change it or drop it, and the option to use;
- anything missing that they think matters.

Only what they confirm is saved. If the user isn't available, leave the draft outside the repo and say it's waiting for review: don't save or commit an unreviewed retro.

## 5. Save it

Write the confirmed retro to `docs/retrospectives/YYYY-MM-DD-<slug>.md` (create the folder the first time). It goes through a PR like any doc; most fit the fast path. Add the confirmed tech-debt rows to that PR, and open the confirmed issues; process changes go in PRs of their own. Link the retro from the phase's or project's tracked issue, if there is one.
