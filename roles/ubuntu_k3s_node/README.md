# pypb.homelab.ubuntu_k3s_node

Prepares an Ubuntu server as a minimal k3s node. It strips the packages and units
that a node doesn't need, and sets up what k3s and its storage need around it:

- Purges packages that conflict with k3s, such as Docker and ufw, and packages a
  node doesn't need, such as snapd, cloud-init and apport. Masks units you list.
- Sets sysctl settings and blacklists unused kernel modules.
- Optionally prepares the node for [Cilium](#cilium): its kernel modules and its
  rp_filter override.
- Optionally sets up [OCFS2](#ocfs2), the shared cluster file system: the kernel
  module, the o2cb cluster stack, fencing and the mounts.
- Installs the NFS client, configures `/etc/nfsmount.conf`, and runs cachefilesd.
- Writes a `resolv.conf` for k3s to give to pods.
- Adds watchdogs that reboot the node when a mount, such as an iSCSI volume, is missing.
- On servers, writes the Pod Security Admission configuration and audit policy
  that k3s reads.

It doesn't install, configure or restart k3s. Use a k3s role for that, and point
its options at the files this role writes.

## Requirements

- Root access on the target, for example through `become`

## Supported platforms

| Platform | Versions | Tested |
|---|---|---|
| Ubuntu | 24.04 (noble), 26.04 (resolute), including Raspberry Pi | Molecule, without kernel modules, cachefilesd, a running OCFS2 cluster or a reboot |

## Role variables

| Variable | Default | Description |
|---|---|---|
| `ubuntu_k3s_node_server` | `false` | Write the PSA configuration and audit policy for a k3s server |
| `ubuntu_k3s_node_data_dir` | `/var/lib/rancher/k3s` | k3s data directory. The server files go in its `server` subdirectory |
| `ubuntu_k3s_node_packages` | `[nfs-common]` | Packages to install |
| `ubuntu_k3s_node_conflicting_packages` | Docker, `prometheus-node-exporter`, `ufw` | Packages that conflict with k3s, or that the cluster runs itself. Purged |
| `ubuntu_k3s_node_unneeded_packages` | See [Removed packages](#removed-packages) | Packages a node doesn't need. Purged |
| `ubuntu_k3s_node_masked_units` | `[]` | Units to stop and mask, such as `thermald.service` |
| `ubuntu_k3s_node_sysctl` | `{vm.overcommit_memory: 1}` | Settings for `/etc/sysctl.d/95-k8s.conf` |
| `ubuntu_k3s_node_blacklisted_modules` | `btrfs` and the RAID modules | Kernel modules that may not be loaded |
| `ubuntu_k3s_node_cilium` | `false` | Prepare the node for Cilium. See [Cilium](#cilium) |
| `ubuntu_k3s_node_cilium_modules` | See `defaults/main.yml` | Kernel modules to load at boot for Cilium |
| `ubuntu_k3s_node_storage_dir` | `/srv/k8s-storage` | Directory for local persistent storage |
| `ubuntu_k3s_node_config_dir` | `/etc/k8s` | Directory for node configuration, such as `resolv.conf` |
| `ubuntu_k3s_node_resolvers` | `[]` | Nameservers for `resolv.conf` in the configuration directory. Not written when empty |
| `ubuntu_k3s_node_nfsmount_conf` | `true` | Write `/etc/nfsmount.conf` with NFS defaults for volumes |
| `ubuntu_k3s_node_cachefilesd` | `true` | Install and run cachefilesd, a local cache for NFS mounts with the `fsc` option |
| `ubuntu_k3s_node_mount_watchdog_paths` | `[]` | Mount points to check. See [Mount watchdogs](#mount-watchdogs) |
| `ubuntu_k3s_node_ocfs2` | `false` | Set up OCFS2. See [OCFS2](#ocfs2) |
| `ubuntu_k3s_node_ocfs2_start` | `true` | Start the cluster stack and the mounts, and check the kernel module. False only writes the configuration |
| `ubuntu_k3s_node_ocfs2_cluster_name` | None | Name of the o2cb cluster, at most 16 letters, digits or underscores. Required with OCFS2 |
| `ubuntu_k3s_node_ocfs2_nodes` | `[]` | Every node of the cluster, each with `name`, `number`, `ip_address` and optionally `ip_port` (`7777`). Required with OCFS2 |
| `ubuntu_k3s_node_ocfs2_heartbeat_threshold` | `31` | A node is declared dead after (threshold - 1) x 2 seconds without a disk heartbeat |
| `ubuntu_k3s_node_ocfs2_idle_timeout_ms` | `30000` | Time before an idle connection to another node is considered down |
| `ubuntu_k3s_node_ocfs2_keepalive_delay_ms` | `2000` | Time before a keepalive is sent on an idle connection |
| `ubuntu_k3s_node_ocfs2_reconnect_delay_ms` | `2000` | Time between attempts to reconnect to another node |
| `ubuntu_k3s_node_ocfs2_sysctl` | `{kernel.panic: 10, kernel.panic_on_oops: 1}` | Settings added to `95-k8s.conf`, so that a fenced node reboots |
| `ubuntu_k3s_node_ocfs2_mounts` | `[]` | File systems to mount, each with `path`, `src` and optionally `opts` |
| `ubuntu_k3s_node_ocfs2_mount_opts` | `_netdev,noauto,x-systemd.automount,...` | Mount options for entries without `opts` |
| `ubuntu_k3s_node_psa_defaults` | Enforce `privileged`, audit and warn `baseline` | Pod Security Admission defaults for namespaces without their own labels |
| `ubuntu_k3s_node_psa_exempt_namespaces` | `[kube-system]` | Namespaces that Pod Security Admission doesn't check |

## Example playbook

```yaml
- name: Prepare k3s nodes
  hosts: k3s_nodes
  become: true
  serial: 1
  roles:
    - role: pypb.homelab.ubuntu_k3s_node
      vars:
        ubuntu_k3s_node_server: true
        ubuntu_k3s_node_resolvers:
          - 192.0.2.53
        ubuntu_k3s_node_psa_exempt_namespaces:
          - kube-system
          - metallb-system
```

Then point k3s at the files, for example in its configuration:

```yaml
kube-apiserver-arg:
  - admission-control-config-file=/var/lib/rancher/k3s/server/psa.yaml
  - audit-policy-file=/var/lib/rancher/k3s/server/audit.yaml
  - audit-log-path=/var/lib/rancher/k3s/server/logs/audit.log
resolv-conf: /etc/k8s/resolv.conf
```

## Rolling out

The [`pypb.homelab.ubuntu_k3s_node`](../../playbooks/ubuntu_k3s_node.yml) playbook
runs the role on one node at a time, and stops at the first failure. On servers,
it waits for the node to be Ready before moving on to the next one. With
`ubuntu_k3s_node_reboot` set, it also reboots each node first. It doesn't drain
nodes.

Try it on one node in check mode first, then for real:

```shell
ansible-playbook pypb.homelab.ubuntu_k3s_node -e ubuntu_k3s_node_hosts=k3s_nodes \
  --limit node1 --check --diff
ansible-playbook pypb.homelab.ubuntu_k3s_node -e ubuntu_k3s_node_hosts=k3s_nodes \
  --limit node1 -e ubuntu_k3s_node_reboot=true
```

The wait uses the host's kernel host name as the node name. Set
`ubuntu_k3s_node_name` if k3s runs with `--node-name`.

## Removed packages

`ubuntu_k3s_node_unneeded_packages` purges `apport`, `byobu`, `cloud-init`,
`landscape-common`, `lxd-installer`, `modemmanager`, `motd-news-config`, `plymouth`,
`pollinate`, `popularity-contest`, `snapd`, `sosreport`, `ubuntu-advantage-tools`,
`ubuntu-pro-client`, `update-notifier-common` and `whoopsie`. Packages that aren't
installed are skipped. Override the list to keep any of them.

- **snapd:** purging it removes every installed snap with its data.
- **cloud-init:** the role fails before purging it if `/etc/netplan/50-cloud-init.yaml`
  exists, because nothing would update that configuration afterwards. Write your
  own netplan file first, or keep cloud-init.
- **ubuntu-pro-client:** apt also removes `update-manager-core` with it.
- **Leftovers:** the role doesn't run `apt autoremove`. Dependencies that are no
  longer needed stay until you remove them.

`unattended-upgrades` isn't on the list, so the node keeps installing security
updates.

## Cilium

With `ubuntu_k3s_node_cilium: true`, the role:

- Loads `ubuntu_k3s_node_cilium_modules` at boot, from `/etc/modules-load.d/cilium.conf`.
  They aren't loaded right away. Reboot, or run `systemctl restart systemd-modules-load`.
  Add `wireguard` for WireGuard encryption.
- Writes `/etc/sysctl.d/99-zzz-override_cilium.conf` from the Cilium documentation.
  It turns rp_filter off for Cilium's interfaces and for `all`, because rp_filter
  can drop packets that Cilium has rewritten. It's applied right away.

Set it before switching the CNI to Cilium. With flannel it does no harm. The role
fails if a Cilium module is also in `ubuntu_k3s_node_blacklisted_modules`.

Setting it back to false removes both files. The settings already applied stay
until the next reboot.

## OCFS2

With `ubuntu_k3s_node_ocfs2: true`, the role sets up OCFS2 with the o2cb cluster
stack and local heartbeat, so every node can mount the same shared block device,
such as an iSCSI LUN, at the same time:

```yaml
ubuntu_k3s_node_ocfs2: true
ubuntu_k3s_node_ocfs2_cluster_name: k3s
ubuntu_k3s_node_ocfs2_nodes:
  - {name: node1, number: 1, ip_address: 192.0.2.11}
  - {name: node2, number: 2, ip_address: 192.0.2.12}
  - {name: node3, number: 3, ip_address: 192.0.2.13}
ubuntu_k3s_node_ocfs2_mounts:
  - path: /srv/k8s-storage
    src: UUID=00000000-0000-0000-0000-000000000000
ubuntu_k3s_node_mount_watchdog_paths:
  - /srv/k8s-storage
```

The role:

1. Installs `ocfs2-tools`, and makes sure the running kernel and the newest
   installed kernel, which the next boot uses, have the `ocfs2` module. If one
   doesn't, it installs that kernel's `linux-modules-extra` package, and fails if
   the module is still missing. For future kernels, keep the flavour's metapackage,
   such as `linux-image-generic`, installed, because it pulls in the extra modules.
2. Writes `/etc/ocfs2/cluster.conf` and the settings in `/etc/default/o2cb`.
3. Enables and starts the `o2cb` and `ocfs2` services. It never restarts them.
4. Adds `ubuntu_k3s_node_ocfs2_sysctl`. OCFS2 fences a node that loses contact with
   the others by panicking it, and these make it reboot rather than hang.
5. Adds the file systems to fstab, with `x-systemd.after=o2cb.service`, so that they
   mount after the cluster stack starts and unmount before it stops. Then it starts
   their automount units, or their mount units without `noauto`.

The play fails before changing anything if the node's host name (`uname -n`) isn't in
`ubuntu_k3s_node_ocfs2_nodes`, because o2cb wouldn't join the cluster.

Things to know:

- **Formatting:** the role doesn't create file systems. Format each device once,
  from one node, with room for every node that will mount it:
  `mkfs.ocfs2 -N 4 -L k8s-storage /dev/sdX`.
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
- **Molecule** only tests the configuration, because containers can't load the
  kernel modules.

## Mount watchdogs

For each path in `ubuntu_k3s_node_mount_watchdog_paths`, a timer checks every 15
minutes, starting 5 minutes after boot, that the path is a mount point. If it isn't,
the node reboots 2 minutes later. This is for volumes, such as iSCSI ones, that
pods can't run without and that a reboot reliably brings back.

The units are named `iscsi-mount-repair-<path>`. Removing a path from the list
doesn't remove its units.

With `x-systemd.automount`, the automount point counts as mounted even when the
volume behind it isn't.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes.
- **Applied right away:** packages, units, sysctl settings and the cachefilesd service.
- **Applied at reboot:** the module blacklist, for which the initramfs is updated,
  and the Cilium modules.
- **Applied at the next k3s restart:** the PSA configuration and audit policy. The
  role doesn't restart k3s.
- **Applied when o2cb next starts:** changes to the OCFS2 cluster configuration and
  timeouts. The role doesn't restart o2cb.
- **Replaced files:** `/etc/sysctl.d/95-k8s.conf`, `/etc/modprobe.d/blacklist-unused-storage.conf`,
  `/etc/nfsmount.conf`, the `resolv.conf` and the server files are replaced in full.
- **Rollback:** none. Purged packages have to be installed again by hand.

## License

Apache-2.0

## Author

pypb
