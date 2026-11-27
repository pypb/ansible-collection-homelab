# pypb.homelab.lego

Certificates from Let's Encrypt, or another ACME server, with
[lego](https://go-acme.github.io/lego/) and the DNS-01 challenge:

- Installs lego from the distribution.
- Installs a script, `/usr/local/sbin/lego-certificates`, that issues each
  certificate that's missing or whose names changed, and renews the others when
  they expire within `lego_renew_days`. When a certificate changes, its hooks
  run, such as a reload of the service that uses it.
- Runs the script while the role runs when a certificate is missing or the
  script changed, so that what uses the certificates can be set up after it.
- Runs the script daily from a systemd timer, and hourly after a failure.

DNS-01 also works for wildcard names and for hosts that aren't reachable from
the internet. lego supports most DNS providers (`lego dnshelp`).

## Requirements

- ansible-core 2.21 or newer

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04

## Role variables

| Variable | Default | Description |
|---|---|---|
| `lego_enabled` | `false` | Issue and renew the certificates. False removes the timer, service, script and provider environment, and keeps `lego_path` |
| `lego_email` | `""` | The ACME account's address. Required when enabled |
| `lego_server` | Let's Encrypt | The ACME directory |
| `lego_dns_provider` | `""` | lego's DNS provider, such as `desec` or `rfc2136`. Required when enabled |
| `lego_environment` | `{}` | The provider's settings as environment variables, such as `DESEC_TOKEN`, in `/etc/lego/environment` (`root`, `0600`) |
| `lego_dns_resolvers` | `[]` | Resolvers (`host:port`) for lego's check that the TXT record is there. Empty uses the system's |
| `lego_certificates` | `[]` | Certificates, each with `domains` and optionally `hooks` |
| `lego_key_type` | `ec256` | lego's key type |
| `lego_renew_days` | `30` | Renew certificates that expire within this many days |
| `lego_path` | `/var/lib/lego` | lego's directory, with the account and the certificates |
| `lego_on_calendar` | `daily` | When the timer runs, as `OnCalendar`, with up to an hour's random delay |

Each certificate is written to
`<lego_path>/certificates/<first domain, with * as _>`: `.pem` with the key and
the full chain, which HAProxy reads as is, and `.crt` and `.key`. No two
certificates may start with the same domain. A certificate removed from the
list is left there.

Hooks run with `sh -c`, in order, when a certificate's file changes, also the
first time. When one fails, the service fails and is retried hourly, and all
of the certificate's hooks run again then, also without a new certificate. On a new host, the service a hook reloads may not be installed
yet, so make the hook succeed then, for example
`! systemctl --quiet is-active haproxy || systemctl reload haproxy`.

## Example playbook

```yaml
- name: A wildcard certificate for HAProxy
  hosts: load_balancers
  become: true
  roles:
    - role: pypb.homelab.lego
      vars:
        lego_enabled: true
        lego_email: hostmaster@example.com
        lego_dns_provider: desec
        lego_environment:
          DESEC_TOKEN: "{{ vaulted_desec_token }}"
        lego_certificates:
          - domains: ["*.example.com"]
            hooks:
              - "! systemctl --quiet is-active haproxy || systemctl reload haproxy"
```

HAProxy then uses `crt /var/lib/lego/certificates/_.example.com.pem`.

## Behaviour

- **Idempotent:** yes. lego only runs while the role runs when a certificate is
  missing or the script changed.
- **Atomic:** no. A certificate that fails doesn't stop the others.
- **Check mode:** yes. lego doesn't run.
- **Applied right away:** yes, for new and changed certificates.
- **Replaced files:** `/usr/local/sbin/lego-certificates`,
  `/etc/lego/environment` and the `lego-certificates` service and timer.
- **Rollback:** set `lego_enabled: false`, which keeps the certificates.

## License

Apache-2.0

## Author

pypb
