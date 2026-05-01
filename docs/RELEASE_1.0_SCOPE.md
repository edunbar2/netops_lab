# Release 1.0.0 Scope

GNS3 CCNP Lab Generator 1.0.0 is the first stable baseline release for the project.

## Included

```text
Non-controller ENCOR practical curriculum
Troubleshooting labs
Configure-from-requirements skill checks
Dedicated ENCOR skill-check track
Guided study plans
Cross-platform GUI
CLI workflow
GNS3 API project generation
Cisco IOS/IOL/IOSv config push
VPCS endpoint auto-configuration
Generated Linux endpoint setup artifacts
Template adapter preflight
Scenario QA metadata
QA report command
Coverage and study-plan documentation
```

## Excluded

```text
Full SD-WAN controller deployment
Full Catalyst Center / SD-Access controller deployment
Full ISE / TrustSec controller workflows
Guaranteed Linux endpoint auto-push across all images
Formal automated grading engine
```

## 1.0.0 counts

```text
Templates:                14
Topologies:               40
Unique lab concepts:      159
Scenario entries:         314
Legacy/fallback entries:  155
```

Unique lab concepts by exam tag:

```text
CCNA:   31
ENCOR:  159
ENARSI: 39
```

Unique ENCOR concepts by domain:

```text
Architecture:       6
Automation:         17
Infrastructure:     66
Network Assurance:  16
Security:           34
Skill Check:        12
Virtualization:     8
```

## Release standard

A 1.0.0 package should satisfy these conditions:

```text
--version works
--stats works
--coverage works
--qa-report returns zero errors
Study plans load
GUI launches and exposes study-plan selection
Template preflight remains enabled by default
Generated labs include learner and answer artifacts
```

## 1.1.0 update

1.1.0 extends the 1.0 baseline with Alpine and RHEL9 endpoint auto-push plus richer generated student briefs. The curriculum scope remains unchanged.
