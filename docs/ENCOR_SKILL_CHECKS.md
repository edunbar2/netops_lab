# ENCOR Skill Checks

0.18.0 expands the configure-from-requirements skill-check catalog for ENCOR.

## Study plan

```bash
./gns3_ccnp_lab_generator.py --list-study-plan encor-skill-checks
```

The plan is also visible in the GUI study-plan selector.

## ENCOR skill checks

```text
skill_encor_ipv6_foundation
skill_encor_dual_stack_campus
skill_encor_ospf_multi_area_advanced
skill_encor_eigrp_advanced
skill_encor_bgp_edge
skill_encor_qos_trust_boundary
skill_encor_security_edge
skill_encor_automation_assurance
skill_encor_enterprise_wan_capstone
```

## Coverage intent

These labs are not single-fault troubleshooting labs. They are configure-from-requirements checks.

They cover:

```text
IPv6 foundation
IPv4/IPv6 dual-stack
Advanced OSPF
EIGRP advanced routing
BGP edge routing
QoS trust boundary and WAN policy
Security edge policy
Automation and assurance workflow
Enterprise WAN capstone
```

## Notes

The enterprise WAN capstone remains the large penultimate/final-style skill check. It includes HQ, multiple field offices, ISP transit, and partner-company reachability.

The EIGRP skill check is included because it remains valuable for advanced routing competence and many learners still expect it as part of professional-level routing practice, even if blueprint emphasis varies by exam version.
