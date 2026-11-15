# pypb.homelab.fail2ban

Bans hosts that keep failing to log in, with fail2ban:

- Installs fail2ban and python3-systemd, so that jails can read the journal.
- Writes fail2ban's settings to `/etc/fail2ban/fail2ban.local`, the jails and
  their defaults to `/etc/fail2ban/jail.local`, and action settings to
  `/etc/fail2ban/action.d/<action>.local`. These override the distribution's
  files, which stay as they are.
- Checks the settings with `fail2ban-client --test` before reloading fail2ban.

By default, the sshd jail reads sshd's messages from the journal and bans
through nftables, in a table of fail2ban's own. That works next to the
[`nftables`](../nftables/README.md) role, which only replaces its own table.

## Requirements

- ansible-core 2.21 or newer

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04, including on a Raspberry Pi

## Role variables

| Variable | Default | Description |
|---|---|---|
| `fail2ban_settings` | `{}` | fail2ban's own settings, such as `loglevel` and `logtarget` |
| `fail2ban_jail_defaults` | nftables ban actions | Settings every jail inherits, such as `bantime` and `maxretry` |
| `fail2ban_jails` | The sshd jail, reading the journal | Jails, as a dict of jail name and settings |
| `fail2ban_ignore_ips` | `[127.0.0.0/8, "::1"]` | Addresses and networks that are never banned |
| `fail2ban_action_settings` | `{}` | Action settings, as a dict of action, section and settings |

Each dict replaces the default rather than adding to it, so to add a jail,
list the sshd jail too.

## Example playbook

```yaml
- name: Ban failed logins
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.fail2ban
      vars:
        fail2ban_settings:
          logtarget: SYSTEMD-JOURNAL
        fail2ban_jail_defaults:
          banaction: nftables-multiport
          banaction_allports: nftables-allports
          bantime: 1h
        fail2ban_ignore_ips: [127.0.0.0/8, "::1", 192.0.2.0/24]
        # Ban before connection tracking, so that established connections from a
        # banned host are cut too.
        fail2ban_action_settings:
          nftables-common:
            Init:
              chain_hook: prerouting
              chain_priority: -50
```

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes. The settings aren't checked with `fail2ban-client`.
- **Applied right away:** fail2ban reloads when a file changes.
- **Replaced files:** `fail2ban.local`, `jail.local` and the action `.local`
  files the role writes. Action files for actions taken off
  `fail2ban_action_settings` stay.
- **Rollback:** none.

## License

Apache-2.0

## Author

pypb
