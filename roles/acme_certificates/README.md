# pypb.homelab.acme_certificates

Requests TLS certificates from an ACME server and installs them where your services
expect them. It renews them before they expire and runs commands, such as a service
reload, when a certificate changes. It can also add CA certificates to the system
trust store, for example the root of a private CA such as
[step-ca](https://smallstep.com/docs/step-ca/), and install a certificate in the
keystore of a Unifi Network controller.

The role proves control of each name with the DNS-01 challenge. It adds the challenge
records with dynamic DNS updates (RFC 2136, `nsupdate`), signed with a TSIG key, and
removes them again afterwards.

## Requirements

- Root access on the target, for example through `become`
- The `community.crypto` and `community.general` collections, which are installed
  with this collection
- An ACME server, and a DNS server that accepts signed dynamic updates for the zones
  of the certificate names. The target sends the updates itself, so it must be able
  to reach the DNS server.
- On the target, Python with `cryptography` and `dnspython`. The role installs them
  on the Debian family.

## Supported platforms

| Platform | Versions | Tested |
|---|---|---|
| Debian | 12 (bookworm), 13 (trixie) | Molecule |
| Ubuntu | 24.04 (noble), 26.04 (resolute) | Molecule |

Proxmox VE is based on Debian and works the same way. The role only installs packages
on the Debian family. On other distributions, install the requirements yourself, set
`acme_certificates_install_packages` to false, and set `acme_certificates_trust_dir`,
`acme_certificates_trust_update_command` and `acme_certificates_trust_remove_command`
to suit the distribution if you trust CAs. For example on the Red Hat family,
`/etc/pki/ca-trust/source/anchors` and `[update-ca-trust]` for both commands.

## Role variables

| Variable | Default | Description |
|---|---|---|
| `acme_certificates_install_packages` | `true` | Install `acme_certificates_packages` on the Debian family |
| `acme_certificates_packages` | `[ca-certificates, python3-cryptography, python3-dnspython, ssl-cert]` | Packages the role needs |
| `acme_certificates_trusted_cas` | `[]` | CA certificates to trust. See [Trusted CAs](#trusted-cas) |
| `acme_certificates_trust_dir` | `/usr/local/share/ca-certificates` | Where the CA certificates are written |
| `acme_certificates_trust_update_command` | `[update-ca-certificates]` | Command, as a list of arguments, that updates the trust store after a CA is added |
| `acme_certificates_trust_remove_command` | `[update-ca-certificates, --fresh]` | Command that rebuilds the trust store after a CA is removed |
| `acme_certificates_certificates` | `[]` | Certificates to request. See [Certificates](#certificates) |
| `acme_certificates_acme_directory` | None | Directory URL of the ACME server. Required with certificates |
| `acme_certificates_account_key_path` | `/etc/ssl/private/acme-account.key` | ACME account key, created if missing |
| `acme_certificates_account_email` | None | Contact address for the ACME account |
| `acme_certificates_terms_agreed` | `false` | Agree to the ACME server's terms of service, which Let's Encrypt requires |
| `acme_certificates_validate_certs` | `true` | Validate the TLS certificate of the ACME server |
| `acme_certificates_remaining_days` | `30` | Renew certificates that expire within this many days |
| `acme_certificates_key_dir` | `/etc/ssl/private` | Default directory for keys |
| `acme_certificates_cert_dir` | `/etc/ssl/certs` | Default directory for certificates |
| `acme_certificates_owner` | `root` | Default owner of keys and certificates |
| `acme_certificates_group` | `ssl-cert` | Default group of keys and certificates |
| `acme_certificates_key_mode` | `0640` | Default mode of keys |
| `acme_certificates_cert_mode` | `0644` | Default mode of certificates |
| `acme_certificates_key_type` | `RSA` | Default key type: `RSA`, `ECC`, `Ed25519` or `Ed448` |
| `acme_certificates_key_size` | `4096` | Default size of RSA keys |
| `acme_certificates_nsupdate_server` | None | DNS server for the challenge records, by address or name. Required with certificates |
| `acme_certificates_nsupdate_port` | `53` | Port of the DNS server |
| `acme_certificates_nsupdate_zone` | None | Zone to update. Looked up from each record name if not set |
| `acme_certificates_nsupdate_key_name` | `ansible` | Name of the TSIG key |
| `acme_certificates_nsupdate_key_secret` | None | Secret of the TSIG key. Required with certificates |
| `acme_certificates_nsupdate_key_algorithm` | `hmac-sha256` | Algorithm of the TSIG key |

## Example playbook

```yaml
- name: Install certificates
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.acme_certificates
      vars:
        acme_certificates_trusted_cas:
          - name: Example Root CA
            certificate: "{{ lookup('ansible.builtin.file', 'files/example-root-ca.crt') }}"
        acme_certificates_acme_directory: https://ca.example.com/acme/acme/directory
        acme_certificates_nsupdate_server: ns1.example.com
        acme_certificates_nsupdate_key_secret: "{{ vaulted_tsig_secret }}"
        acme_certificates_certificates:
          # Written to /etc/ssl/private/<name>.key and /etc/ssl/certs/<name>.crt.
          - common_name: "{{ inventory_hostname }}"
          - common_name: www.example.com
            subject_alt_names:
              - example.com
            key_path: /etc/nginx/tls/www.key
            fullchain_path: /etc/nginx/tls/www.pem
            post_install_commands:
              - systemctl reload nginx
```

## Trusted CAs

Each entry of `acme_certificates_trusted_cas` has these keys:

| Key | Description |
|---|---|
| `name` | Name of the CA. The file is named after it, with unsafe characters replaced by `-` |
| `certificate` | The certificate in PEM format |
| `state` | `present` (default) or `absent`. Removing an entry from the list leaves the CA trusted, so set it to `absent` for one run first |

The CAs are trusted before any certificate is requested, so a private ACME server
with a certificate from one of them can be reached over HTTPS.

## Certificates

Each entry of `acme_certificates_certificates` has these keys. Only `common_name`
is required.

| Key | Default | Description |
|---|---|---|
| `common_name` | | Common name. It is also added as a subject alternative name |
| `subject_alt_names` | `[]` | Other DNS names. Wildcards such as `*.example.com` work |
| `name` | `common_name` | Base name of the default key and certificate files |
| `key_path` | `<acme_certificates_key_dir>/<name>.key` | Private key |
| `cert_path` | `<acme_certificates_cert_dir>/<name>.crt` | Certificate, without the chain |
| `chain_path` | None | Intermediate certificates. Only written if set |
| `fullchain_path` | None | Certificate followed by the intermediates. Only written if set |
| `owner`, `group` | `acme_certificates_owner`, `acme_certificates_group` | Owner and group of the key and certificate files |
| `key_mode`, `cert_mode` | `acme_certificates_key_mode`, `acme_certificates_cert_mode` | Modes of the key and certificate files |
| `key_type`, `key_size`, `key_curve` | `acme_certificates_key_type`, `acme_certificates_key_size`, none | Type of key. `key_curve`, such as `secp256r1`, is required for `ECC` |
| `unifi_keystore` | None | Also install the certificate in a Unifi keystore. See [Unifi Network controller](#unifi-network-controller) |
| `post_install_commands` | `[]` | Shell commands to run, in order, when the key, certificate or keystore changes |

The files can go anywhere, but their directories must exist. The role doesn't create
them, so that it doesn't change the permissions of directories such as
`/etc/ssl/private`.

A certificate is requested when it doesn't exist, when it expires within
`acme_certificates_remaining_days`, when it doesn't match the key, when its names
differ from `common_name` and `subject_alt_names`, or when the `chain_path` or
`fullchain_path` file is missing. The chain files are only written along with a new
certificate, so adding them to an existing certificate requests a new one. Changing the key type or size
replaces the key, so the certificate is requested again too.

`post_install_commands` run after all files of that certificate are in place. They
run as root through the shell, so `systemctl reload nginx` or
`docker restart unifi` work as written. If a command fails, the role stops, and the
commands don't run again on the next run because nothing changes then. Run them by
hand after fixing the problem.

## Unifi Network controller

The Unifi Network application reads its certificate from a Java keystore,
`<data directory>/keystore`, rather than from PEM files. With `unifi_keystore`, the
role writes the key, the certificate and the chain to that keystore. `chain_path` is
required, because the controller has to send the intermediates.

| Key | Default | Description |
|---|---|---|
| `path` | | The keystore. `/var/lib/unifi/keystore` for the Debian package, or `data/keystore` in the volume of a container |
| `owner`, `group` | None | Owner and group of the keystore. The controller must be able to read it |
| `mode` | `0640` | Mode of the keystore |
| `alias` | `unifi` | Alias of the key in the keystore |
| `password` | `aircontrolenterprise` | Password of the keystore, which is the same in every installation |
| `backup` | `true` | Keep a copy of the old keystore when it is replaced |

The controller reads the keystore at startup, so restart it in `post_install_commands`.
For the Debian package:

```yaml
acme_certificates_certificates:
  - common_name: unifi.example.com
    chain_path: /etc/ssl/certs/unifi.example.com.chain.crt
    unifi_keystore:
      path: /var/lib/unifi/keystore
      owner: unifi
      group: unifi
    post_install_commands:
      - systemctl restart unifi
```

For a container, such as `jacobalberty/unifi`, write the keystore in the data volume
on the host, owned by the user the container runs as:

```yaml
acme_certificates_certificates:
  - common_name: unifi.example.com
    chain_path: /etc/ssl/certs/unifi.example.com.chain.crt
    unifi_keystore:
      path: /var/lib/docker/volumes/unifi_unifi/_data/data/keystore
      owner: "999"
      group: "999"
    post_install_commands:
      - docker restart unifi
```

The `jacobalberty/unifi` image can also import PEM files from its `cert` directory at
startup, replacing the keystore. If you use that instead, write `cert.pem`,
`privkey.pem` and `chain.pem` there with `cert_path`, `key_path` and `chain_path`, and
leave out `unifi_keystore`. Don't use both, or the image may replace the keystore the
role wrote with an older certificate.

## Behaviour

- **Idempotent:** yes. Nothing is requested while the certificates are valid and
  match their keys and names.
- **Account key:** the role creates one ACME account key per host, separate from
  the certificate keys.
- **Check mode:** partly. Package installation is skipped, so the crypto modules
  only work in check mode if `python3-cryptography` is already installed. Keys and
  certificates that would be created or renewed are reported as changes, and nothing
  is requested from the ACME server. On a new host, where the key directory
  doesn't exist yet, the certificates are skipped with a message.
- **DNS records:** the challenge records are removed even if the request fails.
- **Trust store:** updated only when a CA file changes. If the update command fails,
  run it by hand, because the next run won't run it again.
- **Secrets:** the TSIG secret and the keystore password aren't logged.
- **Rollback:** none. The Unifi keystore is backed up by default.

## License

Apache-2.0

## Author

pypb
