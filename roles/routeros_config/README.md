# pypb.homelab.routeros_config

Configures MikroTik RouterOS devices from inventory data, in numbered steps,
through the RouterOS API:

- Takes the steps from every variable whose name starts with
  `routeros_config_steps_`, so that they can be spread over `group_vars` and
  `host_vars` files, and merges them, joining the operations of a step.
- Runs the steps in the order of their number, and the operations of a step in
  the order they are listed, with `community.routeros.api_modify`,
  `api_find_and_modify` or, where there is no API path, `command` over SSH.
- Describes each switch port once, with its comment, PoE, bridge, PVID and
  tagged VLANs, and works out the bridge, ethernet, PoE, bridge port and bridge
  VLAN entries from it.
- Checks the steps first, failing on unknown keys and on conflicts, rather than
  skipping what it doesn't recognise.
- Optionally saves `/export` on the controller before changing anything, adds
  and removes the SSH keys of the device's users, and saves an encrypted backup
  on the device after something changed.

Supports check mode and diff, except for `command` operations and SSH keys,
which are skipped.

## Requirements

- ansible-core 2.21 or newer
- `community.routeros` and `community.general` on the controller, and the
  `librouteros` Python library
- RouterOS 7, with the API service (`api-ssl` by default) reachable from the
  controller
- For `command` operations and the export, SSH access as `ansible_user`. Adding
  `+cet1024w` to the user name turns off colours and wraps lines at 1024
  characters

## Steps

A step's name is a number, an underscore and a word, such as `0100_system`.
Steps are sorted by the number, so `900_x` runs before `1000_y`. Each step is a
list of operations:

| Keys | Module | Options |
|---|---|---|
| `path`, `data` | `api_modify` | `ensure_order`, `handle_absent_entries`, `handle_entries_content`, `handle_read_only`, `handle_write_only` |
| `path`, `find`, `values` | `api_find_and_modify` | `allow_no_matches`, `ignore_builtin`, `ignore_dynamic`, `require_matches_min`, `require_matches_max` |
| `command` | `command` | |

The variables are merged in the order of their names, so the operations that
`routeros_config_steps_ap` adds to a step come before those of
`routeros_config_steps_global`. Within a step, the api_modify operations on the
same path are joined into one call, with the entries of all of them. Put
operations that depend on each other in different steps.

`handle_absent_entries` is `ignore` by default, so entries on the device that
aren't in the data are left alone, and `data: []` does nothing. Set it to
`remove` on a path once its data has all the entries the device should have. A
path that removes absent entries may only be set in one step.

## Ports and bridges

```yaml
routeros_config_bridges:
  bridge1:
    vlan_filtering: true
    tagged_vlans: [1, 10]     # the bridge itself
    settings:
      protocol-mode: rstp

routeros_config_ports:
  ether1:
    comment: uplink
    bridge: bridge1
    tagged: [1, 10-20]        # untagged in its PVID, 1, unless it is tagged in it
  ether2:
    comment: printer
    bridge: bridge1
    pvid: 13
    frame_types: admit-only-untagged-and-priority-tagged
    poe: {poe-out: "off"}
  ether3:                     # a bond member: only its comment and PoE
    comment: nas port 1
  bond1:
    bridge: bridge1
    tagged: [12]
```

List the ports in the order RouterOS lists the interfaces, ethernet ports first
and bonds after them. The members of a bridge VLAN are written in that order,
with the bridge itself first, and api_modify compares them as text with what
the device reads back. `cpu_interface` sets the name the bridge itself has in
those lists, the bridge's own name by default.

The entries go to the steps `0200_bridge`, `0200_ethernet` (`interface
ethernet` and `interface ethernet poe`), `0220_bridge_port` and
`0230_bridge_vlan`, which `routeros_config_port_steps` can change. A bridge gets
one VLAN entry per VLAN, or with `group_vlans: true` one for each set of VLANs
with the same members, such as `10-11,13-14`. Bonds, VLAN interfaces and
anything else stay in ordinary steps, before or after these.

