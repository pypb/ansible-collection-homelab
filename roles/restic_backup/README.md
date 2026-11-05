# pypb.homelab.restic_backup

Installs [restic](https://restic.net/) and
[resticprofile](https://creativeprojects.github.io/resticprofile/), configures
backup profiles, initializes the repository and optionally schedules the profiles
with systemd.

## Requirements

- Root access on the target, for example through `become`
- systemd, if using scheduling
- Internet access to GitHub, unless the download URLs are overridden

## Supported platforms

| Platform | Versions | Tested |
|---|---|---|
| Debian | 13 (trixie) | Molecule |
| Ubuntu | 24.04 (noble), 26.04 (resolute) | Molecule |
| Raspberry Pi OS | Trixie-based, 64-bit and 32-bit | Download URLs only |

Supported architectures are `x86_64`, `aarch64`, `armv8l`, `armv7l` and `armv6l`.
The role doesn't refuse to run on other Linux distributions, but it only installs
its required packages on the Debian family.

## Role variables

Every variable is described in [`meta/argument_specs.yml`](meta/argument_specs.yml),
with defaults in [`defaults/main.yml`](defaults/main.yml). The main ones are:

| Variable | Default | Description |
|---|---|---|
| `restic_backup_enable` | `false` | Master switch. The role does nothing unless this is true |
| `restic_backup_install` | `true` | Install the binaries. Disable if they are already installed |
| `restic_backup_password` | None | Repository password. Required when enabled |
| `restic_backup_repo_url` | `/var/tmp/restic_backup` | Repository location |
| `restic_backup_env_list` | Undefined | `NAME=value` strings for resticprofile, such as rest-server credentials. The env file is left alone when undefined |
| `restic_backup_schedule_enable` | `false` | Schedule profiles if true, and remove existing schedules if false |
| `restic_backup_include`, `restic_backup_exclude` | See defaults | Paths to back up and exclude. Each has `_group` and `_host` variants that are added to it |
| `restic_backup_profiles`, `restic_backup_groups` | See defaults | Profiles and groups. Each has `_group` and `_host` variants that are merged into it |
| `restic_backup_restic_version` | `0.19.1` | restic version |
| `restic_backup_resticprofile_version` | `0.33.1` | resticprofile version |

## Tags

| Tag | Runs |
|---|---|
| `restic_backup_install` | Package and binary installation |
| `restic_backup_config` | Configuration files |
| `restic_backup_init` | Repository initialization and scheduling |

## Example playbook

```yaml
- name: Configure backups
  hosts: backup_clients
  become: true
  roles:
    - role: pypb.homelab.restic_backup
      vars:
        restic_backup_enable: true
        restic_backup_password: "{{ vaulted_restic_password }}"
        restic_backup_repo_url: "rest:https://backup.example.com/{{ inventory_hostname_short }}"
        restic_backup_env_list:
          - "RESTIC_REST_USERNAME={{ inventory_hostname_short }}"
          - "RESTIC_REST_PASSWORD={{ vaulted_rest_password }}"
        restic_backup_schedule_enable: true
```

To create rest-server users as well, see the
[`pypb.homelab.restic_backup` playbook](../../playbooks/restic_backup.yml).

## Behaviour

- **Idempotent:** yes, when `restic_backup_scheduler` is `systemd` and at least
  one profile has a schedule. Otherwise, scheduling runs and reports a change on
  every run.
- **Atomic:** no.
- **Check mode:** partly. Configuration files are checked, but package and binary
  installation, repository initialization and scheduling are skipped, and aren't
  reported as pending changes.
- **Repository errors:** the role only initializes a repository if restic reports
  that it doesn't exist. Other errors, such as a failed login, fail the role.
- **Replaced files:** `profiles.yaml`, `password` and `env` are replaced in full.
  `profiles.yaml` is backed up first. `password` and `env` aren't, so that old
  credentials aren't left behind.
- **Rollback:** restore `profiles.yaml` from its backup. The role never removes
  repository data or snapshots.

## License

Apache-2.0

## Author

pypb
