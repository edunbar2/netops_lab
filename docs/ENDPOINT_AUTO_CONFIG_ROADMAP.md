# Endpoint Auto-Configuration

## 1.1.0 status

Automatic endpoint push is supported for:

```text
VPCS
Alpine
RHEL9
```

## VPCS endpoint push

Use VPCS when you want the simplest endpoint auto-push behavior:

```bash
python3 ./gns3_ccnp_lab_generator.py \
  --server http://gns3.example.local \
  --scenario skill_encor_eigrp_advanced \
  --host-type vpcs \
  --push-config \
  --push-endpoints
```

Verify on a VPCS endpoint:

```text
show ip
ping <gateway>
```

## Linux endpoint push

Alpine and RHEL9 endpoint setup is now supported through Linux shell console push.

Example:

```bash
python3 ./gns3_ccnp_lab_generator.py \
  --server http://gns3.example.local \
  --scenario skill_encor_eigrp_advanced \
  --host-type alpine \
  --push-config \
  --push-endpoints \
  --linux-endpoint-username root \
  --linux-endpoint-password ''
```

RHEL9 images may require a configured root password or another privileged login depending on how the template was built.

## Generated files

Every generated lab includes:

```text
endpoint_setup/
endpoint_push_logs/   created when endpoint push runs
```

## Supported and unsupported behavior

Supported in 1.1.0:

```text
VPCS endpoint IP/gateway push
Alpine shell-based setup push
RHEL9 shell-based setup push
```

Not included in 1.1.0:

```text
Automated sudo escalation workflows
SSH-based endpoint push
Cloud-init injection
Formal endpoint health grading
```

## Operational guidance

Automatic Linux endpoint push is best-effort because console login behavior varies by image. The generated setup files in `endpoint_setup/` are always available for manual application.
