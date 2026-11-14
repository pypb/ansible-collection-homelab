# pypb.homelab.ocfs2

Sets up [OCFS2](https://docs.kernel.org/filesystems/ocfs2.html), the shared cluster
file system, with the o2cb cluster stack and local heartbeat. Every node can then
mount the same shared block device, such as an iSCSI LUN, at the same time.

The role:

1. Installs `ocfs2-tools`, and makes sure the running kernel and the newest
   installed kernel, which the next boot uses, have the `ocfs2` module. Debian's
   kernels include it. On Ubuntu, the generic kernels have it in their
   `linux-modules-extra` package, which the role installs when it's missing. For
   future kernels, keep the flavour's metapackage, such as `linux-image-generic`,
   installed, because it pulls in the extra modules. The role fails if a kernel
   still has no module.
2. Writes `/etc/ocfs2/cluster.conf` and the settings in `/etc/default/o2cb`.
3. Enables and starts the `o2cb` and `ocfs2` services. It never restarts them.
4. Writes `ocfs2_sysctl` to `/etc/sysctl.d/95-ocfs2.conf`. OCFS2 fences a node that
   loses contact with the others by panicking it, and these make it reboot rather
   than hang.
5. Adds the file systems to fstab, with `x-systemd.after=o2cb.service`, so that they
   mount after the cluster stack starts and unmount before it stops. Then it starts
   their automount units, or their mount units without `noauto`.

The play fails before changing anything if the node's host name (`uname -n`) isn't in
`ocfs2_nodes`, because o2cb wouldn't join the cluster.

It doesn't create file systems, log in to iSCSI targets or open the firewall.

## Requirements

- Root access on the target, for example through `become`
- A shared block device that every node sees, for example an iSCSI disk from the
  [`pypb.homelab.iscsi_initiator`](../iscsi_initiator/README.md) role
- The `ansible.posix` and `community.general` collections

## Supported platforms

| Platform | Versions | Tested |
|---|---|---|
| Debian | 13 (trixie) | Molecule, configuration only: containers can't load the kernel module |
| Ubuntu | 24.04 (noble), 26.04 (resolute), including Raspberry Pi | Molecule, configuration only. On a live cluster with generic and Raspberry Pi kernels |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `ocfs2_cluster_name` | None | Name of the o2cb cluster, at most 16 letters, digits or underscores. Required |
| `ocfs2_nodes` | `[]` | Every node of the cluster, each with `name`, `number`, `ip_address` and optionally `ip_port` (`7777`). Use the same list on every node. Required |
| `ocfs2_start` | `true` | Start the cluster stack and the mounts, and check the kernel module. False only writes the configuration |
| `ocfs2_heartbeat_threshold` | `31` | A node is declared dead after (threshold - 1) x 2 seconds without a disk heartbeat |
| `ocfs2_idle_timeout_ms` | `30000` | Time before an idle connection to another node is considered down |
| `ocfs2_keepalive_delay_ms` | `2000` | Time before a keepalive is sent on an idle connection |
| `ocfs2_reconnect_delay_ms` | `2000` | Time between attempts to reconnect to another node |
| `ocfs2_sysctl` | `{kernel.panic: 10, kernel.panic_on_oops: 1}` | Settings for `/etc/sysctl.d/95-ocfs2.conf`, so that a fenced node reboots |
| `ocfs2_mounts` | `[]` | File systems to mount, each with `path`, `src` and optionally `opts` |
| `ocfs2_mount_opts` | `_netdev,noauto,x-systemd.automount,...` | Mount options for entries without `opts` |

## Example playbook

```yaml
- name: Set up OCFS2
  hosts: ocfs2_nodes
  become: true
  serial: 1
  roles:
    - role: pypb.homelab.ocfs2
      vars:
        ocfs2_cluster_name: shared
        ocfs2_nodes:
          - {name: node1, number: 1, ip_address: 192.0.2.11}
          - {name: node2, number: 2, ip_address: 192.0.2.12}
          - {name: node3, number: 3, ip_address: 192.0.2.13}
        ocfs2_mounts:
          - path: /srv/shared
            src: UUID=00000000-0000-0000-0000-000000000000
```

On k3s nodes, the [`pypb.homelab.ubuntu_k3s_node`](../../playbooks/ubuntu_k3s_node.yml)
playbook runs this role when `ubuntu_k3s_node_ocfs2` is true.

## Things to know

- **Formatting:** the role doesn't create file systems. Format each device once,
  from one node, with room for every node that will mount it:
  `mkfs.ocfs2 -N 4 -L shared /dev/sdX`.
- **Firewall:** the nodes reach each other on TCP `ip_port`, 7777 by default. The
  role doesn't open it.
- **Changes:** o2cb only reads its configuration when it starts, and it can't stop
  while a file system is mounted. So changes to the nodes or timeouts take effect
  at the next reboot, and the role prints a message when there are any. Reboot the
  nodes one at a time. To add a node, add it to the list, reboot the existing nodes,
  then start the new one. Never change the number of an existing node.
- **fsck:** the fstab entries have pass number 0, so they aren't checked at boot. A
  file system that other nodes have mounted can't be checked. Run `fsck.ocfs2` by
  hand, with the file system unmounted on every node.
- **Taking over entries:** an existing fstab entry for the same mount point is
  replaced in place. Its unit keeps running, and the new options take effect at
  the next mount.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes.
- **Applied right away:** packages, the sysctl settings, the services and the mounts.
- **Applied when o2cb next starts:** changes to the cluster configuration and
  timeouts. The role doesn't restart o2cb.
- **Replaced files:** `/etc/ocfs2/cluster.conf` and `/etc/sysctl.d/95-ocfs2.conf`
  are replaced in full. `/etc/default/o2cb` and fstab are edited line by line.
- **Rollback:** none.

## License

Apache-2.0

## Author

pypb
