# pypb.homelab.users

Manages local groups and accounts on a server:

- Creates groups and accounts, with their user and group IDs, groups, shell and
  password hash.
- Sets the mode of their home directories, `0700` by default.
- Writes their authorized SSH keys, optionally removing keys that aren't listed.
- Deletes accounts and groups, such as `pi` or an image's bootstrap account.

The account Ansible logs in as is an account like any other, so this role also
creates it on a new server. See [Bootstrapping](#bootstrapping).

## Requirements

- ansible-core 2.21 or newer
- `ansible.posix`, for the SSH keys

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04, including on a Raspberry Pi

## Role variables

| Variable | Default | Description |
|---|---|---|
| `users_groups` | `[]` | Groups to create, with `name` and optional `gid` and `system` |
| `users_accounts` | `[]` | Accounts to create. See below |
| `users_update_password` | `on_create` | When to set passwords: `on_create` or `always` |
| `users_home_mode` | `"0700"` | Mode of the home directories |
| `users_removed_accounts` | `[]` | Accounts to delete |
| `users_removed_groups` | `[]` | Groups to delete |
| `users_remove_home` | `false` | Also delete the deleted accounts' home directories |

Each entry in `users_accounts` has a `name`, and optionally:

| Key | Description |
|---|---|
| `uid` | User ID |
| `group` | Primary group, which must exist. Without it, a group of the same name is created |
| `groups` | Other groups. They're added to the ones the account already has |
| `comment` | Full name or description |
| `shell` | Login shell |
| `password` | Password hash, such as from `mkpasswd -m yescrypt`. Keep it in a vault |
| `update_password` | `always` or `on_create`, overriding `users_update_password` |
| `system` | Create a system account |
| `authorized_keys` | Public SSH keys that can log in as it |
| `authorized_keys_exclusive` | Remove the keys in its `authorized_keys` that aren't listed |

## Example playbook

```yaml
- name: Manage accounts
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.users
      vars:
        users_groups:
          - {name: ansible, gid: 2000}
        users_accounts:
          - name: ansible
            uid: 2000
            group: ansible
            groups: [sudo]
            comment: Ansible
            shell: /bin/sh
            password: "{{ vault_ansible_password_hash }}"
            update_password: always
            authorized_keys:
              - ssh-ed25519 AAAA... ansible@controller
          - name: alice
            groups: [adm, sudo]
            shell: /bin/bash
            password: "{{ vault_alice_password_hash }}"
            authorized_keys:
              - ssh-ed25519 AAAA... alice@laptop
        users_removed_accounts: [pi, bootstrap]
```

## Bootstrapping

Run the role first, before roles such as an SSH server role that limit who can
log in, so that the accounts and their keys exist by then.

On a new server, run it once as the account the image comes with, for example
`ansible-playbook -u bootstrap`. That creates the account Ansible uses from then
on. The role never deletes the account Ansible is logged in as, also when that
account is in `users_removed_accounts`. It says so instead, and the next run,
as the new account, deletes it.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes. The SSH keys of accounts the run would create are skipped.
- **Kept as they are:** groups an account has that aren't listed, other keys in
  `authorized_keys` unless `authorized_keys_exclusive` is true, passwords of
  existing accounts with `on_create`, and the files in home directories.
- **Rollback:** none. Deleted accounts and groups have to be created again.

## License

Apache-2.0

## Author

pypb
