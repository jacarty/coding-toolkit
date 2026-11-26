---
name: debugging
description: "Find and fix the root cause of a bug: reproduce it, narrow it down, test one hypothesis at a time, fix the cause, and add a regression test. Use for a bug report, a failing test or CI job, an error or stack trace, or behaviour that differs from what's expected, before proposing a fix."
---

# Debugging

Find the cause before changing code. A fix that wasn't preceded by a reproduction is a guess.

## Steps

1. **Reproduce it.** Find the exact command, input or steps, and run them. Record the real output: the error, the exit code, the wrong result.
   - For a CI failure, read the job's log first, then reproduce it locally with the same command and versions.
   - If it can't be reproduced, stop and say so, with what you tried. Ask for the missing detail (input, environment, version) rather than fixing blind.
2. **Read what it tells you.**
   - An error: the full message and stack trace, the first failure rather than the last. Find the line it points at before forming a theory.
   - A wrong result, with no error: work out the expected value by hand, then follow the intermediate values until they first differ from yours. That's where to look.
3. **Narrow it down.**
   - Shrink the input to the smallest one that still fails.
   - If it used to work, find the change that broke it: `git log -p` on the files involved, and if no commit stands out, `git bisect` with the reproduction as the test.
   - Check the boundaries: what goes into the failing function, and what comes out.
4. **One hypothesis at a time.** State it, and what evidence would confirm or rule it out. Change or add one thing (a log line, an assertion, a value), rerun, and look. Remove temporary logging afterwards.
   - For a regression, the most direct check is the reproduction against the last good version (`git show <rev>:<file>`, or a checkout in a separate worktree).
   - When a theory is ruled out, say so and drop it. Don't stack fixes for several theories.
5. **Settle what's correct, then fix the root cause.**
   - Know the intended behaviour before choosing a fix: the spec, the tests, the reporter. "What it did before" isn't automatically right. If the rule is ambiguous (rounding, time zones, ordering), ask.
   - The fix goes where the cause is, not where the symptom shows. If the cause is outside the change's scope (another module, a dependency, the platform), fix what's needed here, record the rest in `docs/tech-debt.md`, and tell the user.
6. **Add a regression test.** Write it before the fix and watch it fail, then fix and watch it pass. If the fix came first, check it both ways (stash only the fix, `git stash push -- <fix files>`, rerun, then `git stash pop`). If no test can be written, say why.
   - Look for the same mistake elsewhere (the same pattern, the same helper used by other callers) and cover those too, or list them.
7. **Check the result.** Rerun the original reproduction, then the project's tests. Then use what was fixed the way it's used (the **run it** gate in `docs/process.md`); for library code with no app, the reproduction through its public interface is that use.
8. **Report.** The cause, the evidence, the fix, and the test, kept short. Add how the bug got through if it says something (no test covered the case, a "refactor" that changed behaviour). Then run any pre-PR gates `docs/process.md` calls for, and hand over with the `commit-and-pr` skill.

## Don't

- **Don't change several things at once.** You won't know which one mattered, and the rest become unexplained changes.
- **Don't make the symptom go away:** no catching and ignoring errors, no loosening or deleting tests, no retries or sleeps over a race you haven't explained.
- **Don't get past a failure by skipping hooks or editing permission, sandbox or CI settings.** If one of those is the cause, tell the user.
- **Don't print secrets while investigating.** Environment variables, config and logs can hold tokens: check whether a value is set, not what it is.
