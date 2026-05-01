# Template Baseline 1.4.2

This document records the current GNS3 template baseline used by the bundled catalog.

The values are based on the current `/v2/templates` API output from the working GNS3 environment.

## Important changes in 1.4.2

```text
IOL2 ethernet_adapters increased from 4 to 8.
RHEL9 template ID updated.
RHEL9 requires QEMU additional option: -cpu host.
RHEL9 endpoint login defaults documented as cloud-user / redhat.
```

The RHEL9 `-cpu host` setting is required because the RHEL 9.7 KVM guest image expects an x86-64-v2-capable CPU. Without this option, QEMU may expose an older generic CPU and RHEL userspace can fail during boot.

## Required/recommended templates

| Catalog key | GNS3 template name | Template type | Template ID | Adapter count | Notes |
|---|---|---:|---|---:|---|
| `iol2` | IOL2 | iou | `5b3b5780-0b02-4ed4-a8ac-ad5cd269f497` | 8 Ethernet | Preferred L2 switch template. |
| `iol3` | IOL3 | iou | `4a661bb0-e23d-453c-ae5e-83aa0e992ad4` | 8 Ethernet / 2 serial | Preferred router template. |
| `iosvl2` | Cisco IOSvL2 15.2.1 | qemu | `059a700f-8939-42f3-97b3-2fcd2c97060a` | 16 | Legacy/fallback L2 switch. |
| `iosv` | Cisco IOSv 15.8(3)M2 | qemu | `b8e407e5-e4e3-4757-8b32-84e2b42ad21d` | 4 | Legacy/fallback router. |
| `asav` | Cisco ASAv | qemu | `321558eb-162a-4162-acd3-1149cf5186c5` | 8 | Security/firewall labs. |
| `cat8000v` | 8000v | qemu | `31c2e3a1-8113-4dc3-b0a3-eba35a8acf74` | 8 | IOS-XE edge/router labs. |
| `csr1000v` | CSR1000v | qemu | `8daa091e-3f25-4698-92c2-35e40097033c` | 8 | IOS-XE router labs. |
| `nxosv9000` | Cisco NX-OSv 9000 9300v 10.1.1 | qemu | `e0245847-8bd8-44d3-a284-9dfc701a6c3f` | 10 | NX-OS/vPC labs. |
| `alpine` | Alpine Linux | docker | `2790a9f9-ec0a-45d8-ac69-5f7fac4b696e` | 1 | Lightweight Linux endpoint. |
| `rhel9` | RHEL9 | qemu | `379da886-e7bb-4152-96c3-310d0607db8e` | 1 | RHEL endpoint; requires `-cpu host`. |
| `vpcs` | VPCS | vpcs | `19021f99-e36f-394d-b4a1-8aaa902ab9cc` | built-in | Lightweight endpoint. |
| `cloud` | Cloud | cloud | `39e257dc-8412-3174-b6b3-0ee3ed6a43e9` | built-in | Optional. |
| `nat` | NAT | nat | `df8f4ea9-33b7-3e96-86a2-c39bc9bb649c` | built-in | Optional. |
| `ethernet_switch` | Ethernet switch | ethernet_switch | `1966b864-93e7-32d5-965f-001384eec461` | built-in | Optional/simple switching. |

## RHEL9 template details

Recommended RHEL9 template settings:

```text
Template name:       RHEL9
Template ID:         379da886-e7bb-4152-96c3-310d0607db8e
Image:               rhel-9.7-x86_64-kvm.qcow2
Cloud-init ISO:      rhel-cloud-init.iso
RAM:                 4096 MB
vCPUs:               2
NIC adapter type:    virtio-net-pci
Disk interface:      virtio
Console type:        telnet
Additional options:  -cpu host
Username:            cloud-user
Password:            redhat
```

CLI example for RHEL9 endpoint push:

```bash
python3 ./gns3_ccnp_lab_generator.py \
  --server http://gns3.dunbar.home \
  --scenario skill_encor_eigrp_advanced \
  --host-type rhel9 \
  --push-config \
  --push-endpoints \
  --linux-endpoint-username cloud-user \
  --linux-endpoint-password redhat
```

## IOL2 template details

Recommended IOL2 settings:

```text
Template name:       IOL2
Template ID:         5b3b5780-0b02-4ed4-a8ac-ad5cd269f497
Ethernet adapters:   8
Serial adapters:     0
RAM:                 1024 MB
NVRAM:               256 KB
Console type:        telnet
```

The 8-adapter IOL2 template is preferred for generated switching topologies. Smaller 4-adapter templates may still work for basic labs, but larger campus/switching scenarios can fail preflight checks.

## Validation guidance

Use the GUI or CLI preflight checks before creating large projects. If a template has too few adapters, the generator should stop before project creation and report the affected template and required adapter count.
