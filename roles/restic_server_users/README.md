# pypb.homelab.restic_server_users

Manages user logins on a [restic rest-server](https://github.com/restic/rest-server)
running in a container. It does not deploy rest-server itself.

## Requirements

- Any Linux host running the rest-server container, using the official
  `restic/rest-server` image or one that provides `htpasswd`, `cut` and `kill`
  and runs rest-server as PID 1.
- A Docker-compatible API on that host, and the Python libraries
  [`community.docker`](https://docs.ansible.com/ansible/latest/collections/community/docker/)
  needs for that host's Python interpreter.
- Permission to use the Docker API on that host, for example through `become`.

The role installs nothing on the host. The `community.docker` collection is a
dependency of `pypb.homelab`, so it is installed along with it.

## Role variables

| Variable | Default | Description |
|---|---|---|
| `restic_server_users_host` | `restic_server_hostname`, or the current host | Host running the container. Tasks are delegated to it |
| `restic_server_users_container` | `restic_server_container`, or `restic-server` | Container name |
| `restic_server_users_htpasswd_path` | `/data/.htpasswd` | htpasswd path inside the container |
| `restic_server_users_password_length` | `32` | Length of generated passwords |
| `restic_server_users_list` | `[]` | Users to manage. Users that are not listed are left alone |

Each entry in `restic_server_users_list` takes:

| Key | Default | Description |
|---|---|---|
| `name` | Required | Username, without colons or whitespace |
| `password` | Generated | Password to set |
| `state` | `present` | `absent` removes the login. Repository data stays on disk |
| `update_password` | `on_create` | `always` sets the password on every run |

`restic_server_hostname` and `restic_server_container` are collection-wide
variables, so one inventory value can serve every role that needs them.

## Returned facts

`restic_server_users_generated` is a dictionary of the passwords generated during
this run, keyed by username. It is empty if none were generated. **Store these
passwords straight away**, because they can't be recovered later. They appear in
no other output.

In check mode, passwords are generated but not applied.

## Example playbook

```yaml
- name: Manage rest-server users
  hosts: backup_clients
  tasks:
    - name: Ensure this host has a rest-server user
      ansible.builtin.include_role:
        name: pypb.homelab.restic_server_users
      vars:
        restic_server_users_host: backup.example.com
        restic_server_users_list:
          - name: "{{ inventory_hostname_short }}"

    - name: Show whether a password was generated
      ansible.builtin.debug:
        msg: "{{ inventory_hostname_short in restic_server_users_generated }}"
```

The [`pypb.homelab.restic_backup` playbook](../../playbooks/restic_backup.yml)
shows how to pass generated credentials on to the `restic_backup` role.

## Behaviour

- **Idempotent:** yes, except for `update_password: always`, which sets the
  password and reports a change on every run.
- **Atomic:** no. Each user is changed separately.
- **Check mode:** supported. Existing users are read, and nothing is changed.
- **Rollback:** none. A removed login can be recreated, but a replaced password
  can't be restored.
- **Concurrency:** writes are throttled to one host at a time.
- **Reloading:** after a change, the role sends `SIGHUP` to PID 1 in the container
  so that rest-server picks it up immediately.

## License

Apache-2.0

## Author

pypb
