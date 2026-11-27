# pypb.homelab

Ansible roles and plugins for managing my homelab.

## Requirements

- ansible-core 2.21 or newer
- [`ansible.posix`](https://docs.ansible.com/ansible/latest/collections/ansible/posix/)
  2.0.0 or newer, [`community.docker`](https://docs.ansible.com/ansible/latest/collections/community/docker/)
  5.0.0 or newer, [`community.crypto`](https://docs.ansible.com/ansible/latest/collections/community/crypto/)
  3.1.1 or newer and [`community.general`](https://docs.ansible.com/ansible/latest/collections/community/general/)
  9.0.0 or newer, which are installed automatically with this collection
- For the `site` playbook, the roles and collections in
  [`requirements.yml`](requirements.yml), which aren't installed automatically:
  `ansible-galaxy install -r requirements.yml`

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
| [`pypb.homelab.restic_k8up_users`](roles/restic_k8up_users/README.md) | Gives the k8up backup Schedules of a cluster their own rest-server logins, with their credential Secrets | Any Linux |
| [`pypb.homelab.acme_certificates`](roles/acme_certificates/README.md) | Trusts private CAs, and requests certificates from an ACME server with DNS-01 and installs them anywhere, including Unifi keystores | Debian 12 and 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.ubuntu_k3s_node`](roles/ubuntu_k3s_node/README.md) | Strips Ubuntu down to a minimal k3s node, and sets up sysctl, NFS, mount watchdogs, Cilium prerequisites, stopping pods at shutdown and the k3s server's PSA and audit files. Its `reboot` entry point reboots a node so that it leaves the cluster cleanly | Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.iscsi_initiator`](roles/iscsi_initiator/README.md) | Sets up open-iscsi and logs in to targets now and at boot, with a disk timeout for chosen vendors and optional multipathd | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.server_baseline`](roles/server_baseline/README.md) | Basic server configuration: packages, the Ubuntu mirror, the host's domain, a static resolv.conf, sysctl, journald and rsyslog, time zone, sudo, motd and banners, and the kernel consoles and GRUB menu | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.server_hardening`](roles/server_hardening/README.md) | Hardening beyond the baseline: sysctl, blocked kernel modules, masked services, purged packages, wifi and bluetooth, core dumps and idle shell timeouts | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.swap`](roles/swap/README.md) | Swap in compressed RAM with zram, encrypted swap on disk with a new key at every boot, and removing other swap files | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.unattended_upgrades`](roles/unattended_upgrades/README.md) | Installs upgrades automatically with unattended-upgrades, with reports, automatic reboots and any other apt settings | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.chrony`](roles/chrony/README.md) | Keeps the clock in sync with chrony, with sources and settings in its drop-in directories, replacing the distribution's sources | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.users`](roles/users/README.md) | Local groups and accounts with their SSH keys, including the account Ansible uses, and deletes an image's default accounts | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.nftables`](roles/nftables/README.md) | A host firewall that drops input its rules don't accept, replacing only its own table | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.fail2ban`](roles/fail2ban/README.md) | Bans hosts that fail to log in, with jails, defaults and action settings in fail2ban's `.local` files, banning through nftables | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.wireguard`](roles/wireguard/README.md) | A WireGuard interface with wg-quick, with listed peers, a mesh of inventory hosts and optional registration as a peer on OPNsense | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.haproxy`](roles/haproxy/README.md) | HAProxy, with frontends, backends and listen sections, checked with `haproxy -c` before they replace the running configuration | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.haproxy_geoip`](roles/haproxy_geoip/README.md) | Lists of countries' IP prefixes for HAProxy ACLs, from DB-IP, with a timer that keeps them up to date and keeps the last good prefixes when a download fails | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.lego`](roles/lego/README.md) | Certificates from Let's Encrypt or another ACME server with lego and DNS-01, including wildcards, renewed by a systemd timer, with hooks when one changes | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.docker_traefik`](roles/docker_traefik/README.md) | Traefik with Docker Compose, with its static configuration and files of dynamic configuration that it reloads by itself, and rotation of its log files | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.ocfs2`](roles/ocfs2/README.md) | Sets up the OCFS2 cluster file system with the o2cb cluster stack, its kernel module, fencing and the mounts | Debian 13, Ubuntu 24.04 and 26.04 |
| [`pypb.homelab.routeros_config`](roles/routeros_config/README.md) | MikroTik RouterOS configuration as code: numbered steps merged from any number of inventory variables and applied through the API, switch ports described once, SSH keys, an export before and an encrypted backup after a change | RouterOS 7 |

### Playbooks

| Playbook | Description |
|---|---|
| [`pypb.homelab.site`](playbooks/site.yml) | Configures servers in one run, in phases: access, base, firewall, services, monitoring and backup. A role only runs on hosts where its `site_<role>` variable is true |

