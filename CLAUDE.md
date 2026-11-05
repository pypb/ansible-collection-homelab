# pypb.homelab

Ansible collection for managing a homelab. It is currently an empty skeleton:
existing roles will be tidied and migrated into `roles/`.

## Content

- Roles: none yet
- Plugins: none yet

Update these lists, and the matching sections of `README.md`, when content is
added.

## Commands

- Build: `ansible-galaxy collection build`
- Install dependencies: `uv sync`
- Lint: `yamllint .`, `ansible-lint` and `ruff check .`
- Sanity tests: `ansible-test sanity --docker default`
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
- When adding a role, also add its molecule tests and an integration or molecule
  job to `.github/workflows/ci.yml`.
