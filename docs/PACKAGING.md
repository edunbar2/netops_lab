# Packaging NetOps Labs

NetOps Labs can be packaged by GitHub Actions for Windows and Linux, with a source zip available for macOS and manual installs.

## GitHub Actions

The `Package Release` workflow builds:

- Windows portable zip and Inno Setup installer.
- Linux portable zip, Debian package, and RPM package.
- Source zip for users who prefer the manual install path.

The workflow runs on pull requests for package validation, manually from **Actions > Package Release > Run workflow**, and automatically on semantic version tags such as `v4.0.1`.

On tag builds, the workflow uploads all artifacts to the GitHub release as release assets. Every run also stores the generated packages as GitHub Actions artifacts.

## Local Build

Install runtime and build dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install -r packaging/requirements-build.txt
```

Build the package for the current OS:

```bash
python tools/build_packages.py
```

Build only the source zip:

```bash
python tools/build_packages.py --source-only
```

Artifacts are written to `dist/release/`.

## Installer Notes

- Windows uses Inno Setup. Local Windows builds need Inno Setup 6 available on `PATH` or in the normal Program Files location.
- macOS native installer packaging is intentionally disabled. macOS users should use the source zip unless Apple Developer ID signing and notarization are added later.
- Linux builds `.deb` and `.rpm` packages that install to `/opt/netops-labs` and add `/usr/local/bin/netops-labs`.
- Portable zips are always produced so users can still choose a manual install or inspection path.

Local Linux RPM builds need `rpmbuild` available. On Ubuntu CI this is provided by the `rpm` package.

## Runtime Layout

Packaged builds include two PyInstaller executables:

- `NetOps Labs` or `netops-labs`: the Qt GUI.
- `netops-lab-generator`: the CLI generator used by the GUI for preflight, generation, blank topology, and QA commands.

The GUI bundle carries the catalog, templates, docs, and Qt runtime. The generator bundle is intentionally kept lean and does not bundle the Qt runtime or duplicate release data.

The packaged GUI stores user settings and generated labs in a per-user data directory instead of writing inside the installed app directory.
