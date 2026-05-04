# Curriculum QA Report

This report summarizes the current catalog QA state computed from `catalogs/ccnp_encor_lab_catalog.json`.

## Summary

```text
Scenario entries:    447
Unique concepts:     238
Skill checks:        23 entries / 12 unique concepts
Study plans:         9
Required QA fields:  14
QA issues:           0
QA errors:           0
QA warnings:         0
```

## Built-in QA command

```bash
./gns3_ccnp_lab_generator.py --qa-report
```

Current output summary:

```text
Catalog QA Report
=================
Scenario entries: 447
Unique concepts:  238
Issues:           0
Errors:           0
Warnings:         0
Expected variant duplicate groups: 207

No QA issues found.
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

The catalog has complete guided-content structure for all scenarios, including:

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

## What the QA command checks

```text
Missing required QA fields
Missing skill-check fields
Invalid topology references
Malformed answer_key structures
Concept-ID duplicate behavior
Variant duplicate expectations
```

## Remaining QA expectation before 1.0.0

Current automated QA reports zero issues. Remaining work is human review and runtime spot-checking:

```text
Review scenario hints for usefulness and specificity
Review expected_results for exam and operations relevance
Review answer_key summaries for clarity
Spot-check generated labs in GNS3
Confirm endpoint behavior with VPCS and preferred host type
Keep guided study plans synchronized with catalog reality
```
