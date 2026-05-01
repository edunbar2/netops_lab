# Upgrade Notice for 1.6.0

1.6.0 starts the deployment/readiness overhaul and changes how environment-specific settings should be stored.

## What changed

Previous packages included environment-specific defaults such as a specific GNS3 server URL and a bundled template baseline from one working environment.

Starting in 1.6.0:

```text
No personal GNS3 server URL is used as the default.
User-specific settings belong in config/app_config.local.json.
User-specific template mappings belong in config/template_overrides.local.json.
Example files are provided and should be copied before editing.
```

## Required action after upgrading

Create a local app config:

```bash
cp config/app_config.example.json config/app_config.local.json
```

Edit:

```json
"gns3_server": "http://your-gns3-server"
```

Optional template overrides:

```bash
cp config/template_overrides.example.json config/template_overrides.local.json
```

Edit the template IDs/settings to match your GNS3 server.

## Fresh setup recommended

A fresh setup is recommended for 1.6.0 because configuration and template mappings are being separated from bundled catalog content.

Do not edit the example config files directly if you want your local settings to survive future package updates.
