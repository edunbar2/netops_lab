# Guided Study Plans

These plans are stored in the catalog under `study_plans` and can be listed from the CLI.

```bash
./gns3_ccnp_lab_generator.py --list-study-plan encor-core
./gns3_ccnp_lab_generator.py --list-study-plan encor-complete
```

## ENCOR Core Practical Path

A concise path through representative labs for the main non-controller ENCOR technologies.

### 1. Campus Layer 2 fundamentals

**Objective:** Validate VLANs, trunks, STP, and EtherChannel troubleshooting.

Labs:

- `l2_native_vlan_mismatch` — Native VLAN Mismatch
- `svc_bpduguard_missing_on_access` — BPDU Guard Missing on Access Port

### 2. First-hop redundancy and access edge services

**Objective:** Troubleshoot HSRP behavior and common access-edge protection features.

Labs:

- `svc_hsrp_track_wrong_interface` — HSRP Tracks Wrong Interface
- `svc_dhcp_snooping_untrusted_uplink` — DHCP Snooping Uplink Not Trusted
- `svc_port_security_maximum_too_low` — Port Security Maximum Too Low

### 3. OSPF and IPv6/OSPFv3

**Objective:** Practice OSPFv2, IPv6, and OSPFv3 adjacency/path issues.

Labs:

- `l3_ospf_area_mismatch` — OSPF Area Mismatch
- `l3_ospf_cost_suboptimal` — OSPF Suboptimal Path
- `l3_ospf_auth_mismatch` — OSPF Authentication Mismatch
- `l3_ipv6_unicast_routing_missing` — IPv6 Unicast Routing Missing
- `l3_ospfv3_area_mismatch` — OSPFv3 Area Mismatch
- `l3_ospfv3_router_id_duplicate` — OSPFv3 Duplicate Router ID

### 4. Path control and external reachability

**Objective:** Cover BGP, PBR, NAT, and default-route style troubleshooting.

Labs:

- `bgp_wrong_remote_as` — BGP Wrong Remote AS

### 5. Virtualization and tunneling

**Objective:** Practice VRF-Lite and GRE issues without requiring controllers.

Labs:


### 6. Security and access hardening

**Objective:** Troubleshoot ACLs, AAA, CoPP, ASAv, and edge-security failures.

Labs:

- `sec_acl_sequence_shadowing` — ACL Sequence Shadows Permit
- `sec_aaa_method_list_wrong` — AAA Method List Not Applied to VTY
- `sec_copp_blocks_ospf` — CoPP Blocks OSPF
- `sec_asav_outside_acl_missing_https` — ASAv Outside ACL Missing HTTPS Permit
- `svc_dai_trust_missing_on_uplink` — DAI Trust Missing on Uplink

### 7. Network assurance

**Objective:** Validate monitoring and operational visibility components.

Labs:

- `na_syslog_wrong_host` — Syslog Wrong Host
- `na_snmp_acl_blocks_collector` — SNMP ACL Blocks Collector
- `na_netflow_missing_interface_monitor` — NetFlow Monitor Missing from Interface
- `na_span_wrong_source_interface` — SPAN Wrong Source Interface
- `na_ipsla_wrong_target` — IP SLA Wrong Probe Target
- `na_ntp_wrong_server` — NTP Wrong Server

### 8. QoS and multicast

**Objective:** Troubleshoot QoS policy behavior and multicast forwarding.

Labs:

- `qos_wan_policy_missing` — WAN QoS Policy Missing
- `qos_voice_class_matches_wrong_dscp` — Voice Class Matches Wrong DSCP
- `qos_access_port_trust_boundary_wrong` — Access Port Trust Boundary Wrong
- `mcast_pim_missing_on_transit` — PIM Missing on Transit Link
- `mcast_wrong_rp_address` — Wrong Static RP Address
- `mcast_rpf_path_wrong` — Multicast RPF Path Wrong

### 9. Automation and architecture

**Objective:** Practice automation interpretation and design-level reasoning.

Labs:

