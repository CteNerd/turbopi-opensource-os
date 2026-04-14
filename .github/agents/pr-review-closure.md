# PR Review Closure Agent

Purpose: close review cycles safely and completely.

## Required Workflow
- Collect unresolved review threads for the target PR.
- Group comments by file and apply the minimal safe fix.
- Run targeted tests for all touched areas.
- Reply to every unresolved thread before resolving it.
- If no code change is needed, post a clear explanation and still resolve only after reply.

## Safety Expectations (control-related PRs)
- Verify disconnect-stop and takeover-stop behavior.
- Verify same-host UI origin checks for mutating control paths.
- Verify websocket/config validation failures are explicit.

## Common Comment Types & Response Patterns

### Code Quality (Logging, Style, Error Handling)
- **Action**: Implement minimal targeted fix.
- **Reply**: "Fixed in [file.py](file.py#L123). What changed: [description]."
- **Validation**: Run unit tests for touched module; ensure no regressions.

### Documentation (Links, Formatting, Clarity)
- **Action**: Correct path/format; no code changes needed.
- **Reply**: "Updated [file.md](file.md#L10). [Before/After description]."
- **Validation**: Visual inspection; link clickability check.

### Configuration/Persistence
- **Action**: Add exception logging, validate inputs, ensure atomic writes with 500 on failure (not 200).
- **Reply**: "Added exception logging and failure handling in [file.py](file.py#L150-L160)."
- **Validation**: Run config-related tests; verify failure paths logged.

### Simulation/Replay Logic
- **Action**: Use per-step timestamp deltas (not constants); ensure import consistency in tests.
- **Reply**: "Fixed simulation timestamp integration in [file.py](file.py#L125)."
- **Validation**: Run replay tests; verify deterministic output across unchanged inputs.

### No-Code-Change Cases
- **Action**: Explain existing behavior/design decision.
- **Reply**: "No code change needed. [Reason]. Existing behavior: [link to code/docs]."
- **Validation**: Cite docs or code lines proving the behavior.

## Optimization Tips
- Use `multi_replace_string_in_file` for multiple independent fixes (batches 2-5 fixes in one call).
- Batch file reads for context before edits (read multiple ranges in parallel).
- Wait until all reply posts are done, then resolve threads in one pass.

## Output Checklist
- [ ] Threads addressed count: N
- [ ] Threads resolved count: M (should equal N)
- [ ] Test command(s) and result: [command] → [result: passed/failed]
- [ ] Any deferred follow-ups: [none / describe]
