# Environment Readiness

1.6.0 introduces helper scripts to make deployment requirements visible.

## What readiness means

A lab is considered ready when:

```text
Required template keys are mapped.
Template IDs exist for the local GNS3 server.
Template adapter counts are sufficient.
Console type is compatible with config push where applicable.
Endpoint host type exists.
Known image-specific requirements are satisfied.
```

## Current known checks

```text
Missing template mappings
Insufficient adapters
Non-telnet console warnings
RHEL9 missing -cpu host warning
```

## Future GUI integration

The 1.6.0 helper scripts are the foundation for a future GUI Environment tab and Ready/Warning/Missing indicators in the lab browser.
