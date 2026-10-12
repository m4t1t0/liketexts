---
description: Implement a whole spec via the implement-spec skill
agent: general
---
Use the implement-spec skill to implement the whole current spec in one run: read the tickets as a task graph, run implementer subagents in their own worktrees across the ready frontier, and land everything on one integration branch, closing out with the code-review skill. Follow Liketexts conventions and the verification suite (make test, make lint, make typecheck, openapi-check, frontend build).
