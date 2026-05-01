# ENCOR Lab Curriculum Coverage

This file tracks curriculum-oriented coverage for the lab generator.

## Counting model

Use **unique lab concepts** for curriculum completeness. Scenario entries include platform variants such as `_iosv` legacy duplicates.

Current counts:

```text
Unique lab concepts: 79
Scenario entries: 153
Legacy duplicate entries: 74
```

## Current release

```text
Release: v20 IPv6 / OSPFv3 curriculum wave
Templates: 11
Topologies: 18
Scenarios: 113
```

## Current exam tags

```text
CCNA:   42
ENCOR:  113
ENARSI: 44
```

## Completed focused waves

### v20 — IPv6 / OSPFv3 / dual-stack

Added:

```text
dual_stack_ipv6_campus
dual_stack_ipv6_campus_iosv
```

Added lab concepts:

```text
IPv6 unicast routing missing
OSPFv3 area mismatch
OSPFv3 passive interface
OSPFv3 duplicate router ID
OSPFv3 missing interface enablement
IPv4 works / IPv6 fails
IPv6 ACL blocks traffic
IPv6 wrong prefix
OSPFv3 network type mismatch
```


### v21 — Network Assurance

Added:

```text
network_assurance_lab
network_assurance_lab_iosv
```

Added lab concepts:

```text
Syslog wrong host
Syslog trap level too restrictive
SNMP ACL blocks collector
SNMP community mismatch
Flexible NetFlow exporter wrong destination
Flexible NetFlow monitor missing from interface
SPAN wrong source interface
RSPAN VLAN missing remote-span
IP SLA wrong probe target
NTP wrong server
```

Current catalog after v21:

```text
Templates: 11
Topologies: 20
Scenarios: 133
CCNA-tagged scenarios: 42
ENCOR-tagged scenarios: 133
ENARSI-tagged scenarios: 46
Network Assurance scenario entries: 24
```


### v22 — Security hardening and deeper ASAv

Added:

```text
security_hardening_lab
security_hardening_lab_iosv
```

Added unique lab concepts:

```text
Local user privilege too low
VTY allows Telnet
AAA method list not applied to VTY
AAA missing local fallback
ACL sequence shadows permit
ACL applied in wrong direction
CoPP blocks OSPF
ASAv DMZ security level wrong
ASAv static NAT uses wrong DMZ host
ASAv outside ACL missing HTTPS permit
```

Current catalog after v22:

```text
Templates: 11
Topologies: 22
Unique lab concepts: 79
Scenario entries: 153
Legacy duplicate entries: 74
CCNA unique lab concepts: 23
ENCOR unique lab concepts: 79
ENARSI unique lab concepts: 24
Security unique lab concepts: 18
```


### v23 — Automation / NETCONF / RESTCONF / JSON / EEM

Added:

```text
automation_api_lab
automation_api_lab_iol
```

Added unique lab concepts:

```text
RESTCONF disabled
NETCONF/YANG disabled
RESTCONF authentication missing local user
EEM applet wrong syslog pattern
EEM applet missing enable action
Invalid JSON inventory
RESTCONF 404 wrong endpoint
RESTCONF 401 authentication failure
YANG interface payload interpretation
Python parser bug
```

Current catalog after v23:

```text
Templates: 11
Topologies: 23
Unique lab concepts: 87
Scenario entries: 171
Legacy/fallback entries: 84
CCNA unique lab concepts: 23
ENCOR unique lab concepts: 87
ENARSI unique lab concepts: 24
Automation unique lab concepts: 11
```


### v24 — QoS + Architecture

Added:

```text
qos_architecture_lab
qos_architecture_lab_iosv
```

Added unique lab concepts:

```text
WAN QoS policy missing
Voice class matches wrong DSCP
Priority queue missing
Access port trust boundary wrong
Phone port not trusting CoS
Access-layer single point of failure
Wrong default gateway placement
Suboptimal WAN path selection
Underlay/overlay mapping error
QoS marking at wrong layer
```

Current catalog after v24:

```text
Templates: 11
Topologies: 25
Unique lab concepts: 97
Scenario entries: 191
Legacy/fallback entries: 94
CCNA unique lab concepts: 24
ENCOR unique lab concepts: 97
ENARSI unique lab concepts: 25
Architecture unique lab concepts: 6
Infrastructure unique lab concepts: 42
```

