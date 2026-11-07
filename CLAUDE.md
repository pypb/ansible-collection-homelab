# pypb.homelab

Ansible collection for managing a homelab. Existing roles are being tidied and
migrated into `roles/`.

## Content

- Roles:
  - `smtp_client`: sets up msmtp as the sendmail and SMTP client of a server, sending mail through a relay
  - `restic_backup`: installs and configures restic and resticprofile
  - `restic_server_users`: manages logins on a containerised rest-server
- Playbooks:
  - `restic_backup`: combines both roles
- Plugins: none yet

Update these lists, and the matching sections of `README.md`, when content is
added.

## Commands

- Build: `ansible-galaxy collection build`
- Install dependencies: `uv sync`
- Lint: `yamllint .`, `ansible-lint` and `ruff check .`
- Sanity tests: `ansible-test sanity --docker default`
- Molecule: run `molecule test --scenario-name <name>` from `extensions/`, with
  `ANSIBLE_COLLECTIONS_PATH` covering this collection and `community.docker`.
  With Podman, also start the API socket and set `DOCKER_HOST`
- Changelog: add a fragment to `changelogs/fragments/`, then run
  `antsibull-changelog release` when releasing

Python dependencies are declared in `pyproject.toml`. Its `version` is separate
from the collection version in `galaxy.yml`, which is the one that matters for
releases.

## Conventions

- Follow the Red Hat CoP automation good practices:
  https://github.com/redhat-cop/automation-good-practices
- Role names are snake_case. Each role has `meta/argument_specs.yml`.
- Document collection-wide variables in `README.md`, since they are referenced
  from role defaults rather than declared explicitly.
- When adding a role, also add a scenario in `extensions/molecule/` and list it in
  the molecule job in `.github/workflows/ci.yml`.
- This repo is public. Keep homelab-specific hostnames and values out of it, and
  copy roles in as clean files rather than importing their git history.
