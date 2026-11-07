# pypb.homelab.smtp_client

Sets up the part of a server that sends mail: an SMTP client and `sendmail`, for
cron and other programs, that pass all of the host's mail on to an SMTP relay. It
also manages mail aliases. The client is [msmtp](https://marlam.de/msmtp/).

## Requirements

- Root access on the target, for example through `become`
- An SMTP relay

## Supported platforms

| Platform | Versions | Tested |
|---|---|---|
| Debian | 13 (trixie) | Molecule |
| Ubuntu | 24.04 (noble), 26.04 (resolute) | Molecule |

The role only installs packages on the Debian family. On other distributions,
install msmtp yourself and leave the package variables on or off as you like.

## Role variables

| Variable | Default | Description |
|---|---|---|
| `smtp_client_install` | `true` | Install msmtp |
| `smtp_client_install_sendmail` | `true` | Install the `msmtp-mta` package, which provides `sendmail`. See [Other MTAs](#other-mtas) |
| `smtp_client_remove_other_mta` | `false` | Let `msmtp-mta` replace other MTAs. See [Other MTAs](#other-mtas) |
| `smtp_client_configure` | `true` | Template `/etc/msmtprc`, create the files it needs and manage aliases |
| `smtp_client_relay_host` | None | Relay to send all mail through. Required when `smtp_client_configure` is true |
| `smtp_client_relay_port` | `25` | Port of the relay |
| `smtp_client_relay_user` | None | Login for the relay. Set together with `smtp_client_relay_password` |
| `smtp_client_relay_password` | None | Password for the relay. Set together with `smtp_client_relay_user` |
| `smtp_client_tls` | `true` | Use TLS for the connection to the relay |
| `smtp_client_starttls` | `true` | Start TLS with the STARTTLS command rather than when connecting |
| `smtp_client_from` | `%U@%M` | Envelope sender. `%U` is the user name and `%M` the contents of `/etc/mailname` |
| `smtp_client_helo_domain` | `%M` | Domain sent in the SMTP EHLO command |
| `smtp_client_aliases` | `{}` | Entries for `/etc/aliases`. See [Aliases](#aliases) |

To skip a host, set `smtp_client_install`, `smtp_client_install_sendmail` and `smtp_client_configure` to
false. The role then does nothing, and `smtp_client_relay_host` isn't needed.

## Example playbook

```yaml
- name: Send mail through a relay
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.smtp_client
      vars:
        smtp_client_relay_host: mail.example.com
        smtp_client_relay_port: 587
        smtp_client_relay_user: server
        smtp_client_relay_password: "{{ vaulted_smtp_relay_password }}"
        smtp_client_aliases:
          root: admin@example.com
```

## Aliases

Aliases decide where mail goes when a recipient has no domain, such as mail to
`root` from cron. `smtp_client_aliases` maps those names to addresses:

```yaml
smtp_client_aliases:
  root: admin@example.com
  backup: admin@example.com, backup@example.com
  retired: null
```

The entries are merged into `/etc/aliases`. An existing entry with the same name
is replaced, other entries are left alone, and a null value removes an entry. So
removing a name from the variable doesn't remove it from the file: set it to null
for one run first.

An address may be another alias. An entry named `default` catches every name
without its own entry.

## Other MTAs

`msmtp-mta` can't be installed alongside another MTA, such as Postfix or Exim. The
role looks for any installed package that provides one. If it finds any:

- **By default**, it prints a message saying so and does nothing else on that host.
  The play continues and the host isn't reported as failed. Check your output for
  this message, because nothing else shows that msmtp wasn't set up.
- **With `smtp_client_remove_other_mta: true`**, `msmtp-mta` replaces the MTA. Mail
  still queued in the old MTA isn't sent, and its configuration files stay on disk.
  Packages that only need some MTA, such as `bsd-mailx`, stay installed.

With `smtp_client_install_sendmail: false` there is no conflict, so the role doesn't
look for other MTAs and never removes them. msmtp is then set up alongside them, and
the other MTA keeps providing `sendmail`.

## Who can send mail

The `msmtp` binary runs with the permissions of the user sending the mail, so
that user has to be able to read `/etc/msmtprc`.

- **Without a login**, the file is `0644`, so every user can send mail.
- **With a login**, the file is `0640` and owned by `root:msmtp`, to protect the
  password. Only root and members of the `msmtp` group can send mail, and those
  members can read the password.

## Behaviour

- **Idempotent:** yes.
- **Other MTAs:** detected on the Debian family only.
- **Atomic:** no.
- **Check mode:** partly. Configuration files are checked, but package
  installation is skipped and isn't reported as a pending change.
- **Created files:** msmtp fails to send without `/etc/mailname` if it's used by
  `smtp_client_from` or `smtp_client_helo_domain`, and without `/etc/aliases` if a recipient
  has no domain. The role creates each of these if it's missing, with
  `/etc/mailname` holding the host's FQDN. It doesn't change `/etc/mailname` if it exists.
- **Unmatched aliases:** mail to a name with no entry and no `default` entry goes
  to the relay as it is, for example as `root`.
- **Replaced files:** `/etc/msmtprc` is replaced in full, without a backup, so
  that old credentials aren't left behind.
- **Secrets:** changes to `/etc/msmtprc` aren't shown by `--diff` when
  `smtp_client_relay_password` is set.
- **Rollback:** none.

## License

Apache-2.0

## Author

pypb
