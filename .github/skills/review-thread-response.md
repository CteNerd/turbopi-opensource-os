# Skill: Review Thread Response

Use this skill when handling pull request comments.

## Goal
Ensure every review comment gets a complete response path:
1) code fix + reply, or
2) no-change explanation + reply.

## Steps
- Read unresolved threads and identify concrete asks.
- Implement only required fixes.
- Validate with targeted tests.
- Post one concise reply per unresolved thread.
- Resolve threads after replies are posted.

## Reply Template
- What changed: <file/behavior>
- Why it addresses feedback: <safety/contract reason>
- Validation: <test command/result>

## No-Change Template
- Reason no code change is required
- Clarification of existing behavior/docs
- Optional follow-up item if needed