- `auto_restconf_disabled` — RESTCONF Disabled
- `auto_json_inventory_invalid` — Invalid JSON Inventory
- `auto_python_parse_show_output_bug` — Python Parser Bug
- `arch_wrong_default_gateway_placement` — Architecture: Wrong Default Gateway Placement
- `arch_wan_path_selection_suboptimal` — Architecture: Suboptimal WAN Path Selection

## ENCOR Complete Domain Sweep

A longer sweep organized by ENCOR domain. Use this after the core path or for comprehensive review.

### 1. Architecture

**Objective:** Review campus, overlay/underlay, gateway placement, and resiliency design decisions.

Labs:

- `arch_single_point_of_failure_access` — Architecture: Access Layer Single Point of Failure
- `arch_wrong_default_gateway_placement` — Architecture: Wrong Default Gateway Placement
- `arch_wan_path_selection_suboptimal` — Architecture: Suboptimal WAN Path Selection
- `arch_underlay_overlay_mapping_error` — Architecture: Underlay/Overlay Mapping Error
- `arch_qos_marking_at_wrong_layer` — Architecture: QoS Marking at Wrong Layer

### 2. Virtualization

**Objective:** Troubleshoot VRF and tunnel-based segmentation/transport labs.

Labs:


### 3. Infrastructure

**Objective:** Review the largest ENCOR domain: L2, routing, IPv6, QoS, multicast, NAT, and FHRP.

Labs:

- `l3_ospf_area_mismatch` — OSPF Area Mismatch
- `l3_ospf_cost_suboptimal` — OSPF Suboptimal Path
- `l3_ipv6_unicast_routing_missing` — IPv6 Unicast Routing Missing
- `bgp_wrong_remote_as` — BGP Wrong Remote AS
- `qos_wan_policy_missing` — WAN QoS Policy Missing
- `mcast_multicast_routing_disabled` — Multicast Routing Disabled

### 4. Network Assurance

**Objective:** Verify syslog, SNMP, NetFlow, SPAN/RSPAN, IP SLA, and NTP visibility.

Labs:

- `na_syslog_wrong_host` — Syslog Wrong Host
- `na_syslog_trap_level_wrong` — Syslog Trap Level Too Restrictive
- `na_snmp_acl_blocks_collector` — SNMP ACL Blocks Collector
- `na_netflow_exporter_wrong_destination` — NetFlow Exporter Wrong Destination
- `na_rspan_vlan_not_remote_span` — RSPAN VLAN Missing Remote-Span
- `na_ipsla_wrong_target` — IP SLA Wrong Probe Target
- `na_ntp_wrong_server` — NTP Wrong Server

### 5. Security

**Objective:** Review device access, ACLs, CoPP, firewall behavior, and access-edge security controls.

Labs:

- `sec_local_user_privilege_low` — Local User Privilege Too Low
- `sec_vty_transport_telnet_enabled` — VTY Allows Telnet
- `sec_acl_sequence_shadowing` — ACL Sequence Shadows Permit
- `sec_copp_blocks_ospf` — CoPP Blocks OSPF
- `sec_asav_static_nat_wrong_object` — ASAv Static NAT Uses Wrong DMZ Host
- `svc_dhcp_snooping_vlan_missing` — DHCP Snooping VLAN Missing
- `svc_port_security_violation_shutdown` — Port Security Violation Mode Shutdown

### 6. Automation

**Objective:** Review JSON, REST/NETCONF/YANG, EEM, and Python parsing tasks.

Labs:

- `auto_restconf_disabled` — RESTCONF Disabled
- `auto_netconf_yang_disabled` — NETCONF/YANG Disabled
- `auto_rest_status_404_wrong_endpoint` — RESTCONF 404 Wrong Endpoint
- `auto_rest_status_401_auth_failure` — RESTCONF 401 Authentication Failure
- `auto_yang_interface_payload_interpret` — YANG Interface Payload Interpretation
- `auto_python_parse_show_output_bug` — Python Parser Bug

