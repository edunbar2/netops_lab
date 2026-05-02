## Release Scope

- [ ] Patch release branch
- [ ] Minor release branch
- [ ] Major release branch
- [ ] Non-release maintenance branch

Target version:

## Branch and Merge Checklist

- [ ] This work was developed outside `main`.
- [ ] This pull request targets `main`.
- [ ] The branch contains one release scope only.
- [ ] Version metadata, changelog, and release notes are updated if the shipped version changes.

## Testing Checklist

- [ ] Unit tests were added or updated for this implementation.
- [ ] `python tools/validate_catalog.py` passes, or expected warnings are documented below.
- [ ] `python -m unittest discover -s tests` passes.
- [ ] Manual GNS3 verification was completed, or the reason it was not required is documented below.

## Summary

## Verification

## Compatibility Notes
