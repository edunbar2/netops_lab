# Exam Tagging Policy

This catalog supports multiple exam tracks. Scenario exam tags should be intentional and not used as a generic difficulty label.

## Policy

```text
CCNA-only foundation scenarios use IDs beginning with ccna_.
ccna_* scenarios must have exam_blueprints = ["CCNA"].
ccna_* scenarios must have primary_exam = "CCNA".
ENCOR study paths should not include ccna_* scenarios.
```

## Rationale

A professional-level ENCOR learner should already know many CCNA fundamentals. Including all CCNA foundation scenarios in ENCOR would inflate ENCOR counts and make ENCOR study paths less focused.

## 1.3.0 audit result

```text
ccna_* scenarios with non-CCNA tags: 0
ENCOR unique lab concepts: 158
CCNA unique lab concepts: 85
```

The one previously accidental ENCOR tag on a `ccna_*` IPv6 lab was removed in 1.3.0.
