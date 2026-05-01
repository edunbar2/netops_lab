# Converting GNS3 `/v2/templates` API Output into Catalog Template Entries

This file explains how to convert the raw GNS3 templates API response into the `templates` section used by the GNS3 CCNP/CCNA lab generator.

It is written to be usable by a human or by an LLM.

## Goal

The generator catalog needs stable, compact template entries like this:

```json
"templates": {
  "iol3": {
    "name": "IOL3",
    "template_id": "4a661bb0-e23d-453c-ae5e-83aa0e992ad4",
    "template_type": "iou",
    "category": "router",
    "compute_id": "local",
    "role": "default_router"
  }
}
```

The GNS3 `/v2/templates` endpoint returns much larger objects. Only a small subset is required for the generator.

## How to get the raw template export

Linux/macOS:

```bash
curl http://gns3.dunbar.home/v2/templates > gns3-templates.json
```

Windows PowerShell:

```powershell
Invoke-RestMethod http://gns3.dunbar.home/v2/templates |
    ConvertTo-Json -Depth 20 |
    Out-File .\gns3-templates.json -Encoding utf8
```

Change the URL if your GNS3 server is not `http://gns3.dunbar.home`.

## Required fields

Each catalog template entry should contain:

```text
name
template_id
template_type
category
compute_id
```

`compute_id` may be `null` for built-in nodes such as VPCS, NAT, Cloud, or Ethernet switch.

## Recommended optional fields

Add these when useful:

```text
role
create_mode
console_type
notes
optional
```

## Template key naming convention

Use short stable keys. Do not use spaces.

Recommended keys:

```text
iosv
iosvl2
iol3
iol2
csr1000v
cat8000v
asav
nxosv9000
alpine
rhel9
vpcs
nat
cloud
ethernet_switch
```

The key is what topology nodes reference:

```json
"template": "iol3"
```

## Role naming convention

Roles are not required by GNS3, but they help humans and LLMs reason about the catalog.

Recommended roles:

```text
default_router
default_l2_switch
classic_ios_router
classic_ios_l2_l3_switch
iosxe_router
iosxe_edge_router
firewall
nxos_switch
lightweight_host
linux_host
vpcs_host
builtin_nat
builtin_cloud
builtin_switch
```

## Conversion rules

### Rule 1 — Include non-built-in appliance templates

For QEMU, IOU/IOL, Docker, or other actual node images, include a catalog entry.

Good candidates:

```text
template_type: qemu
template_type: iou
template_type: docker
```

### Rule 2 — Include selected built-ins only if the generator needs them

Built-in templates have:

```json
"builtin": true
```

Usually include:

```text
VPCS
NAT
Cloud
Ethernet switch
```

Do not include Frame Relay, ATM, or Hub unless a topology needs them.

### Rule 3 — Preserve exact `template_id`

The `template_id` is the most important field. The generator uses it to create nodes through the GNS3 API.

### Rule 4 — Do not copy unnecessary image/disk fields

The generator does not normally need these in the catalog:

```text
hda_disk_image
hda_disk_interface
ram
cpus
adapter_type
adapters
qemu_path
symbol
usage
```

Those settings live in the GNS3 template itself. The catalog only needs to know which template to instantiate.

### Rule 5 — Use `create_mode: direct_vpcs` only for VPCS if needed

The generator can create VPCS directly without calling `/templates/{template_id}`. If using the direct mode, the entry should look like:

```json
"vpcs": {
  "name": "VPCS",
  "template_id": "19021f99-e36f-394d-b4a1-8aaa902ab9cc",
  "template_type": "vpcs",
  "category": "guest",
  "compute_id": "local",
  "create_mode": "direct_vpcs",
  "role": "vpcs_host"
}
```

If the GNS3 API template-create endpoint works in your environment, `create_mode` can be omitted.

## Example conversion

Raw API object:

```json
{
  "name": "IOL3",
  "template_id": "4a661bb0-e23d-453c-ae5e-83aa0e992ad4",
  "template_type": "iou",
  "category": "router",
  "compute_id": "local",
  "ethernet_adapters": 2,
  "ram": 1024,
  "path": "x86_64_crb_linux-adventerprisek9-ms.iol"
}
```

Catalog entry:

```json
"iol3": {
  "name": "IOL3",
  "template_id": "4a661bb0-e23d-453c-ae5e-83aa0e992ad4",
  "template_type": "iou",
  "category": "router",
  "compute_id": "local",
  "role": "default_router"
}
```

## Recommended LLM prompt

Use this prompt when asking an LLM to convert a new `/v2/templates` export:

```text
You are updating the GNS3 lab generator catalog.

I will provide a raw JSON response from GET /v2/templates.

Create a compact `templates` object for `ccnp_encor_lab_catalog.json`.

Rules:
- Preserve exact template_id values.
- Include useful QEMU, IOU/IOL, Docker, VPCS, NAT, Cloud, and Ethernet switch templates.
- Omit disk/image/RAM/CPU details unless needed as notes.
- Use stable lowercase keys: iosv, iosvl2, iol3, iol2, csr1000v, cat8000v, asav, nxosv9000, alpine, rhel9, vpcs, nat, cloud, ethernet_switch.
- Add a role field using the recommended role names from this guide.
- Mark license-dependent or environment-dependent templates with `"optional": true` only if they are not guaranteed to be available.
- Return valid JSON only.
```

## Validation checklist

After updating `templates`, run:

```bash
./gns3_ccnp_lab_generator.py --list-templates
```

Then create a small project with no auto-config:

```bash
./gns3_ccnp_lab_generator.py \
  --scenario l3_ospf_area_mismatch \
  --no-auto-config
```

If a template ID is wrong, node creation will fail with a GNS3 API error.
