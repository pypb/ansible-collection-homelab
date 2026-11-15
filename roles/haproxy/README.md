# pypb.homelab.haproxy

Sets up HAProxy:

- Installs HAProxy and writes `/etc/haproxy/haproxy.cfg`: the global and
  defaults sections, then the frontends, backends and listen sections.
- Checks the configuration with `haproxy -c` before writing it, so a broken one
  never replaces the running one.
- Reloads HAProxy after a change, which keeps established connections, and
  starts it at boot.

Each section is given as its lines, as in HAProxy's own configuration.

## Requirements

- ansible-core 2.21 or newer

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04

## Role variables

| Variable | Default | Description |
|---|---|---|
| `haproxy_global` | Logging to stdout, and an admin stats socket | Lines of the global section, after the distribution's `chroot`, `user`, `group` and `daemon` |
| `haproxy_defaults` | HTTP mode, with the distribution's timeouts and error files | Lines of the defaults section |
| `haproxy_frontends` | `{}` | Frontends, as a dict of name and lines |
| `haproxy_backends` | `{}` | Backends, as a dict of name and lines |
| `haproxy_listens` | `{}` | Listen sections, as a dict of name and lines |

Replacing `haproxy_global` drops the default logging and stats socket. Keep
`expose-fd listeners` on the stats socket, so that reloads keep the listening
sockets. Section names must be unique across frontends, backends and listen
sections.

## Example playbook

```yaml
- name: Pass HTTPS through to the ingress, by SNI
  hosts: load_balancers
  become: true
  roles:
    - role: pypb.homelab.haproxy
      vars:
        haproxy_defaults: |
          mode tcp
          log global
          timeout connect 5s
          timeout client 30s
          timeout server 30s
        haproxy_frontends:
          https: |
            bind :443
            tcp-request inspect-delay 2s
            tcp-request content accept if { req_ssl_hello_type 1 }
            use_backend ingress if { req_ssl_sni -m end .example.org }
            default_backend deny
        haproxy_backends:
          ingress: |
            server ingress 192.0.2.10:443 check send-proxy-v2
          deny: |
            tcp-request content reject
```

## Behaviour

- **Idempotent:** yes.
- **Atomic:** yes. The configuration is checked before it's written.
- **Check mode:** yes. The configuration isn't checked with `haproxy -c`.
- **Applied right away:** HAProxy reloads when the configuration changes.
- **Replaced files:** `/etc/haproxy/haproxy.cfg`.
- **Rollback:** none needed, since a broken configuration is never written.

## License

Apache-2.0

## Author

pypb
