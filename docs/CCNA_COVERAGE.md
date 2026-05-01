# CCNA Coverage

1.3.0 completes the second CCNA-focused content wave. The CCNA track now includes starter topologies, `ccna-core`, `ccna-complete`, and a larger set of foundational troubleshooting and interpretation labs.

## Exam-tag isolation

All scenarios whose IDs begin with `ccna_` are tagged as:

```json
"exam_blueprints": ["CCNA"],
"primary_exam": "CCNA"
```

These CCNA foundation labs are intentionally not added to ENCOR. ENCOR remains focused on professional-level content, while CCNA receives its own foundation track.

## Study plans

```bash
python3 ./gns3_ccnp_lab_generator.py --list-study-plan ccna-core
python3 ./gns3_ccnp_lab_generator.py --list-study-plan ccna-complete
```

Both plans are available in the GUI study-plan selector.

## CCNA starter topologies

```text
ccna_two_router_lan
ccna_small_switched_lan
ccna_router_on_a_stick
ccna_small_ospf
ccna_services_edge
ccna_automation_workstation
ccna_wireless_security_interpretation
```

Each topology has a matching legacy variant where device type compatibility is relevant.

## CCNA unique concept counts after 1.3.0

```text
CCNA unique lab concepts: 85
CCNA-prefixed unique lab concepts: 55
```

By CCNA domain:

```text
Automation and Programmability: 8
IP Connectivity:                8
IP Services:                    11
Network Access:                 12
Network Fundamentals:           6
Security Fundamentals:          9
```

## 1.2.0 CCNA labs

### Network Fundamentals

```text
ccna_nf_interface_shutdown
ccna_nf_speed_duplex_mismatch
ccna_nf_wrong_default_gateway
ccna_nf_wrong_subnet_mask
ccna_nf_ipv6_wrong_prefix
ccna_nf_mac_table_learning
```

### Network Access

```text
ccna_na_access_vlan_wrong
ccna_na_voice_vlan_missing
ccna_na_trunk_mode_missing
ccna_na_native_vlan_easy
ccna_na_lacp_basic_mismatch
ccna_na_portfast_missing
```

### IP Connectivity

```text
ccna_ip_static_route_missing
ccna_ip_static_route_wrong_next_hop
ccna_ip_default_route_missing
ccna_ip_floating_static_ad_wrong
ccna_ip_ipv6_static_route_missing
ccna_ip_ospf_network_missing
ccna_ip_ospf_router_id_duplicate
ccna_ip_ospf_passive_wrong_link
```

### IP Services

```text
ccna_svc_nat_inside_outside_swapped
ccna_svc_pat_overload_missing
ccna_svc_ntp_wrong_server
ccna_svc_syslog_wrong_host
ccna_svc_snmp_community_mismatch
```

### Security Fundamentals

```text
ccna_sec_local_user_missing
ccna_sec_vty_telnet_enabled
ccna_sec_standard_acl_wrong_source
```

### Automation and Programmability

```text
ccna_auto_json_invalid
ccna_auto_rest_wrong_http_verb
```

## 1.3.0 CCNA labs

### Network Access

```text
ccna_na_cdp_neighbor_discovery
ccna_na_lldp_neighbor_discovery
ccna_na_intervlan_subinterface_missing
ccna_na_bpduguard_errdisable_easy
ccna_wifi_wpa2_psk_mismatch
ccna_wifi_guest_isolation_requirement
```

### IP Services

```text
ccna_svc_dhcp_pool_wrong_gateway
ccna_svc_dhcp_excluded_missing
ccna_svc_ssh_domain_name_missing
ccna_svc_ssh_transport_missing
ccna_svc_syslog_severity_too_high
ccna_svc_nat_acl_wrong_source
```

### Security Fundamentals

```text
ccna_sec_enable_secret_missing
ccna_sec_extended_acl_wrong_direction_easy
ccna_sec_port_security_shutdown_easy
ccna_sec_dhcp_snooping_trust_easy
ccna_sec_dai_without_snooping
ccna_sec_unused_ports_not_shutdown
```

### Automation and Programmability

```text
ccna_auto_crud_mapping
ccna_auto_api_auth_type
ccna_auto_ansible_inventory_basic
ccna_auto_controller_roles
ccna_auto_iac_config_drift
ccna_auto_ai_ml_ops_interpretation
```

## Notes

Some older non-`ccna_` labs remain tagged for both CCNA and ENCOR where the same concept is reasonable at both levels, such as VLANs, OSPF basics, ACL basics, and DHCP Snooping. The dedicated `ccna_*` foundation labs are separated so they do not bloat ENCOR counts or ENCOR study plans.
