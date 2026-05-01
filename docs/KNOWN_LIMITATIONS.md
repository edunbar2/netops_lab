# Known Limitations

This project is a practical GNS3 lab generator, not a complete replacement for official Cisco training, production design review, or hardware-specific validation.

## Controller-heavy technologies

The 1.0.0 release intentionally does not implement full deployments for:

```text
SD-WAN controllers
Catalyst Center / SD-Access controllers
ISE / TrustSec controller workflows
```

Related concepts may be represented through interpretation, architecture, or simulated workflows, but not full controller-based labs.

## Endpoint automation

VPCS endpoint auto-configuration is supported when using `--host-type vpcs`.

Alpine and RHEL9 endpoint console push is supported in 1.1.0, but Linux images can vary in login prompts, shell readiness, sudo/root behavior, and console timing. Generated setup files remain available for manual application.

## Image-specific behavior

Cisco images can differ by version and platform. Some commands may need minor adjustment depending on whether the lab uses IOL, IOSv, IOS-XE, ASAv, or NX-OSv.

## Template dependencies

The catalog expects matching GNS3 template names and IDs. The generator performs preflight checks, but users may still need to update the local catalog template metadata when moving to a new GNS3 environment.

## Automated grading

The project generates requirements, expected results, verification commands, grading criteria, and answer keys. It does not yet include a formal automated grading engine.

## Exam scope

The 1.0.0 curriculum is ENCOR-focused and non-controller-focused. It includes CCNA and ENARSI overlap tags, but those exams are not the primary completeness target for this release.
