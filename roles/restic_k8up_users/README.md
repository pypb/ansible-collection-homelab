# pypb.homelab.restic_k8up_users

Gives the [k8up](https://k8up.io) backup Schedules of a cluster their own logins
on a containerised rest-server:

- Lists the cluster's Schedules with kubectl. Each Schedule whose rest backend
  is on `restic_k8up_users_server_host` gets a user named by the first path
  segment of its repository URL, as rest-server's `--private-repos` requires.
- When the Schedule's credential Secret is missing, or holds another username
  because the URL changed, sets a new password with
  [`pypb.homelab.restic_server_users`](../restic_server_users/README.md) and
  writes the Secret in the Schedule's namespace.
- Leaves Secrets that match alone, so a rerun changes nothing.
- Reports users that start with `restic_k8up_users_report_prefix` and have no
  Schedule. They aren't removed, since their repositories may still hold backups.

The Schedule's `userSecretRef` and `passwordSecretReg` must name the same Secret.
The repository password stays whatever k8up is given, for example its global
one.

## Requirements

- ansible-core 2.21 or newer
- kubectl access to the cluster from the host the role runs on
- A rest-server container that `pypb.homelab.restic_server_users` can reach

## Role variables

| Variable | Default | Description |
|---|---|---|
| `restic_k8up_users_kubectl` | `[k3s, kubectl]` | The command that runs kubectl, as a list |
| `restic_k8up_users_server_host` | The host of `restic_backup_repo_url` | The rest-server's host name |
| `restic_k8up_users_report_prefix` | `""` | Report users with this prefix and no Schedule. Empty reports nothing |

The rest-server's host and container are set with the variables of
`pypb.homelab.restic_server_users`: `restic_server_users_host` and
`restic_server_users_container`, which default to the collection-wide
`restic_server_hostname` and `restic_server_container`.

## Example playbook

```yaml
- name: Give the cluster's k8up Schedules rest-server logins
  hosts: k3s_servers[0]
  become: true
  roles:
    - role: pypb.homelab.restic_k8up_users
      vars:
        restic_k8up_users_server_host: rest.example.org
        restic_k8up_users_report_prefix: k8up-
        restic_server_users_host: nas.example.org
```

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no. A password is set on the rest-server before its Secret is
  written, so a failure in between leaves a Secret that a rerun replaces.
- **Check mode:** yes. It reports the users that would get a new password, but
  doesn't set passwords or write Secrets.
- **Applied right away:** yes. rest-server reloads its logins, and k8up reads the
  Secret at its next backup.
- **Replaced files:** none. Secrets of stale users are replaced.
- **Rollback:** none.

## License

Apache-2.0

## Author

pypb
