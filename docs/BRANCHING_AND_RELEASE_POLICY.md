# Branching and Release Policy

NetOps Labs uses strict `major.minor.patch` versioning and develops every release on an isolated branch.

## Branch Rules

- Do not commit directly to `main`.
- Patch work must be developed on its own patch branch.
- Minor release work must be developed on its own minor release branch.
- Major release work must be developed on its own major release branch.
- Merge changes to `main` only through a reviewed GitHub pull request or merge request.
- Keep one release scope per branch. Do not mix patch stabilization work with unrelated minor or major features.

Recommended branch names:

- `patch/v4.0.1-short-topic`
- `minor/v4.1.0-short-topic`
- `major/v5.0.0-short-topic`

Assistant-generated branches may use the local `codex/` prefix when the branch name still clearly identifies the target release and purpose.

## Testing Rules

- Every implementation must add or update unit tests for the behavior it changes.
- Bug fixes should include a regression test when the behavior can be isolated without a live GNS3 server.
- GNS3 API behavior should be tested with mocks or fakes unless the test is explicitly an integration test.
- Pull requests must include the exact test command and result.
- Release branches should not be merged until unit tests and any relevant manual verification have passed.

## Merge Rules

- `main` is the release integration branch.
- `main` should only receive changes through pull requests or merge requests.
- A release PR should identify whether it is a patch, minor, or major release.
- A release PR should list user-visible changes, compatibility risks, and verification performed.
- Version metadata, changelog entries, and release notes must be updated when a branch changes the shipped release version.
