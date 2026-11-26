# pypb.homelab.haproxy_geoip

Lists of countries' IP prefixes for HAProxy ACLs, kept up to date. Set
`haproxy_geoip_enabled` to true to write them:

- Writes each list in `haproxy_geoip_lists` to `<haproxy_geoip_dir>/<name>.lst`,
  with the IPv4 and IPv6 prefixes of its countries, for `src -f` in an ACL.
- Installs `/usr/local/sbin/haproxy-geoip-update` and a systemd timer that runs
  it. It downloads each new month of DB-IP's
  [IP to Country Lite](https://db-ip.com/db/download/ip-to-country-lite), which
  places addresses where they're used, rather than where the block is
  registered, rebuilds the lists and reloads HAProxy when one changed.
- Keeps each country's last good prefixes in `<haproxy_geoip_dir>/countries/`.
  A download that fails, or a country that looks broken in it, keeps them, so
  the lists only get older while the downloads fail. A failed run is retried
  hourly.
- Builds the lists before it ends, so a HAProxy configuration that refers to them
  can be checked right after. Run it before `pypb.homelab.haproxy`.
- With `haproxy_geoip_enabled` false, the default, removes all of it: the
  timer and service, the script and `haproxy_geoip_dir`.

IP Geolocation by DB-IP (https://db-ip.com), CC BY 4.0.

## Requirements

- ansible-core 2.21 or newer
- Python 3 on the host, and HTTPS access to `download.db-ip.com`

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04

## Role variables

| Variable | Default | Description |
|---|---|---|
| `haproxy_geoip_enabled` | `false` | Write and update the lists. False removes them, with the script, its timer and `haproxy_geoip_dir` |
| `haproxy_geoip_lists` | `{}` | Lists, as a dict of list name and its countries' ISO codes |
| `haproxy_geoip_dir` | `/etc/haproxy/geoip` | Directory of the lists, the countries' prefixes and the configuration |
| `haproxy_geoip_seeds_dir` | `""` | Directory on the controller with a `<code>.lst` seed per country |
| `haproxy_geoip_on_calendar` | `daily` | When to look for a new month, as a systemd `OnCalendar` expression, plus a random delay of up to an hour |
| `haproxy_geoip_min_prefixes` | `50` | A country with fewer IPv4 prefixes than this in a download, or less than half as many as before, keeps its last good prefixes |

A month that has been applied isn't downloaded again, unless a country has no
prefixes yet. A list that is removed from `haproxy_geoip_lists` is left on the
host.

### Turning it off

Remove the ACLs that refer to the lists first, in the same run or before, then
set `haproxy_geoip_enabled` to false. HAProxy keeps running without the lists,
but can't reload, restart or start at boot while its configuration refers to
them. So the role fails without removing anything while any of these still
refer to `haproxy_geoip_dir`: `haproxy_frontends`, `haproxy_backends`,
`haproxy_listens`, `haproxy_global` and `haproxy_defaults`. Those are the
variables of `pypb.homelab.haproxy`, so the check covers that role's
configuration, not one written some other way.

`haproxy_geoip_dir` must be an absolute path at least two levels below `/`,
since it's deleted.

### Seeds

The first time a host needs a country, its prefixes come from the seed in
`haproxy_geoip_seeds_dir`, if there is one, and are replaced by the first
download that works. A country without a seed is downloaded while the role
runs, and the role fails if that download does. Seeds let a new host get its
lists while DB-IP can't be reached. Write them with the role's script, which
gives them the same form as on the host, and they only need to be recent
enough to be usable:

```shell
python3 -I roles/haproxy_geoip/files/haproxy_geoip_update.py --seeds files/geoip se dk
```

## Example playbook

```yaml
- name: Let only clients in Sweden and Denmark through
  hosts: load_balancers
  become: true
  tasks:
    - name: Write the country lists
      ansible.builtin.include_role:
        name: pypb.homelab.haproxy_geoip
      vars:
        haproxy_geoip_enabled: true
        haproxy_geoip_lists:
          web_allowed: [se, dk]

    - name: Set up HAProxy
      ansible.builtin.include_role:
        name: pypb.homelab.haproxy
      vars:
        haproxy_defaults: |
          mode tcp
          timeout connect 5s
          timeout client 30s
          timeout server 30s
        haproxy_frontends:
          https: |
            bind :443
            default_backend web_allowed
        haproxy_backends:
          web_allowed: |
            tcp-request content reject unless { src -f /etc/haproxy/geoip/web_allowed.lst }
            server web 192.0.2.10:443 check
```

## Behaviour

- **Idempotent:** yes.
- **Atomic:** yes. Every file the script writes replaces the old one in one step.
- **Check mode:** yes. The lists aren't built and nothing is downloaded.
- **Applied right away:** the lists are built while the role runs, and a new
  version of the script downloads right after. HAProxy is reloaded, if it runs,
  when a list changes.
- **Replaced files:** the lists, `<haproxy_geoip_dir>/config.json`,
  `/usr/local/sbin/haproxy-geoip-update` and
  `/etc/systemd/system/haproxy-geoip-update.{service,timer}`. A country's
  prefixes are only replaced by a download that looks good.
- **Rollback:** none needed. A download that looks broken is never applied.
  Set `haproxy_geoip_enabled` to false to remove the role's files.

## License

Apache-2.0

## Author

pypb
