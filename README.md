# pypb.homelab

Ansible roles and plugins for managing my homelab.

## Requirements

- ansible-core 2.21 or newer
- [`ansible.posix`](https://docs.ansible.com/ansible/latest/collections/ansible/posix/)
  2.0.0 or newer, [`community.docker`](https://docs.ansible.com/ansible/latest/collections/community/docker/)
  5.0.0 or newer, [`community.crypto`](https://docs.ansible.com/ansible/latest/collections/community/crypto/)
  3.1.1 or newer and [`community.general`](https://docs.ansible.com/ansible/latest/collections/community/general/)
  9.0.0 or newer, which are installed automatically with this collection

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
| [`pypb.homelab.acme_certificates`](roles/acme_certificates/README.md) | Trusts private CAs, and requests certificates from an ACME server with DNS-01 and installs them anywhere, including Unifi keystores | Debian 12 and 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.ubuntu_k3s_node`](roles/ubuntu_k3s_node/README.md) | Strips Ubuntu down to a minimal k3s node, and sets up sysctl, NFS, mount watchdogs, Cilium prerequisites, stopping pods at shutdown and the k3s server's PSA and audit files | Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.iscsi_initiator`](roles/iscsi_initiator/README.md) | Sets up open-iscsi and logs in to targets now and at boot, with a disk timeout for chosen vendors and optional multipathd | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.server_baseline`](roles/server_baseline/README.md) | Basic server configuration: packages, the Ubuntu mirror, the host's domain, a static resolv.conf, sysctl, time zone, sudo, motd and banners, and the kernel consoles and GRUB menu | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.unattended_upgrades`](roles/unattended_upgrades/README.md) | Installs upgrades automatically with unattended-upgrades, with reports, automatic reboots and any other apt settings | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.ocfs2`](roles/ocfs2/README.md) | Sets up the OCFS2 cluster file system with the o2cb cluster stack, its kernel module, fencing and the mounts | Debian 13, Ubuntu 24.04 and 26.04 |

### Playbooks

| Playbook | Description |
|---|---|
| [`pypb.homelab.restic_backup`](playbooks/restic_backup.yml) | Creates a rest-server user for each host with `restic_backup_enable` set, and configures backups with the generated credentials |

```shell
ansible-playbook pypb.homelab.restic_backup -e restic_backup_hosts=backup_clients
```

The playbook targets the hosts in `restic_backup_hosts`, which defaults to `all`.
It only acts on hosts where `restic_backup_enable` is true.

| Playbook | Description |
|---|---|
| [`pypb.homelab.ubuntu_k3s_node`](playbooks/ubuntu_k3s_node.yml) | Runs the `ubuntu_k3s_node` role, and before it the `iscsi_initiator` and `ocfs2` roles when `ubuntu_k3s_node_iscsi` and `ubuntu_k3s_node_ocfs2` are true, on one node at a time, optionally reboots it after stopping k3s and unmounting OCFS2, and waits for servers that run k3s to be Ready before the next node. It doesn't install k3s: use a role such as `xanmanning.k3s` after it |

```shell
ansible-playbook pypb.homelab.ubuntu_k3s_node -e ubuntu_k3s_node_hosts=k3s_nodes --limit node1
```

The playbook targets the hosts in `ubuntu_k3s_node_hosts`, which defaults to the
`k3s_nodes` group rather than `all`, since the role purges packages. See [Rolling out](roles/ubuntu_k3s_node/README.md#rolling-out).

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
molecule test --scenario-name acme_certificates
molecule test --scenario-name ubuntu_k3s_node
molecule test --scenario-name ocfs2
molecule test --scenario-name iscsi_initiator
molecule test --scenario-name server_baseline
molecule test --scenario-name unattended_upgrades
```

The molecule scenarios need Docker, or Podman with its API socket enabled and
`DOCKER_HOST` pointing to it, and the `docker` command, which can be Podman's. They also
need this collection, `ansible.posix`, `community.docker`, `community.crypto` and
`community.general` on `ANSIBLE_COLLECTIONS_PATH`.

Describe each change in a fragment under `changelogs/fragments/`, then generate
the changelog at release time with `antsibull-changelog release`.

## License

Apache License 2.0. See [LICENSE](LICENSE) for the full text.
