# pypb.homelab.server_hardening

Hardens a Debian or Ubuntu server, beyond the basics in
[`server_baseline`](../server_baseline/README.md):

- Installs AppArmor, debsums and passwdqc, and purges network services such as
  avahi, telnet and talk, auditing tools such as lynis and rkhunter, popularity
  reporting, and Ubuntu's crash reporting.
- Purges wifi and bluetooth, and turns the radios off on a Raspberry Pi.
- Writes sysctl settings from
  [madaidans-insecurities' Linux hardening guide](https://madaidans-insecurities.github.io/guides/linux-hardening.html).
- Blocks kernel modules for rare network protocols, FireWire, rarely used file
  systems and devices that servers don't have.
- Stops and masks rpcbind, the other NFS RPC services, rsync and Ubuntu Pro's
  services.
- Turns off core dumps through limits.conf, closes idle login shells after a day,
  and has debsums check the installed files every day.

The defaults are strict, and some of them change how the network and debugging
work. See [Settings to check](#settings-to-check) before applying the role.

## Requirements

- ansible-core 2.21 or newer

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04, including on a Raspberry Pi

## Role variables

| Variable | Default | Description |
|---|---|---|
| `server_hardening_packages` | `[apparmor, debsums, libpam-passwdqc]` | Packages to install |
| `server_hardening_purged_packages` | Network services, auditing tools, popularity-contest | Packages to purge. Patterns such as `telnet*` work |
| `server_hardening_ubuntu_purged_packages` | apport | Packages to purge on Ubuntu |
| `server_hardening_wifi` | `false` | Keep wifi. False purges rfkill and wpasupplicant, and turns wifi off on a Raspberry Pi |
| `server_hardening_bluetooth` | `false` | Keep bluetooth. False purges bluez, blocks its modules, and turns it off on a Raspberry Pi |
| `server_hardening_masked_units` | rpcbind, NFS RPC services, rsync, Ubuntu Pro | Systemd units to stop and mask |
| `server_hardening_blocked_modules` | Rare protocols, FireWire, file systems, devices | Kernel modules that can't be loaded |
| `server_hardening_extra_blocked_modules` | `[]` | More modules to block |
| `server_hardening_sysctl` | madaidans' settings | Sysctl settings |
| `server_hardening_limits` | `["* hard core 0"]` | Lines for limits.conf. The file is removed when empty |
| `server_hardening_shell_timeout` | `86400` | Seconds before an idle login shell closes. Not managed when null |
| `server_hardening_debsums_cron` | `daily` | How often debsums runs: `daily`, `weekly`, `monthly` or `never` |
| `server_hardening_removed_files` | `[]` | Files and directories to delete |

The full default lists are in [`defaults/main.yml`](defaults/main.yml).

## Example playbook

```yaml
- name: Harden servers
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.server_hardening
      vars:
        # NFSv3 mounts need rpcbind on the client.
        server_hardening_masked_units: [rsync.service]
        server_hardening_extra_blocked_modules: [esp4, esp6]
        server_hardening_removed_files:
          - /etc/ssh/sshd_config.d/50-cloud-init.conf
```

## Settings to check

- **TCP:** `net.ipv4.tcp_timestamps: 0` and `tcp_sack: 0` stop the host from
  revealing its uptime, and avoid past SACK bugs, but slow TCP down on lossy or
  fast links.
- **Debugging:** `kernel.yama.ptrace_scope: 2` lets only root attach debuggers
  such as gdb and strace, and `kernel.perf_event_paranoid: 3` turns perf off for
  other users. `kernel.kexec_load_disabled: 1` stops kexec, and with it kdump,
  until the next boot.
- **eBPF:** `kernel.unprivileged_bpf_disabled: 1` only allows root to load eBPF
  programs, which is what Cilium and other eBPF tools run as.
- **Reverse path filtering:** `rp_filter: 1` drops packets that arrive on an
  interface the reply wouldn't leave by, which breaks asymmetric routing.
- **NFS:** masking rpcbind and the RPC services leaves NFSv4 working, but NFSv3
  mounts need rpcbind and rpc-statd on the client. Take them off
  `server_hardening_masked_units` on those hosts.
- **Modules:** squashfs is blocked, which snaps need. Add `bluetooth` back by
  setting `server_hardening_bluetooth: true`, not by editing the module list.

To change one setting, override the whole variable. `server_hardening_sysctl`,
for example, replaces the default dict rather than adding to it.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes. The debsums setting is skipped when debsums isn't
  installed yet.
- **Applied right away:** packages, sysctl settings (except in containers, which
  share their host's kernel), masked units, the files deleted.
- **Applied later:** blocked modules that are already loaded stay loaded until the
  next boot. Resource limits and the shell timeout apply from the next login, and
  the Raspberry Pi radio settings from the next boot.
- **Replaced files:** `/etc/sysctl.d/90-server-hardening.conf`,
  `/etc/modprobe.d/90-server-hardening.conf`,
  `/etc/security/limits.d/90-server-hardening.conf` and
  `/etc/profile.d/server-hardening.sh` are replaced in full. In
  `/etc/default/debsums` and a Raspberry Pi's `config.txt`, only the role's
  lines change.
- **Rollback:** none. Purged packages have to be installed again by hand, and
  masked units stay masked.

## License

Apache-2.0

## Author

pypb
