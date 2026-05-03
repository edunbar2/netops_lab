# Configuration-Guided Lab Expansion Plan

## Objective
Shift modality from troubleshooting-heavy content toward guided, configuration-first labs while preserving exam realism.

## Scope (Wave 1)
Implement the first 20 concepts from the generated shortlist, distributed across all study paths.

Target minimum per path in Wave 1:
- ccna-foundations: 5
- ccnp-enterprise: 5
- secure-enclave-networking: 4
- rhel9-operations: 3
- network-troubleshooting (rebalanced): 3

## Content Requirements (per new lab)
Each lab must include:
1. Clear skill objective (student-facing, no answer leakage)
2. Prerequisites
3. Config targets (protocols/features)
4. Guided walkthrough (6-10 steps)
5. Validation checks (commands + expected outcomes)
6. Common mistakes/coaching notes
7. estimated_minutes + difficulty
8. Study path mapping metadata

## Delivery Sequence
1. Author concept stubs in catalog metadata.
2. Add walkthrough + validation blocks.
3. Run catalog validation.
4. Run unit tests.
5. Review wording for anti-leakage.
6. Merge in small batches (3-5 labs per PR).

## Acceptance Criteria
- Wave 1 labs added with full metadata and walkthroughs.
- Validator: 0 errors; warnings unchanged or improved.
- Tests pass.
- Documented modality shift and updated per-path counts.

## Wave 1 Candidate Order (first pass)
1. ccna-vlan-trunk-native-hardening
2. ccna-router-on-a-stick-intervlan
3. ccna-ospf-single-area-baseline
4. ccna-standard-extended-acl-placement
5. ccna-fhrp-hsrp-gateway-redundancy
6. ccnp-ospf-multi-area-abrs-filtering
7. ccnp-bgp-ebgp-ibgp-localpref-med
8. ccnp-vrf-lite-mp-bgp-leak
9. ccnp-qos-classification-marking-policy
10. ccnp-netflow-flexible-monitor-export
11. senk-asav-inside-outside-nat
12. senk-asav-static-nat-dmz-publishing
13. senk-site2site-ipsec-ikev2-vti
14. senk-aaa-tacacs-local-fallback
15. rhel9-nmcli-static-ip-dns
16. rhel9-vlan-subinterfaces-nmcli
17. rhel9-firewalld-zones-services-richrules
18. nt-config-ip-sla-track-failover
19. nt-config-change-window-checkpoint-rollback
20. nt-config-golden-baseline-campus-switch
