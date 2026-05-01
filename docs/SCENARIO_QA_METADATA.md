# Scenario QA Metadata

0.17.0 standardizes learner-facing QA metadata in each scenario.

## Core fields

```json
"hints": [
  "Start with the symptom and confirm the failure with the listed verification commands."
],
"expected_results": [
  "The symptom is resolved.",
  "Suggested verification commands show the intended state."
],
"answer_key": {
  "root_cause": "...",
  "fix_summary": "...",
  "verification": []
}
```

## Skill-check fields

Skill checks should also include:

```json
"requirements": [],
"grading_criteria": []
```

## Generated files

Each generated lab includes:

```text
hints.md
expected_results.md
answer_key.md
grading_criteria.md
requirements.md
verification.md
```

## QA command

```bash
./gns3_ccnp_lab_generator.py --qa-report
```
