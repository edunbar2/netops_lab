# Linux Endpoint Auto-Push

1.1.0 adds automatic Linux endpoint setup for supported Alpine and RHEL9 endpoint templates.

## Supported host types

```text
alpine
rhel9
```

VPCS endpoint auto-push is still supported.

## How it works

The generator renders the endpoint setup template, opens the node console, attempts to reach a Linux shell, and pastes the generated setup commands.

The same setup content is always written to:

```text
endpoint_setup/
```

Push logs are written to:

```text
endpoint_push_logs/
```

## CLI examples

Alpine:

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

RHEL9:

```bash
python3 ./gns3_ccnp_lab_generator.py \
  --server http://gns3.example.local \
  --scenario skill_encor_eigrp_advanced \
  --host-type rhel9 \
  --push-config \
  --push-endpoints \
  --linux-endpoint-username root \
  --linux-endpoint-password '<password-if-required>'
```

## GUI usage

The GUI includes:

```text
Push supported endpoints
Linux endpoint user
Linux endpoint password
```

Enable endpoint push, select `alpine` or `rhel9` as the host type, and provide credentials if the image requires them.

## Verification commands on Linux endpoints

After endpoint push, open the endpoint console and run:

```bash
ip addr show eth0
ip route
ping -c 4 <gateway>
```

For example:

```bash
ip addr show eth0
ip route
ping -c 4 10.180.10.1
```

## Troubleshooting

If endpoint push does not complete:

1. Open the endpoint console and confirm it reaches a login prompt or shell.
2. Confirm the username and password.
3. Check `endpoint_push_logs/<node>_endpoint_push.log`.
4. Apply the generated file from `endpoint_setup/` manually if the image uses a non-standard login workflow.

Linux endpoint console behavior can vary by image. The generated setup files remain the source of truth even if automatic push is not successful.
