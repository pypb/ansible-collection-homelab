# pypb.homelab.docker_traefik

Runs Traefik with Docker Compose:

- Writes a Compose project for Traefik in `/srv/docker/traefik`, with secrets in
  a `.env` that only root can read.
- Writes the static configuration, and restarts Traefik when it changes.
- Writes files of dynamic configuration, which Traefik reloads by itself, and
  removes the ones that aren't listed.
- Starts the project, pulling the image when it's missing, and removes the
  containers of services that are no longer in it.
- Rotates the log files in the `logs` volume with the host's logrotate, and
  sends Traefik `USR1` afterwards, which makes it reopen them.

The project has an internal network, `reverse_proxy`, that containers of other
projects can join to be reached by Traefik. With the Docker provider, they are
only exposed when they have the label `traefik.enable=true`.

## Requirements

- ansible-core 2.21 or newer
- Docker with its Compose plugin, for example from `geerlingguy.docker`

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04

## Role variables

| Variable | Default | Description |
|---|---|---|
| `docker_traefik_dir` | `/srv/docker/traefik` | The project's directory, whose name is the project's name |
| `docker_traefik_group` | `docker` | The group that owns the directory and the configuration, other than `.env` |
| `docker_traefik_image` | `traefik:v3.7` | The Traefik image |
| `docker_traefik_ports` | `["80:80", "443:443"]` | Published ports, in Compose's short syntax |
| `docker_traefik_volumes` | `[]` | More volumes, in Compose's short syntax, relative to the project's directory |
| `docker_traefik_environment` | `{}` | Environment variables, in the Compose file |
| `docker_traefik_secret_environment` | `{}` | Environment variables for secrets, in `.env` |
| `docker_traefik_static_config` | The `web` and `websecure` entry points, and the Docker provider | The static configuration |
| `docker_traefik_static_config_extra` | `{}` | Merged recursively over `docker_traefik_static_config` |
| `docker_traefik_dynamic_config` | `{}` | Files of dynamic configuration, as a dict of file name and content |
| `docker_traefik_logrotate` | `true` | Rotate the `.log` files in the `logs` volume. When false, the role's logrotate configuration is removed |
| `docker_traefik_logrotate_options` | `daily`, `rotate 14`, `compress`, `delaycompress`, `missingok`, `notifempty` | Directives of the logrotate section, one per item |

The role always sets `providers.file` in the static configuration, to read the
dynamic configuration from `/etc/traefik/dynamic` in the container.

The container always has the host's time zone and CAs, the configuration in
`/etc/traefik`, the Docker socket, and the `data` and `logs` volumes in `/data`
and `/logs`. Put ACME storage in `/data`, and log files in `/logs`.

## Example playbook

```yaml
- name: Run Traefik with Let's Encrypt certificates
  hosts: proxies
  become: true
  roles:
    - role: pypb.homelab.docker_traefik
      vars:
        docker_traefik_secret_environment:
          DESEC_TOKEN: "{{ vault_desec_token }}"
        docker_traefik_static_config_extra:
          certificatesResolvers:
            letsencrypt:
              acme:
                email: hostmaster@example.org
                storage: /data/acme.json
                dnsChallenge:
                  provider: desec
        docker_traefik_dynamic_config:
          middlewares.yml:
            http:
              middlewares:
                secheaders:
                  headers:
                    frameDeny: true
                    stsSeconds: 31536000
```

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no. A broken static configuration stops Traefik when it restarts.
- **Check mode:** yes. On a new host, Traefik isn't started, and logrotate
  isn't configured, since the `logs` volume doesn't exist yet.
- **Applied right away:** Traefik restarts when the static configuration
  changes, and the container is recreated when the Compose file or `.env`
  changes. It reloads the dynamic configuration by itself.
- **Replaced files:** `docker-compose.yml`, `.env` and `conf/traefik.yml` in the
  project's directory, everything in `conf/dynamic`, and
  `/etc/logrotate.d/<project>-traefik`.
- **Rollback:** none.

## License

Apache-2.0

## Author

pypb