## Role variables

| Variable | Default | Description |
|---|---|---|
| `routeros_config_steps_*` | | Steps, merged from every variable with this prefix |
| `routeros_config_ports` | `{}` | Ports, as above |
| `routeros_config_bridges` | `{}` | Bridges, as above |
| `routeros_config_port_steps` | `{}` | The steps for the `bridge`, `ethernet`, `port` and `vlan` entries |
| `routeros_config_ethernet_pattern` | `^(ether\|sfp\|qsfp\|combo)\d` | Ports that get an `interface ethernet` entry |
| `routeros_config_handle_absent_entries_default` | `ignore` | `handle_absent_entries` for operations that don't set it |
| `routeros_config_api_hostname` | `{{ inventory_hostname }}` | The device's API address |
| `routeros_config_api_username` | `ansible_user` without a `+` suffix | The API user |
| `routeros_config_api_password` | | The API password. Required |
| `routeros_config_api_port` | `0` | The API port, 0 for the default |
| `routeros_config_api_tls` | `true` | Use the API over TLS |
| `routeros_config_api_validate_certs` | `true` | Check the device's certificate |
| `routeros_config_api_validate_cert_hostname` | `true` | Check that the certificate matches the host name |
| `routeros_config_api_ca_path` | `""` | A CA certificate file for the check |
| `routeros_config_api_timeout` | `10` | The API timeout, in seconds |
| `routeros_config_ssh_keys` | `[]` | SSH keys, each with `user`, `key` and an optional `comment` |
| `routeros_config_ssh_keys_exclusive` | `false` | Remove the SSH keys, of any user, that aren't listed |
| `routeros_config_export_dir` | `""` | A directory on the controller for `<inventory_hostname>.rsc`. Empty for no export |
| `routeros_config_export_options` | `terse` | Options for `/export`, such as `terse show-sensitive` |
| `routeros_config_device_backup` | `false` | Save an encrypted backup on the device after a change |
| `routeros_config_device_backup_name` | `ansible` | The backup's name |
| `routeros_config_device_backup_password` | `""` | The backup's password. Required for a backup |

The `plan` entry point only works out the plan, without connecting to the
device, and sets `routeros_config_plan` to the list of module calls in order:

```yaml
- name: Show what would be applied, in order
  hosts: routeros
  gather_facts: false
  tasks:
    - name: Work out the plan
      ansible.builtin.include_role:
        name: pypb.homelab.routeros_config
        tasks_from: plan

    - name: Show it
      ansible.builtin.debug:
        var: routeros_config_plan
```

## Example inventory

`group_vars/routeros.yml`:

```yaml
ansible_connection: local
ansible_user: ansible+cet1024w
routeros_config_api_password: "{{ vault_routeros_password }}"
routeros_config_export_dir: "{{ inventory_dir }}/../exports"

routeros_config_steps_global:
  "0100_system":
    - path: system identity
      data:
        - name: "{{ inventory_hostname_short }}"
    - path: system clock
      data:
        - time-zone-name: Europe/Stockholm
  "0300_ip":
    - path: ip dns
      data:
        - servers: 192.0.2.53
    - path: ip service
      find: {name: telnet}
      values: {disabled: true}
  "0900_tool":
    - path: tool mac-server
      data:
        - allowed-interface-list: none
```

`host_vars/ap1.example.com.yml`, which adds to `0100_system` without replacing
the global operations:

```yaml
routeros_config_steps_ap1:
  "0100_system":
    - path: system leds settings
      data:
        - all-leds-off: after-1min
```

## Example playbook

```yaml
- name: Configure RouterOS devices
  hosts: routeros
  gather_facts: false
  roles:
    - role: pypb.homelab.routeros_config
```

Or use the `pypb.homelab.routeros` playbook. Run it with `--check --diff`
first: a step's diff shows what would be added, changed and removed.