## v25 operational bugfix note

v25 does not add curriculum content. It adds a live GNS3 template adapter-capacity preflight check to prevent IOL/IOU serial-to-Ethernet link failures caused by templates with too few Ethernet adapters.


### v28 — Multicast / PIM / IGMP

Added:

```text
multicast_enterprise_lab
multicast_enterprise_lab_iosv
```

Added unique lab concepts:

```text
Multicast routing disabled
PIM missing on transit link
Receiver LAN missing PIM
Wrong static RP address
IGMP join uses wrong group
Source LAN missing PIM
Multicast boundary blocks group
Multicast RPF path wrong
RP loopback not PIM enabled
Remote receiver LAN missing IGMP join
```

Operational fixes:

```text
Console host 0.0.0.0 now resolves to the host from --server for telnet config push.
GUI opens larger by default and saves/restores usable window geometry.
```

Current catalog after v28:

```text
Templates: 11
Topologies: 29
Unique lab concepts: 107
Scenario entries: 211
Legacy/fallback entries: 104
CCNA unique lab concepts: 24
ENCOR unique lab concepts: 107
ENARSI unique lab concepts: 26
Multicast unique lab concepts: 10
```

## 0.9.0 template metadata refresh note

0.9.0 does not add curriculum content. It refreshes the compact catalog template metadata from the latest GNS3 `/v2/templates` export, including the corrected IOL2 template ID and adapter counts.


## Versioning note

The old `vNN` release numbering is retired. Historical `v29` corresponds to `0.9.0`. Future content waves increment the minor version; bugfix-only releases increment the patch version.

### 0.10.0 — Access edge services/security

Added:

```text
access_edge_services_lab
access_edge_services_lab_iosv
```

Added unique lab concepts:

```text
DHCP snooping uplink not trusted
DHCP snooping VLAN missing
DAI trust missing on uplink
Port security maximum too low
Port security violation mode shutdown
BPDU Guard missing on access port
Storm control missing
Errdisable recovery missing
HSRP tracks wrong interface
HSRP decrement too low
```

Current catalog after 0.10.0:

```text
Templates: 14
Topologies: 31
Unique lab concepts: 117
Scenario entries: 231
Legacy/fallback entries: 114
CCNA unique lab concepts: 28
ENCOR unique lab concepts: 117
ENARSI unique lab concepts: 26
Security unique lab concepts: 24
Infrastructure unique lab concepts: 56
```

### 0.12.0 — Advanced routing depth

Added:

```text
advanced_routing_lab
advanced_routing_lab_iosv
```

Added unique lab concepts:

```text
Redistribution missing subnets
Redistribution route map denies routes
Prefix list too specific
OSPF summary mask wrong
OSPF default originate missing
BGP missing OSPF redistribution
BGP network mask wrong
Floating static administrative distance wrong
OSPF distribute list blocks route install
OSPF external metric type wrong
```

Current catalog after 0.12.0:

```text
Templates: 14
Topologies: 33
Unique lab concepts: 127
Scenario entries: 251
Legacy/fallback entries: 124
CCNA unique lab concepts: 28
ENCOR unique lab concepts: 127
ENARSI unique lab concepts: 36
Infrastructure unique lab concepts: 66
```

### 0.13.0 — Security policy depth

Added:

```text
security_policy_depth_lab
security_policy_depth_lab_iosv
```

Added unique lab concepts:

```text
ASAv NAT rule shadowed by broad dynamic NAT
ASAv twice NAT destination object wrong
ASAv outside ACL uses real instead of mapped IP
ASAv access group on wrong interface
ASAv ICMP inspection missing
ASAv SSH management allowed on wrong interface
IOS ACL broad permit shadows policy
IOS strict uRPF breaks asymmetric path
IOS VTY ACL too broad
IOS ACL missing explicit deny log
```

Current catalog after 0.13.0:

```text
Templates: 14
Topologies: 35
Unique lab concepts: 137
Scenario entries: 271
Legacy/fallback entries: 134
CCNA unique lab concepts: 30
ENCOR unique lab concepts: 137
ENARSI unique lab concepts: 36
Security unique lab concepts: 34
ASAv unique lab concepts: 12
```

### 0.14.0 — Automation and assurance workflow depth

Added:

```text
automation_assurance_workflow_lab
automation_assurance_workflow_lab_iosv
```

Added unique lab concepts:

