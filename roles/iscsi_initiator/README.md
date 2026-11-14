# pypb.homelab.iscsi_initiator

Sets up open-iscsi, and logs in to iSCSI targets now and at every boot:

- Installs open-iscsi, sets the initiator name and the settings in `iscsid.conf`,
  and enables `iscsid` and `open-iscsi`, which logs in at boot.
- Discovers each target that has no node record yet, applies the `node.*` settings
  from `iscsid.conf` to its record, and logs in.
- Optionally gives the disks of chosen SCSI vendors a longer command timeout, so
  that I/O waits for a target that restarts rather than failing.
- Runs multipathd, or stops and disables it.

It doesn't create file systems or mount anything. For a file system that several
hosts share, use the [`pypb.homelab.ocfs2`](../ocfs2/README.md) role after this one.
For any other, use `ansible.posix.mount` with the `_netdev` option.

## Requirements

- Root access on the target, for example through `become`
- The `community.general` collection

## Supported platforms

| Platform | Versions | Tested |
|---|---|---|
| Debian | 13 (trixie) | Molecule, with a node record but without discovery or logging in: containers can't load `iscsi_tcp` |
| Ubuntu | 24.04 (noble), 26.04 (resolute), including Raspberry Pi | Molecule, as for Debian. On a live cluster with a Synology target |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `iscsi_initiator_packages` | `[open-iscsi, lsscsi]` | Packages to install. `multipath-tools` is added when `iscsi_initiator_multipathd` is true |
| `iscsi_initiator_name` | Unset: `<prefix>:01:<short host name>` | Initiator name. The prefix is the distribution's, as the package uses. An empty string keeps the generated name |
| `iscsi_initiator_iscsid_settings` | Replacement timeout 600 s, 20 login retries | Settings for `iscsid.conf`. The `node.*` ones are also applied to the targets' records |
| `iscsi_initiator_start` | `true` | Start iscsid, and multipathd if enabled, and log in. False enables them without starting them and leaves logins alone, for containers and images |
| `iscsi_initiator_targets` | `[]` | Targets, each with `target`, `portal` and optionally `port` (`3260`), `login` (false logs out), `auto_node_startup` and `auto_portal_startup` (all `true`) |
| `iscsi_initiator_device_vendors` | `[]` | SCSI vendors whose disks get the timeout below, such as `LIO-ORG` or `SYNOLOGY` |
| `iscsi_initiator_device_timeout` | `600` | SCSI command timeout in seconds for those disks |
| `iscsi_initiator_multipathd` | `false` | Run multipathd. False stops and disables it if it's installed |

## Example playbook

```yaml
- name: Log in to the storage target
  hosts: storage_clients
  become: true
  roles:
    - role: pypb.homelab.iscsi_initiator
      vars:
        iscsi_initiator_device_vendors: [LIO-ORG]
        iscsi_initiator_targets:
          - target: iqn.2003-01.org.linux-iscsi.nas.x8664:sn.0123456789ab
            portal: 192.0.2.30
```

## Things to know

- **Discovery:** the role only discovers a target that has no node record, because
  discovery resets the records it finds, such as whether they start at boot. To
  pick up new portals of a known target, run `iscsiadm -m discovery -t st -p <portal>`
  by hand.
- **Settings:** changes to the `node.*` settings reach a session at its next login,
  so at the next boot.
- **Initiator name:** the target's access list must allow it. Changing it restarts
  iscsid, which doesn't end existing sessions, and new logins use the new name.
- **multipathd:** with one path to each disk, multipathd claims the disks and adds
  nothing, so the default stops it. Set `iscsi_initiator_multipathd: true` with
  several paths, and mount the `/dev/mapper` devices.
- **Disk timeout:** the udev rule applies to disks as they're added, so at the next
  login or boot.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes. A target that hasn't been discovered yet is skipped.
- **Applied right away:** packages, services, logins and the initiator name.
- **Applied at the next login:** the `node.*` settings and the disk timeout.
- **Replaced files:** the udev rule. `iscsid.conf` and `initiatorname.iscsi` are
  edited line by line.
- **Rollback:** none. The role doesn't log out of targets that leave the list.

## License

Apache-2.0

## Author

pypb
