# Curriculum QA Report

This report summarizes the 0.17.0 curriculum QA pass.

## Summary

```text
Scenario entries:    298
Unique concepts:     151
Skill checks:        4
Required QA fields:  14
```

## Required QA fields

```text
title
topology
exam_blueprints
domain
topic
difficulty
lab_type
symptom
faults
verification
hints
expected_results
answer_key
concept_id
```

## QA field completion

The 0.17.0 pass populated missing baseline QA fields across the catalog:

```text
hints
expected_results
answer_key
qa_status
learner_artifacts
```

Skill-check scenarios also use:

```text
requirements
grading_criteria
```

## Built-in QA command

```bash
./gns3_ccnp_lab_generator.py --qa-report
```

The command checks:

```text
Missing required QA fields
Missing skill-check fields
Invalid topology references
Malformed answer_key structures
Concept-ID duplicate behavior
Variant duplicate expectations
```

## Remaining QA expectation before 1.0.0

0.17.0 creates consistent metadata and generated artifacts. Before final 1.0.0, the remaining task is human review:

```text
Review scenario hints for usefulness
Review expected_results for exam relevance
Review answer_key summaries for clarity
Spot-check generated labs in GNS3
Confirm endpoint behavior with VPCS and preferred host type
```
