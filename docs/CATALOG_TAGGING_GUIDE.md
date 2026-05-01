# Catalog Tagging Guide

1.4.0 adds normalized scenario tags to improve GUI lab discovery.

## Why tags exist

The older catalog relied heavily on one `domain` and one `topic` value. That made broad searches difficult. For example, many OSPF, BGP, static route, NAT, and VRF scenarios are routing-related, but they should not all use the single topic `Routing`.

Tags solve that problem.

## Scenario metadata fields

```json
{
  "domain": "Infrastructure",
  "topic": "OSPF",
  "tags": ["routing", "ospf", "igp", "infrastructure"],
  "primary_exam": "ENCOR",
  "progression_rank": [3, 2, 2, "OSPF", "..."]
}
```

## Tagging rules

Use tags for search and filtering. Use exam tags only when the lab genuinely belongs to that exam track.

```text
Use tags for technology relationships.
Use domain/topic for primary catalog organization.
Use exam_blueprints for exam scope.
Use primary_exam for the main intended audience.
```

## CCNA isolation rule

```text
Scenarios beginning with ccna_ are CCNA-only.
ccna_* scenarios must not be tagged as ENCOR.
```

This keeps ENCOR focused and prevents foundational CCNA labs from bloating professional-level study paths.

## Common tags

```text
routing
ospf
eigrp
bgp
static-routing
ipv4
ipv6
dual-stack
switching
vlan
trunking
etherchannel
stp
fhrp
nat
acl
security
device-access
dhcp
ntp
syslog
snmp
qos
multicast
wireless
automation
json
rest-api
python
netconf
restconf
assurance
skill-check
asav
nxos
fundamentals
```

## Study-plan ordering

Study plans should generally order labs by:

```text
1. Exam domain order
2. Foundational prerequisite order
3. Difficulty
4. Lab type
5. Topic-specific progression
```

For example, an ENCOR learner should generally see IGP and route-reachability labs before iBGP labs that depend on those underlay concepts.
