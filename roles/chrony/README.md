# pypb.homelab.chrony

Keeps the clock in sync with chrony:

- Installs chrony, and purges the other time daemons, such as systemd-timesyncd.
- Writes the NTP servers and pools to `/etc/chrony/sources.d/ansible.sources`,
  and other settings to `/etc/chrony/conf.d/ansible.conf`. The distribution's
  `chrony.conf` stays in place and reads both directories.
- With servers or pools of its own, turns off the distribution's sources, and
  turns them back on when it has none.
- Optionally sets the options chronyd starts with.

## Requirements

- ansible-core 2.21 or newer

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04

## Role variables

| Variable | Default | Description |
|---|---|---|
| `chrony_servers` | `[]` | NTP servers, each a host name or address, or a dict with `host` and `options` |
| `chrony_pools` | `[]` | NTP pools, in the same form |
| `chrony_source_options` | `[iburst]` | Options for the servers and pools that don't set their own |
| `chrony_settings` | `{}` | Other `chrony.conf` directives. A list writes the directive once for each item, and `true` writes it with no value |
| `chrony_daemon_opts` | `""` | The options chronyd starts with, in `/etc/default/chrony`. Unmanaged when empty |
| `chrony_purged_packages` | `[ntp, ntpsec, openntpd, systemd-timesyncd]` | Time daemons to purge |

When both `chrony_servers` and `chrony_pools` are empty, chrony uses the
distribution's sources.

## Example playbook

Use two local servers and a pool, require two sources to agree before the
clock is changed, and serve time to the local network:

```yaml
- name: Keep the clock in sync
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.chrony
      vars:
        chrony_servers:
          - ntp1.example.com
          - host: 192.0.2.123
            options: [iburst, prefer]
        chrony_pools:
          - pool.ntp.org
        chrony_source_options: [iburst, maxpoll 12]
        chrony_settings:
          minsources: 2
          allow:
            - 192.0.2.0/24
```

## The distribution's sources

Debian and Ubuntu 24.04 list their pools in `chrony.conf` itself, and Ubuntu
26.04 in `sources.d/ubuntu-ntp-pools.sources`. With sources of its own, the role
turns those off:

- In `chrony.conf`, it puts `#ansible-disabled# ` in front of each `pool`,
  `server` and `peer` line.
- In `sources.d`, it renames the other `.sources` files to `.sources.disabled`,
  so that chrony skips them.

When the role has no sources again, it undoes both. Sources from DHCP, in
`/run/chrony-dhcp`, stay on.

A `chrony.conf` that another tool replaced may not read `sources.d` and
`conf.d`. In that case, the role puts back the distribution's, from the copy the
package keeps in `/usr/share/chrony/chrony.conf`.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes. On a host without chrony, only the package changes are
  shown.
- **Applied right away:** yes. chrony restarts when its settings change.
- **Containers:** Ubuntu 26.04's chrony unit doesn't start in a container, which
  shares its host's clock, so there the role reports a change on every run.
- **Replaced files:** `ansible.sources` and `ansible.conf`, both checked with
  `chronyd -p` before they're written. The check reads a temporary copy in
  `/etc/chrony`, since Ubuntu's AppArmor profile lets chronyd read nothing else. A `chrony.conf` without the drop-in
  directories is replaced by the distribution's, and the distribution's sources
  are renamed or commented out, as described above.
- **Rollback:** empty `chrony_servers`, `chrony_pools` and `chrony_settings`
  bring back the distribution's sources and settings.

## License

Apache-2.0

## Author

pypb
