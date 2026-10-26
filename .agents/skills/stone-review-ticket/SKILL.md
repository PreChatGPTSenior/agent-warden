---
name: stone-review-ticket
description: Independently review a frozen Stone Shelter application candidate with current static evidence.
---

# Stone Review Ticket

Use execution/prompts/code_review.md. Require candidate identity, raw static reports, base diff, task scope and OpenSpec requirements. Review the change and tests without editing; model/framework imports alone do not prove correct architecture. Return APPROVED or actionable findings using templates/agent-result.schema.json. Never approve stale content or review your own development session.
