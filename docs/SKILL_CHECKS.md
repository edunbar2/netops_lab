# Skill Checks

Skill checks are configure-from-requirements labs rather than single-fault troubleshooting labs.

They are designed to assess whether the learner can build a working configuration from a realistic requirement set.

## Current study plan

```bash
./gns3_ccnp_lab_generator.py --list-study-plan skill-checks
```

## Included skill checks

```text
skill_ccna_access_edge_basic
skill_encor_campus_routing_intermediate
skill_enarsi_advanced_routing
skill_encor_enterprise_wan_capstone
```

## Generated output layout

0.16.0 makes the output layout explicit:

```text
configs/                 Starter/starter/faulty configs, retained for backward compatibility
starter_configs/         Starter configs intended for the learner
clean_configs/           Known-good configs, retained for backward compatibility
answer_key_configs/      Known-good answer configs
endpoint_setup/          Endpoint setup files
requirements.md          Lab requirements
hints.md                 Hints, if documented
expected_results.md      Expected success indicators, if documented
verification.md          Suggested verification commands
student_brief.md         Learner-facing brief
answer_key.md            Root-cause/fix summary and metadata
lab_manifest.json        Machine-readable manifest
```

## Capstone intent

The enterprise WAN capstone includes:

```text
Campus HQ
Multiple field offices
ISP transit
Partner company A
Partner company B
Preconfigured ISP/partner routers
Enterprise routers requiring user configuration
```

The learner must configure company routing so field offices and HQ can communicate and so enterprise sites can reach required partner networks across the ISP.

## Answer-key behavior

The clean generated configs represent one possible answer key / target state.

The starter/faulty generated configs are intentionally incomplete and are the configs intended to be loaded for the learner.


## ENCOR skill-check expansion

0.18.0 adds a dedicated ENCOR skill-check plan:

```bash
./gns3_ccnp_lab_generator.py --list-study-plan encor-skill-checks
```

New ENCOR checks:

```text
skill_encor_ipv6_foundation
skill_encor_dual_stack_campus
skill_encor_ospf_multi_area_advanced
skill_encor_eigrp_advanced
skill_encor_bgp_edge
skill_encor_qos_trust_boundary
skill_encor_security_edge
skill_encor_automation_assurance
```

The existing enterprise WAN capstone is included as the final step in the ENCOR skill-check plan.
