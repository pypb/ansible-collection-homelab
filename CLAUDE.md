# pypb.homelab

Ansible collection for managing a homelab. Existing roles are being tidied and
migrated into `roles/`.

## Content

- Roles:
  - `smtp_client`: sets up msmtp as the sendmail and SMTP client of a server, sending mail through a relay
  - `restic_backup`: installs and configures restic and resticprofile
  - `restic_server_users`: manages logins on a containerised rest-server
  - `restic_k8up_users`: rest-server logins and credential Secrets for a cluster's
    k8up Schedules
  - `acme_certificates`: trusts private CAs, and requests certificates from an ACME
    server with DNS-01, installing them anywhere, including Unifi keystores
  - `ubuntu_k3s_node`: strips Ubuntu down to a minimal k3s node, with sysctl, NFS,
    mount watchdogs, Cilium prerequisites, stopping pods at shutdown and the k3s
    server's PSA and audit files, plus a `reboot` entry point that leaves the
    cluster cleanly
  - `ocfs2`: sets up the OCFS2 cluster file system with o2cb, and its mounts
  - `iscsi_initiator`: sets up open-iscsi and logs in to targets, with optional multipathd
  - `server_baseline`: basic configuration of a Debian or Ubuntu server, including
    resolv.conf, journald, motd and the kernel consoles and GRUB menu
  - `server_hardening`: opt-in hardening beyond the baseline: sysctl, blocked
    kernel modules, masked services, purged packages, wifi and bluetooth
  - `swap`: zram swap with systemd-zram-generator, and encrypted swap in a file
    through crypttab
  - `unattended_upgrades`: installs upgrades automatically, with reports and reboots
  - `chrony`: keeps the clock in sync with chrony, using its drop-in directories
  - `users`: local groups and accounts with their SSH keys, including the account
    Ansible uses, and deletes unwanted accounts
  - `nftables`: a host firewall with nftables, replacing only its own table
  - `fail2ban`: bans hosts that fail to log in, banning through nftables
  - `wireguard`: a WireGuard interface with wg-quick, with peers, a mesh of inventory
    hosts and registration as a peer on OPNsense
  - `haproxy`: HAProxy with frontends, backends and listen sections, checked before
    they are loaded
  - `docker_traefik`: Traefik with Docker Compose, with its static and dynamic
    configuration
  - `routeros_config`: MikroTik RouterOS configuration in numbered steps merged from
    `routeros_config_steps_*` variables, with switch ports described once, SSH keys,
    an export and a device backup
- Playbooks:
  - `site`: configures servers in phases (access, base, firewall, services,
    monitoring, backup), running each role where its `site_<role>` variable is
    true, with a tag per phase and per role. External content it uses is listed
    in `requirements.yml`
  - `restic_backup`: combines both restic roles
  - `ubuntu_k3s_node`: runs `ubuntu_k3s_node`, and optionally `iscsi_initiator` and
    `ocfs2`, one node at a time
  - `k3s_cluster`: one k3s cluster: the `ubuntu_k3s_node` playbook, k3s with
    `xanmanning.k3s` and `restic_k8up_users`
  - `upgrade`: installs all pending upgrades one host at a time, rebooting through
    the `ubuntu_k3s_node` role's `reboot` entry point
  - `routeros`: runs `routeros_config` on the `routeros` group, one device at a time
- Plugins:
  - filters `routeros_config_plan`, `routeros_config_ports` and
    `routeros_ssh_fingerprint` in `plugins/filter/routeros.py`, with their docs in
    `.yml` files beside it

Update these lists, and the matching sections of `README.md`, when content is
added.

## Commands

- Build: `ansible-galaxy collection build`
- Install dependencies: `uv sync`
- Lint: `yamllint .`, `ansible-lint` and `ruff check .`
- Sanity tests: `ansible-test sanity --docker default`
- Unit tests: `ansible-test units --docker default`, or quicker,
  `PYTHONPATH=<dir above ansible_collections> python -m pytest tests/unit`
- Molecule: run `molecule test --scenario-name <name>` from `extensions/`, with
  `ANSIBLE_COLLECTIONS_PATH` covering this collection, `ansible.posix`,
  `community.docker`, `community.crypto` and `community.general`, and for the
  `site` scenario `community.zabbix`. The `routeros_config` scenario runs on
  localhost without a device.
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
