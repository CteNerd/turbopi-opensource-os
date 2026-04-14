# Skill: Multi-Epic Sequential Delivery

Use this skill when executing multiple related epics in sequence (e.g., feature set roadmap).

## Goal
Complete a sequence of numbered epics efficiently, maintaining test coverage and PR hygiene across epic boundaries, while minimizing communication overhead.

## Prerequisites
- Epics are ordered in roadmap (e.g., #27, #28, #29) and build incrementally
- User provides minimal direction; assume autonomous execution with direction milestones
- Each epic has clear acceptance criteria and required docs
- Test suite exists and passes between epic boundaries

## Workflow for Each Epic

### 1) Fetch & Plan
- Read epic requirements from issue description and acceptance criteria
- Link required docs (docs/init/*, docs/api/*, etc.) in PR description
- Identify implementation touch points (files, modules, test stubs)

### 2) Implement Locally
- Create feature branch: `copilot/issue-<number>-<short-title>`
- Implement acceptance criteria incrementally
- Keep scope tight: only what the issue requests

### 3) Test & Validate
- Run full test suite: ensure no regressions from previous epics
- Add new tests for non-trivial logic (parsers, state machines, safety paths)
- Document test coverage in PR description

### 4) Open PR
- Title format: `(#ISSUE) <short description>`
- PR body includes: "Closes #ISSUE", acceptance checklist, required docs links, what changed
- Push and create PR; do NOT merge immediately

### 5) Await & Address Comments (5-Minute Gate)
- Wait ~5 minutes for Copilot review to be generated (Copilot review latency)
- Poll PR for unresolved review threads
- For each thread: implement fix (minimal, targeted) + reply + resolve
- Use `multi_replace_string_in_file` for multiple independent fixes (saves cost/time)
- Validate fixes with targeted test runs

### 6) Merge Gate Checks
- Verify: unresolved thread count = 0
- Verify: time elapsed since PR creation ≥ 5 minutes
- Verify: mergeable = true
- Answer: no status check failures blocking merge

### 7) Merge & Continue
- Squash merge to main; delete branch
- Switch to main and pull latest
- Proceed to next epic (repeat from step 1)

## Common Comment Categories & Response Patterns

### Code Quality Comments
- **Pattern**: "Add/fix logging", "Use consistent style", "Add error handling"
- **Response**: Minimal targeted fix; reply with what changed and why
- **Validation**: Run unit tests for touched module

### Safety/Contract Comments
- **Pattern**: "Validate input", "Check for timeout/disconnect", "Preserve arbiter path"
- **Response**: Implement validation; explain safety contract preserved
- **Validation**: Run safety-specific tests (disconnection handling, input boundary tests)

### Documentation Comments
- **Pattern**: "Fix link path", "Add missing field", "Clarify title"
- **Response**: Correct text/link; reply with before/after
- **Validation**: Visual inspection; no test needed for docs-only changes

### No-Change Comments
- **Pattern**: "Behavior already implemented", "This is by design"
- **Response**: Explain existing implementation/design decision
- **Validation**: Link to existing code or docs proving behavior

## Test Validation Checklist

After each epic:
- [ ] Full existing suite passes (no regressions)
- [ ] New tests added for non-trivial logic pass
- [ ] Failure paths covered (network errors, invalid input, timeouts)
- [ ] Replay/simulation tests remain deterministic (if applicable)
- [ ] Safety tests pass (if control/arbiter/HAL touched)

## Communication Pattern
- **During Implementation**: None (autonomous mode)
- **After Merge**: Auto-reply that epic is complete, ready for next
- **On Blockers**: Ask for clarification; do not guess

## Cost & Time Optimization
- Use `multi_replace_string_in_file` for multiple independent code fixes (1 call = N fixes)
- Batch file reads: read multiple ranges in parallel before edits
- Run targeted tests only (not full suite) after each fix validation

## Common Pitfalls to Avoid
1. **Import Consistency**: Mismatched import styles cause dual module loading; verify test imports align with production
2. **Timestamp Accuracy**: Simulations must use per-step deltas, not constants, for accuracy with real-world non-uniform data
3. **Persistence Failures**: Never silent-fail on config writes; return explicit 500 + log exception
4. **Early Merge**: Do not merge before 5-minute gate; Copilot review comments may arrive late
5. **Unresolved Threads**: Every thread must have a reply before resolution; "no-change" cases still require explanation

## Definition of Done (Per Epic)
- All acceptance criteria implemented
- PR description complete with required docs links
- All review comments addressed (fixes + replies + resolved threads)
- All tests passing with no regressions
- PR merged to main
- Branch deleted