```text
Automation inventory script uses wrong JSON key
Mock API response contains invalid JSON
Down-interface parser logic wrong
Event correlator severity case mismatch
RESTCONF workflow HTTP server disabled
NETCONF blocked by VTY transport
Syslog severity too restrictive for workflow
SNMP community mismatch in workflow
NetFlow summary uses wrong field name
Syslog correlation uses wrong device
```

Current catalog after 0.14.0:

```text
Templates: 14
Topologies: 37
Unique lab concepts: 147
Scenario entries: 291
Legacy/fallback entries: 144
CCNA unique lab concepts: 30
ENCOR unique lab concepts: 147
ENARSI unique lab concepts: 36
Automation unique lab concepts: 17
Network Assurance unique lab concepts: 16
```

### 0.15.0 — Skill checks

Added:

```text
skill-checks study plan
skillcheck_enterprise_wan_capstone
```

Added unique skill-check concepts:

```text
CCNA access edge basic skill check
ENCOR campus routing/services skill check
ENARSI advanced routing skill check
ENCOR enterprise WAN capstone skill check
```

Current catalog after 0.15.0:

```text
Templates: 14
Topologies: 38
Unique lab concepts: 151
Scenario entries: 298
Legacy/fallback entries: 147
CCNA unique lab concepts: 31
ENCOR unique lab concepts: 151
ENARSI unique lab concepts: 38
Skill Check unique lab concepts: 4
```

### 0.16.0 — Endpoint auto-configuration and output polish

Added functional polish:

```text
VPCS endpoint auto-configuration
Endpoint push CLI flags
GUI endpoint push toggle
Skill-check output folder cleanup
1.0.0 scope document
```

No new lab concepts were added.

Current catalog after 0.16.0:

```text
Templates: 14
Topologies: 38
Unique lab concepts: 151
Scenario entries: 298
Legacy/fallback entries: 147
CCNA unique lab concepts: 31
ENCOR unique lab concepts: 151
ENARSI unique lab concepts: 38
```

### 0.17.0 — Curriculum QA

Added functional/curriculum QA:

```text
Scenario hints
Expected results
Structured answer_key objects
Skill-check grading criteria
--qa-report command
Generated grading_criteria.md
Curriculum QA documentation
```

No new lab concepts were added.

QA report:

```text
Scenario entries: 298
Unique concepts: 151
Issues: 0
Errors: 0
Warnings: 0
```

Current catalog after 0.17.0:

```text
Templates: 14
Topologies: 38
Unique lab concepts: 151
Scenario entries: 298
Legacy/fallback entries: 147
CCNA unique lab concepts: 31
ENCOR unique lab concepts: 151
ENARSI unique lab concepts: 38
```

### 0.18.0 — ENCOR skill-check expansion

Added:

```text
encor-skill-checks study plan
skillcheck_encor_eigrp_lab
skillcheck_encor_eigrp_lab_iosv
```

Added unique ENCOR skill-check concepts:

```text
IPv6 foundation skill check
IPv4/IPv6 dual-stack skill check
Advanced OSPF multi-area skill check
EIGRP advanced routing skill check
BGP edge routing skill check
QoS trust boundary skill check
Security edge policy skill check
Automation and assurance workflow skill check
```

Current catalog after 0.18.0:

```text
Templates: 14
Topologies: 40
Unique lab concepts: 159
Scenario entries: 314
Legacy/fallback entries: 155
CCNA unique lab concepts: 31
ENCOR unique lab concepts: 159
ENARSI unique lab concepts: 39
Skill Check unique lab concepts: 12
```

## Remaining recommended waves

```text
v26  Curriculum polish: coverage map, guided mode, prerequisites
```

## Notes

The current catalog is strongest in Infrastructure, especially routing/switching/NAT/VRF/GRE/OSPF/BGP. The v20 wave closes a major IPv6/OSPFv3 gap. The next largest practical gap is Network Assurance.


### 1.2.0 — CCNA foundation content wave

Added 30 unique CCNA foundation labs and two CCNA study plans.

```text
ccna-core
ccna-complete
```

Current catalog after 1.2.0:

```text
Templates: 14
Topologies: 52
Unique lab concepts: 189
Scenario entries: 374
Legacy/fallback entries: 185
CCNA unique lab concepts: 61
ENCOR unique lab concepts: 159
ENARSI unique lab concepts: 39
```
