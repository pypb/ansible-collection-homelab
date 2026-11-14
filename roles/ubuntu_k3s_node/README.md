# pypb.homelab.ubuntu_k3s_node

Prepares an Ubuntu server as a minimal k3s node. It strips the packages and units
that a node doesn't need, and sets up what k3s and its storage need around it:

- Purges packages that conflict with k3s, such as Docker and ufw, and packages a
  node doesn't need, such as snapd, cloud-init and apport. Masks units you list.
- Sets sysctl settings and blacklists unused kernel modules.
- Optionally prepares the node for [Cilium](#cilium): its kernel modules and its
  rp_filter override.
- Installs the NFS client, configures `/etc/nfsmount.conf`, and runs cachefilesd.
- Writes a `resolv.conf` for k3s to give to pods.
- Adds watchdogs that reboot the node when a mount, such as an iSCSI volume, is missing.
- Stops the k3s pods at shutdown, so that shared file systems such as OCFS2
  unmount cleanly.
- On servers, writes the Pod Security Admission configuration and audit policy
  that k3s reads.

It doesn't install, configure or restart k3s. Install k3s with a role such as
[`xanmanning.k3s`](https://github.com/PyratLabs/ansible-role-k3s), and point its
options at the files this role writes. Run this role first: it works on a node
that doesn't have k3s yet, so k3s finds its configuration when it first starts.

## Requirements

- Root access on the target, for example through `become`

## Supported platforms

| Platform | Versions | Tested |
|---|---|---|
| Ubuntu | 24.04 (noble), 26.04 (resolute), including Raspberry Pi | Molecule, without kernel modules, cachefilesd or a reboot |

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
| `ubuntu_k3s_node_stop_pods_at_shutdown` | `true` | Stop the k3s pods at shutdown. See [Stopping pods at shutdown](#stopping-pods-at-shutdown) |
| `ubuntu_k3s_node_k3s_service` | `k3s.service` | The k3s unit, which the pods are stopped after |
| `ubuntu_k3s_node_k3s_killall` | `/usr/local/bin/k3s-killall.sh` | The script that stops k3s and its pods |
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
runs the role on one node at a time, and stops at the first failure. On servers
that already run k3s, it waits for the node to be Ready before moving on to the
next one. Set `ubuntu_k3s_node_k3s_service` when the k3s unit isn't called
`k3s.service`. With `ubuntu_k3s_node_iscsi` set, it first runs the
[`iscsi_initiator`](../iscsi_initiator/README.md) role, and with
`ubuntu_k3s_node_ocfs2` set, the [`ocfs2`](#ocfs2) role.

With `ubuntu_k3s_node_reboot` set, it also reboots each node. Before the reboot, it
stops k3s and its pods with `ubuntu_k3s_node_k3s_killall` and, with
`ubuntu_k3s_node_ocfs2` set, unmounts `ocfs2_mounts`, so that the node leaves the
OCFS2 cluster cleanly. If a file system is still busy, the play fails and the node
isn't rebooted. It doesn't drain nodes, so the pods stop without being moved.

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

The [`pypb.homelab.ocfs2`](../ocfs2/README.md) role sets up OCFS2, usually on
iSCSI disks from the [`pypb.homelab.iscsi_initiator`](../iscsi_initiator/README.md)
role. The [`pypb.homelab.ubuntu_k3s_node`](../../playbooks/ubuntu_k3s_node.yml)
playbook runs them before this role when `ubuntu_k3s_node_iscsi` and
`ubuntu_k3s_node_ocfs2` are true, so that the mounts exist before the watchdogs
check them:

```yaml
ubuntu_k3s_node_iscsi: true
iscsi_initiator_targets:
  - target: iqn.2003-01.org.linux-iscsi.nas.x8664:sn.0123456789ab
    portal: 192.0.2.30
ubuntu_k3s_node_ocfs2: true
ocfs2_cluster_name: k3s
ocfs2_nodes:
  - {name: node1, number: 1, ip_address: 192.0.2.11}
  - {name: node2, number: 2, ip_address: 192.0.2.12}
ocfs2_mounts:
  - path: /srv/k8s-storage
    src: UUID=00000000-0000-0000-0000-000000000000
ubuntu_k3s_node_mount_watchdog_paths:
  - /srv/k8s-storage
```

## Mount watchdogs

For each path in `ubuntu_k3s_node_mount_watchdog_paths`, a timer checks every 15
minutes, starting 5 minutes after boot, that the path is a mount point. If it isn't,
the node reboots 2 minutes later. This is for volumes, such as iSCSI ones, that
pods can't run without and that a reboot reliably brings back.

The units are named `iscsi-mount-repair-<path>`. Removing a path from the list
doesn't remove its units.

With `x-systemd.automount`, the automount point counts as mounted even when the
volume behind it isn't.

## Stopping pods at shutdown

k3s leaves its containers running when it stops. At shutdown they keep the file
systems they use busy, so those don't unmount until the containers are killed.
For OCFS2 that's too late: by then the network is down, and the other nodes block
until they declare the node dead. See the clean shutdown note in the
[`ocfs2`](../ocfs2/README.md#things-to-know) role.

With `ubuntu_k3s_node_stop_pods_at_shutdown`, the role installs and starts
`stop-k3s-pods.service`. It does nothing at boot. At shutdown, it runs
`k3s-killall.sh` after k3s stops and before the file systems unmount and the network
goes down. Its name doesn't start with `k3s`, because `k3s-killall.sh` stops the
units with those names. Stopping it by hand also stops the pods.

Turning it off disables and deletes the unit without stopping it. The unit that's
already loaded may still run once, at the next shutdown.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes.
- **Applied right away:** packages, units, sysctl settings, the cachefilesd service
  and the unit that stops the pods at shutdown.
- **Applied at reboot:** the module blacklist, for which the initramfs is updated,
  and the Cilium modules.
- **Applied at the next k3s restart:** the PSA configuration and audit policy. The
  role doesn't restart k3s.
- **Replaced files:** `/etc/sysctl.d/95-k8s.conf`, `/etc/modprobe.d/blacklist-unused-storage.conf`,
  `/etc/nfsmount.conf`, the `resolv.conf` and the server files are replaced in full.
- **Rollback:** none. Purged packages have to be installed again by hand.

## License

Apache-2.0

## Author

pypb
