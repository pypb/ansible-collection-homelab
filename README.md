# pypb.homelab

Ansible roles and plugins for managing my homelab.

## Requirements

- ansible-core 2.21 or newer
- [`community.docker`](https://docs.ansible.com/ansible/latest/collections/community/docker/)
  5.0.0 or newer, which is installed automatically with this collection

## Installation

The collection is not published on Ansible Galaxy. Install it from Git:

```shell
ansible-galaxy collection install git+https://github.com/pypb/ansible-collection-homelab.git
```

## Content

### Roles

| Role | Description | Platforms |
|---|---|---|
| [`pypb.homelab.smtp_client`](roles/smtp_client/README.md) | Sets up msmtp as the sendmail and SMTP client of a server, with mail aliases | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.restic_backup`](roles/restic_backup/README.md) | Installs and configures restic and resticprofile for scheduled backups | Debian 13, Ubuntu 24.04 and 26.04, Raspberry Pi OS (trixie-based) |
| [`pypb.homelab.restic_server_users`](roles/restic_server_users/README.md) | Manages user logins on a containerised rest-server | Any Linux |

### Playbooks

| Playbook | Description |
|---|---|
| [`pypb.homelab.restic_backup`](playbooks/restic_backup.yml) | Creates a rest-server user for each host with `restic_backup_enable` set, and configures backups with the generated credentials |

```shell
ansible-playbook pypb.homelab.restic_backup -e restic_backup_hosts=backup_clients
```

The playbook targets the hosts in `restic_backup_hosts`, which defaults to `all`.
It only acts on hosts where `restic_backup_enable` is true.

### Plugins

None yet.

### Collection-wide variables

These are not set by any role, but roles use them as defaults when they are
defined in your inventory.

| Variable | Used by | Description |
|---|---|---|
| `restic_server_hostname` | `restic_server_users` | Host running the rest-server container |
| `restic_server_container` | `restic_server_users` | Name of the rest-server container |

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

cd extensions
molecule test --scenario-name restic_server_users
molecule test --scenario-name restic_backup
molecule test --scenario-name smtp_client
```

The molecule scenarios need Docker, or Podman with its API socket enabled and
`DOCKER_HOST` pointing to it. They also need this collection and `community.docker`
on `ANSIBLE_COLLECTIONS_PATH`.

Describe each change in a fragment under `changelogs/fragments/`, then generate
the changelog at release time with `antsibull-changelog release`.

## License

Apache License 2.0. See [LICENSE](LICENSE) for the full text.
