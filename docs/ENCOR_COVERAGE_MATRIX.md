# ENCOR Coverage Matrix

Counts below are **unique lab concepts**, not `_iosv` or fallback scenario entries.

## Summary

- Templates: 14
- Topologies: 31
- Scenario entries: 291
- Unique lab concepts: 147

## By exam tag

| Exam | Unique concepts |
|---|---:|
| CCNA | 28 |
| ENARSI | 26 |
| ENCOR | 117 |

## By ENCOR-style domain

| Domain | Unique concepts |
|---|---:|
| Infrastructure | 56 |
| Security | 24 |
| Network Assurance | 12 |
| Automation | 11 |
| Virtualization | 8 |
| Architecture | 6 |

## By topic

| Topic | Unique concepts |
|---|---:|
| Multicast | 10 |
| OSPF | 8 |
| ASAv | 6 |
| BGP | 5 |
| OSPFv3 | 5 |
| QoS | 5 |
| HSRP | 4 |
| NAT | 4 |
| AAA | 3 |
| ACLs | 3 |
| EEM | 3 |
| GRE | 3 |
| IPv6 | 3 |
| Syslog | 3 |
| VRF | 3 |
| CoPP | 2 |
| DHCP Snooping | 2 |
| Device Access | 2 |
| Flexible NetFlow | 2 |
| IP SLA | 2 |
| Layer 2 Trunking | 2 |
| NX-OS | 2 |
| PBR | 2 |
| Port Security | 2 |
| REST APIs | 2 |
| RESTCONF | 2 |
| Redistribution | 2 |
| SNMP | 2 |
| STP | 2 |
| Campus Design | 1 |
| Dynamic ARP Inspection | 1 |
| Errdisable | 1 |
| EtherChannel | 1 |
| High Availability | 1 |
| IPv6 ACLs | 1 |
| JSON | 1 |
| Management Plane | 1 |
| NETCONF | 1 |
| NTP | 1 |
| Overlay Concepts | 1 |
| Path Selection | 1 |
| Python | 1 |
| QoS Design | 1 |
| RSPAN | 1 |
| Routing | 1 |
| SPAN | 1 |
| Services | 1 |
| Storm Control | 1 |
| VLANs | 1 |
| YANG | 1 |

## By difficulty

| Difficulty | Unique concepts |
|---|---:|
| easy | 46 |
| hard | 7 |
| intro | 1 |
| medium | 63 |

## Notes toward 1.0.0

The curriculum is now broad enough that remaining work should emphasize quality, answer keys, repeatable validation, guided tracks, and gap closure rather than only adding raw scenario volume.

Recommended remaining release sequence:

```text
0.12.0  Advanced routing depth: redistribution, filtering, summarization, path selection
0.13.0  Security/ASAv depth and policy edge cases
0.14.0  Automation/assurance workflow depth and mock API exercises
0.15.0  Curriculum QA: answer keys, hints, expected outputs, weak-scenario cleanup
1.0.0   Feature-complete ENCOR non-controller curriculum baseline
```
