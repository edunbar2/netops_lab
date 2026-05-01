# Template API Conversion Guide

This guide explains how to convert a GNS3 `/v2/templates` API response into the catalog template metadata used by this project.

## Source data

Export templates from GNS3:

```bash
curl http://<gns3-server>/v2/templates
```

or in PowerShell:

```powershell
Invoke-RestMethod http://<gns3-server>/v2/templates | ConvertTo-Json -Depth 20
```

## Catalog target

The generator expects a `templates` object inside:

```text
catalogs/ccnp_encor_lab_catalog.json
```

Each catalog key is a stable logical name used by topologies and scenarios:

```text
iol2
iol3
iosv
iosvl2
asav
cat8000v
csr1000v
nxosv9000
alpine
rhel9
vpcs
cloud
nat
ethernet_switch
```

## Mapping rules

For QEMU and Docker templates, map:

```text
name
template_id
template_type
category
compute_id
adapters
console_type
port_name_format
first_port_name
```

For IOU/IOL templates, map:

```text
name
template_id
template_type
category
compute_id
ethernet_adapters
serial_adapters
console_type
ram
nvram
```

For built-in VPCS/Cloud/NAT/Ethernet switch templates, map:

```text
name
template_id
template_type
category
compute_id
```

## Example: IOL2

Source API fields:

```json
{
  "name": "IOL2",
  "template_id": "5b3b5780-0b02-4ed4-a8ac-ad5cd269f497",
  "template_type": "iou",
  "ethernet_adapters": 8,
  "serial_adapters": 0,
  "console_type": "telnet"
}
```

Catalog entry:

```json
"iol2": {
  "name": "IOL2",
  "template_id": "5b3b5780-0b02-4ed4-a8ac-ad5cd269f497",
  "template_type": "iou",
  "category": "switch",
  "compute_id": "local",
  "role": "default_l2_switch",
  "ethernet_adapters": 8,
  "serial_adapters": 0,
  "console_type": "telnet"
}
```

## Example: RHEL9

Source API fields:

```json
{
  "name": "RHEL9",
  "template_id": "379da886-e7bb-4152-96c3-310d0607db8e",
  "template_type": "qemu",
  "adapter_type": "virtio-net-pci",
  "adapters": 1,
  "hda_disk_interface": "virtio",
  "ram": 4096,
  "cpus": 2,
  "options": "-cpu host"
}
```

Catalog entry:

```json
"rhel9": {
  "name": "RHEL9",
  "template_id": "379da886-e7bb-4152-96c3-310d0607db8e",
  "template_type": "qemu",
  "category": "guest",
  "compute_id": "local",
  "role": "linux_host",
  "adapters": 1,
  "console_type": "telnet",
  "port_name_format": "Ethernet{0}",
  "adapter_type": "virtio-net-pci",
  "hda_disk_interface": "virtio",
  "ram": 4096,
  "cpus": 2,
  "options": "-cpu host",
  "default_username": "cloud-user",
  "default_password": "redhat"
}
```

## Important notes

- Template names can vary across environments, so the catalog uses logical keys.
- Template IDs are environment-specific; update them when moving to a different GNS3 server.
- Adapter counts are important. Preflight checks use them to prevent invalid topologies.
- RHEL9 should keep `options: -cpu host` when using the RHEL 9.7 KVM guest image.
