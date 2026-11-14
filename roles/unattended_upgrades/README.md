# pypb.homelab.unattended_upgrades

Installs security and other upgrades automatically with unattended-upgrades:

- Installs unattended-upgrades, and turns the daily package list updates and
  upgrades on or off in `/etc/apt/apt.conf.d/20auto-upgrades`.
- Writes the report, reboot and cleanup settings, and any other apt settings, to
  `/etc/apt/apt.conf.d/52unattended-upgrades-local`. That file comes after the
  distribution's `50unattended-upgrades` and overrides it, so which origins are
  upgraded stays as the distribution ships it unless you change it.
- Makes sure the apt timers that run it are enabled.

## Requirements

- ansible-core 2.21 or newer
- For reports, a working `sendmail` or `mail` command, such as the one the
  [`pypb.homelab.smtp_client`](../smtp_client/README.md) role sets up

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04

## Role variables

| Variable | Default | Description |
|---|---|---|
| `unattended_upgrades_enabled` | `true` | Install unattended-upgrades and run it every day. False stops it from running, but leaves the package installed |
| `unattended_upgrades_update_package_lists` | `true` | Update the package lists every day |
| `unattended_upgrades_mail` | `""` | Where reports go, such as `root`. No mail when empty |
| `unattended_upgrades_mail_report` | `on-change` | When to send a report: `always`, `only-on-error` or `on-change` |
| `unattended_upgrades_automatic_reboot` | `false` | Reboot when an upgrade needs it |
| `unattended_upgrades_automatic_reboot_time` | `now` | When to reboot: `now`, or a time such as `02:00` |
| `unattended_upgrades_remove_unused_dependencies` | `false` | Purge the packages that upgrades leave unneeded |
| `unattended_upgrades_syslog` | `false` | Log to syslog as well as to `/var/log/unattended-upgrades` |
| `unattended_upgrades_settings` | `{}` | Other apt settings, by their full names. These override the variables above |

In `unattended_upgrades_settings`, booleans are written as `"true"` and `"false"`,
and a list adds to the distribution's list of the same name:

```yaml
unattended_upgrades_settings:
  Unattended-Upgrade::Automatic-Reboot-WithUsers: false
  Unattended-Upgrade::Package-Blacklist:
    - linux-image-.*
```

## Example playbook

Set the common settings for every host, and stagger the reboots of nodes that
share a cluster, so that they never reboot together:

```yaml
# group_vars/all.yml
unattended_upgrades_mail: root
unattended_upgrades_mail_report: only-on-error
unattended_upgrades_automatic_reboot: true
unattended_upgrades_remove_unused_dependencies: true

# host_vars/node2.yml
unattended_upgrades_automatic_reboot_time: "03:00"
```

```yaml
- name: Install upgrades automatically
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.unattended_upgrades
```

## Automatic reboots

unattended-upgrades reboots with `shutdown -r`, so the services stop as in any
other reboot. On k3s nodes with shared file systems, the
[`pypb.homelab.ubuntu_k3s_node`](../ubuntu_k3s_node/README.md#stopping-pods-at-shutdown)
role stops the pods first, so that the file systems unmount. Nothing drains the
node: its pods stop until it's back.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes.
- **Applied right away:** all of it. The next run of `apt-daily-upgrade.timer` uses
  the settings.
- **Replaced files:** `20auto-upgrades` and `52unattended-upgrades-local` are
  replaced in full, and checked with `apt-config` before they're written.
- **Rollback:** set `unattended_upgrades_enabled` to false.

## License

Apache-2.0

## Author

pypb