```shell
ansible-playbook pypb.homelab.site
ansible-playbook pypb.homelab.site --tags monitoring --limit host1
ansible-playbook pypb.homelab.site --tags users -u bootstrap --limit newhost
ansible-playbook pypb.homelab.site --list-tags
```

The playbook targets the hosts in `site_hosts`, which defaults to the `site` group.
Each phase is tagged with its name, and each role with the name in the table.
The phases run in this order, and the roles within a phase in the order shown:

| Phase | Tag | Role | Enabled by |
|---|---|---|---|
| access | `users` | `pypb.homelab.users` | `site_users` |
| access | `sshd` | `willshersystems.sshd` | `site_sshd` |
| base | `server_baseline` | `pypb.homelab.server_baseline` | `site_server_baseline` |
| base | `chrony` | `pypb.homelab.chrony` | `site_chrony` |
| base | `swap` | `pypb.homelab.swap` | `site_swap` |
| base | `smtp_client` | `pypb.homelab.smtp_client` | `site_smtp_client` |
| base | `unattended_upgrades` | `pypb.homelab.unattended_upgrades` | `site_unattended_upgrades` |
| base | `acme_certificates` | `pypb.homelab.acme_certificates` | `site_acme_certificates` |
| firewall | `wireguard` | `pypb.homelab.wireguard` | `site_wireguard` |
| firewall | `nftables` | `pypb.homelab.nftables` | `site_nftables` |
| firewall | `fail2ban` | `pypb.homelab.fail2ban` | `site_fail2ban` |
| firewall | `server_hardening` | `pypb.homelab.server_hardening` | `site_server_hardening` |
| services | `docker` | `geerlingguy.docker` | `site_docker` |
| services | `lego` | `pypb.homelab.lego` | `site_lego` |
| services | `haproxy_geoip` | `pypb.homelab.haproxy_geoip` | `site_haproxy_geoip` |
| services | `haproxy` | `pypb.homelab.haproxy` | `site_haproxy` |
| services | `docker_traefik` | `pypb.homelab.docker_traefik` | `site_docker_traefik` |
| monitoring | `zabbix_agent` | `community.zabbix.zabbix_agent`, adding the `zabbix` user to `ssl-cert`, and to `docker` when `site_docker` is true | `site_zabbix_agent` |
| monitoring | `zabbix_host` | The `community.zabbix.zabbix_host` module | `site_zabbix_host` |
| monitoring | `alloy` | `grafana.grafana.alloy` | `site_alloy` |
| backup | `restic_backup` | The `pypb.homelab.restic_backup` playbook | `site_restic_backup` |

Every `site_<role>` variable defaults to false. The order is what the roles need:
the account Ansible uses exists before sshd limits logins, the certificates before
the services that use them, the firewall before the services open their ports,
fail2ban after nftables, which it bans through, the country lists before HAProxy,
whose configuration refers to them, Traefik and the Zabbix agent after
Docker.

`zabbix_host` registers the host through the Zabbix API host in
`zabbix_host_config_api_host`, with `zabbix_host_config_groups`,
`zabbix_host_config_link_templates`, `zabbix_host_config_interface_dns` and,
optionally, `zabbix_host_config_description`.

The roles from outside this collection are included when they run, so they only have
to be installed when a host enables them. `community.zabbix` is always needed.

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

| Playbook | Description |
|---|---|
| [`pypb.homelab.k3s_cluster`](playbooks/k3s_cluster.yml) | Sets up one k3s cluster: the `ubuntu_k3s_node` playbook, then k3s with `xanmanning.k3s`, then the rest-server logins of its k8up backups with `restic_k8up_users` |

```shell
ansible-playbook pypb.homelab.k3s_cluster
ansible-playbook pypb.homelab.k3s_cluster --tags k3s
ansible-playbook pypb.homelab.k3s_cluster -e k3s_cluster_hosts=cluster2
```

The playbook targets the hosts in `k3s_cluster_hosts`, which defaults to the
`k3s_cluster` group, and should be one cluster's nodes, since `xanmanning.k3s`
builds a cluster from them. Its steps run in this order:

| Tag | Step | Runs on |
|---|---|---|
| `ubuntu_k3s_node` | The [`pypb.homelab.ubuntu_k3s_node`](playbooks/ubuntu_k3s_node.yml) playbook | One node at a time |
| `k3s` | `xanmanning.k3s`, configured with its own `k3s_*` variables | All nodes together |
| `restic_k8up_users` | `pypb.homelab.restic_k8up_users` | The first node, when `restic_k8up_users_enable` is true there |

`xanmanning.k3s` is listed in `requirements.yml`. It's included when it runs, so
it only has to be installed for the `k3s` step.

