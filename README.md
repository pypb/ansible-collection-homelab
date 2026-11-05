# pypb.homelab

Ansible roles and plugins for managing my homelab.

This collection is a skeleton for now. Roles will be added as they are tidied
and migrated.

## Requirements

- ansible-core 2.22 or newer
- Python 3.13 or newer on the control node

## Installation

The collection is not published on Ansible Galaxy. Install it from Git:

```shell
ansible-galaxy collection install git+https://github.com/pypb/homelab.git
```

## Content

### Roles

None yet.

### Plugins

None yet.

### Collection-wide variables

None yet. Roles that share configuration should reference a collection-wide
variable from their `defaults/main.yml`, and that variable should be documented
here.

## Development

Clone the repository to a path ending in `ansible_collections/pypb/homelab`,
which `ansible-test` requires.

```shell
uv sync

yamllint .
ansible-lint
ruff check .
ansible-test sanity --docker default
ansible-galaxy collection build
```

Describe each change in a fragment under `changelogs/fragments/`, then generate
the changelog at release time with `antsibull-changelog release`.

## License

Apache License 2.0. See [LICENSE](LICENSE) for the full text.