| Playbook | Description |
|---|---|
| [`pypb.homelab.upgrade`](playbooks/upgrade.yml) | Installs every pending upgrade on Debian and Ubuntu, one host at a time, and reboots the hosts that ask for it or run an older kernel than the newest installed one. k3s nodes leave the cluster cleanly first |

```shell
ansible-playbook pypb.homelab.upgrade
ansible-playbook pypb.homelab.upgrade --limit host1 -e upgrade_reboot=false
```

The playbook targets the hosts in `upgrade_hosts`, which defaults to the `servers`
group. It stops at the first host that fails. It reboots through the
`ubuntu_k3s_node` role's [`reboot` entry point](roles/ubuntu_k3s_node/README.md#rebooting),
so on a k3s node it stops k3s and its pods, unmounts `ocfs2_mounts` when
`ubuntu_k3s_node_ocfs2` is true, and waits for servers to be Ready before the next
host. On other hosts it's a plain reboot.

| Variable | Default | Description |
|---|---|---|
| `upgrade_hosts` | `servers` | Hosts to upgrade |
| `upgrade_reboot` | `true` | Reboot the hosts that need it |
| `upgrade_cache_valid_time` | `3600` | Seconds the package lists stay valid before they're updated |
| `upgrade_post_reboot_delay` | `30` | Seconds to wait after a host is back, before checking it |

| Playbook | Description |
|---|---|
| [`pypb.homelab.routeros`](playbooks/routeros.yml) | Configures RouterOS devices with `routeros_config`, one at a time, connecting from the controller |

```shell
ansible-playbook pypb.homelab.routeros --check --diff --limit sw1
```

The playbook targets the hosts in `routeros_hosts`, which defaults to the
`routeros` group.

### Plugins

| Plugin | Type | Description |
|---|---|---|
| [`pypb.homelab.routeros_config_plan`](plugins/filter/routeros_config_plan.yml) | filter | Orders and checks the steps of `routeros_config`, joining the operations on the same path |
| [`pypb.homelab.routeros_config_ports`](plugins/filter/routeros_config_ports.yml) | filter | Turns ports and bridges described once into bridge, ethernet, PoE, bridge port and bridge VLAN entries |
| [`pypb.homelab.routeros_ssh_fingerprint`](plugins/filter/routeros_ssh_fingerprint.yml) | filter | The SHA256 fingerprint of an SSH public key, as RouterOS shows it |

### Collection-wide variables

These are not set by any role, but roles use them as defaults when they are
defined in your inventory.

| Variable | Used by | Description |
|---|---|---|
| `restic_server_hostname` | `restic_server_users`, `restic_k8up_users` | Host running the rest-server container |
| `restic_server_container` | `restic_server_users`, `restic_k8up_users` | Name of the rest-server container |
| `restic_backup_repo_url` | `restic_k8up_users` | Also `restic_backup`'s own variable. Its host is the rest-server's |

## Development

Clone the repository to a path ending in `ansible_collections/pypb/homelab`,
which `ansible-test` requires.

```shell
uv sync

yamllint .
ansible-lint
ruff check .
ansible-test sanity --docker default
ansible-test units --docker default
ansible-galaxy collection build

cd extensions
molecule test --scenario-name restic_server_users
molecule test --scenario-name restic_k8up_users
molecule test --scenario-name restic_backup
molecule test --scenario-name smtp_client
molecule test --scenario-name acme_certificates
molecule test --scenario-name ubuntu_k3s_node
molecule test --scenario-name ocfs2
molecule test --scenario-name iscsi_initiator
molecule test --scenario-name server_baseline
molecule test --scenario-name server_hardening
molecule test --scenario-name swap
molecule test --scenario-name unattended_upgrades
molecule test --scenario-name chrony
molecule test --scenario-name users
molecule test --scenario-name nftables
molecule test --scenario-name fail2ban
molecule test --scenario-name wireguard
molecule test --scenario-name haproxy
molecule test --scenario-name haproxy_geoip
molecule test --scenario-name lego
molecule test --scenario-name docker_traefik
molecule test --scenario-name routeros_config
molecule test --scenario-name site
molecule test --scenario-name upgrade
```

The molecule scenarios need Docker, or Podman with its API socket enabled and
`DOCKER_HOST` pointing to it, and the `docker` command, which can be Podman's. They also
need this collection, `ansible.posix`, `community.docker`, `community.crypto` and
`community.general` on `ANSIBLE_COLLECTIONS_PATH`, and the `site` scenario also
`community.zabbix`. The `routeros_config` scenario only works out the plan, so it
needs no container or device.

Describe each change in a fragment under `changelogs/fragments/`, then generate
the changelog at release time with `antsibull-changelog release`.

## License

Apache License 2.0. See [LICENSE](LICENSE) for the full text.
