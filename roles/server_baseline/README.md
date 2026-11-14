# pypb.homelab.server_baseline

Basic configuration of a Debian or Ubuntu server, applied to every server before
the roles that give it a purpose:

- Installs and purges packages, with extra lists for Ubuntu and for virtual
  machines, and optionally points Ubuntu at an archive mirror.
- Sets the host's domain name in `/etc/mailname`, and in the `127.0.1.1` line of
  `/etc/hosts` when there is one.
- Optionally writes a static, immutable `/etc/resolv.conf`, and stops
  NetworkManager, dhclient and resolvconf from rewriting it.
- Sets sysctl settings, the time zone, the sudo password timeout, vim's mouse,
  `/tmp` as tmpfs on Debian and Ubuntu's motd-news.
- Writes the message of the day and the login banners.
- Sets the kernel consoles and the GRUB menu, or the consoles on a Raspberry Pi's
  kernel command line. See [Consoles and boot menu](#consoles-and-boot-menu).

Most settings are left alone until you set them. The defaults only install and
purge packages, turn off ICMP redirects, and keep motd-news as it is.

## Requirements

- ansible-core 2.21 or newer
- `community.general`, for the time zone

## Supported platforms

- Debian 13, including Proxmox VE 9
- Ubuntu 24.04 and 26.04, including on a Raspberry Pi

## Role variables

| Variable | Default | Description |
|---|---|---|
| `server_baseline_packages` | `[]` | Packages to install |
| `server_baseline_purged_packages` | `[]` | Packages to purge |
| `server_baseline_ubuntu_packages` | `[python3-debian, ssl-cert]` | Packages to install on Ubuntu |
| `server_baseline_ubuntu_purged_packages` | Landscape, Ubuntu Pro and update-notifier packages | Packages to purge on Ubuntu |
| `server_baseline_vm_purged_packages` | fwupd, smartmontools, udisks2 | Packages to purge on virtual machines and containers |
| `server_baseline_autoremove` | `false` | Purge the packages nothing depends on any more |
| `server_baseline_apt_clean` | `false` | Empty the package cache |
| `server_baseline_ubuntu_mirror` | `""` | Mirror for `archive.ubuntu.com` and `security.ubuntu.com`. `ports.ubuntu.com` is left alone |
| `server_baseline_domain` | `""` | The host's DNS domain, for `/etc/mailname`, the resolv.conf search domain and an existing `127.0.1.1` line in `/etc/hosts` |
| `server_baseline_nameservers` | `[]` | Nameservers for a static resolv.conf. See [DNS](#dns) |
| `server_baseline_dns_search` | The domain | Search domains for resolv.conf |
| `server_baseline_resolv_options` | `[edns0, "timeout:2"]` | Options for resolv.conf |
| `server_baseline_resolv_conf_immutable` | `true` | Make resolv.conf immutable |
| `server_baseline_sysctl_file` | `90-server-baseline.conf` | Name of the sysctl file in `/etc/sysctl.d` |
| `server_baseline_sysctl` | No ICMP redirects | Sysctl settings |
| `server_baseline_timezone` | `""` | Time zone, such as `Europe/Berlin` |
| `server_baseline_sudo_timestamp_timeout` | Not set | Minutes sudo remembers a password. Installs sudo |
| `server_baseline_vim_disable_mouse` | `false` | Turn off the mouse in vim, so that the terminal selects and pastes text |
| `server_baseline_tmp_tmpfs` | `false` | Mount `/tmp` as tmpfs from the next boot. Debian only |
| `server_baseline_motd_news` | `true` | Show Ubuntu's news in the message of the day |
| `server_baseline_motd` | Not set | Contents of `/etc/motd` |
| `server_baseline_issue` | Not set | Contents of `/etc/issue`, shown before console logins |
| `server_baseline_issue_net` | Not set | Contents of `/etc/issue.net`, which sshd can show as its banner |
| `server_baseline_kernel_consoles` | `[]` | Kernel consoles. The last one gets systemd's status |
| `server_baseline_grub_timeout` | Not set | Seconds GRUB shows its menu for |
| `server_baseline_grub_terminals` | `[]` | GRUB terminals, such as `[console, serial]` |
| `server_baseline_grub_serial_command` | `serial --unit=0 --speed=115200` | GRUB serial port settings |

Variables that are empty or not set aren't managed: the role leaves those files
and settings as they are.

## Example playbook

```yaml
- name: Configure servers
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.server_baseline
      vars:
        server_baseline_packages: [curl, jq, tmux, vim]
        server_baseline_purged_packages: [nano]
        server_baseline_domain: example.com
        server_baseline_nameservers: [192.0.2.53, 192.0.2.54]
        server_baseline_timezone: Europe/Berlin
        server_baseline_motd_news: false
        server_baseline_issue_net: |
          Authorised use only.
        server_baseline_kernel_consoles: [ttyS0, tty1]
        server_baseline_grub_timeout: 5
        server_baseline_grub_terminals: [console, serial]
```

## DNS

With `server_baseline_nameservers` set, `/etc/resolv.conf` becomes a static file
with those nameservers, the search domains and the options. On Ubuntu that
replaces the link to systemd-resolved's stub resolver. systemd-resolved keeps
running, but nothing uses it.

So that the file stays as written, the role:

- tells NetworkManager not to manage it, with `dns=none`, which takes effect when
  NetworkManager next starts
- turns off dhclient's update of it with an enter hook
- purges resolvconf and openresolv
- makes it immutable, unless `server_baseline_resolv_conf_immutable` is false.
  The flag only comes off while the role changes the file.

Containers, which get their resolv.conf and hosts file from their host, are
skipped.

## Consoles and boot menu

The kernel writes its messages to every console on its command line, but
`/dev/console`, and with it systemd's start and stop messages, is only the last
one. Ubuntu's cloud images boot with `console=tty1 console=ttyS0`, so a virtual
machine's screen shows kernel messages and nothing from systemd. Set
`server_baseline_kernel_consoles: [ttyS0, tty1]` to put the screen last.

**GRUB:** the role writes `/etc/default/grub.d/99-server-baseline.cfg` and runs
`update-grub`. update-grub reads it after the cloud images'
`50-cloudimg-settings.cfg`. The file:

- removes the `console=` options set before, in both `GRUB_CMDLINE_LINUX` and
  `GRUB_CMDLINE_LINUX_DEFAULT`, and adds the role's, keeping the other options
- sets `GRUB_TIMEOUT`, with the menu shown rather than hidden, for
  `server_baseline_grub_timeout`. The cloud images hide the menu with a timeout
  of 0, so there's no chance to edit a boot entry
- sets `GRUB_TERMINAL` and `GRUB_SERIAL_COMMAND` for `server_baseline_grub_terminals`,
  so the menu also shows on the serial console.

The file is removed when none of these is set. A file in `/etc/default/grub.d`
that sorts after it can still override it, and only files ending in `.cfg` are
read at all.

**Raspberry Pi:** without `/etc/default/grub`, but with
`/boot/firmware/cmdline.txt`, the role replaces the `console=` options in that
file, keeping a backup. The GRUB settings don't apply.

Hosts with neither are reported and skipped. All console changes take effect at
the next boot.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes. Settings that need a package the run would install, such as
  the time zone and sudo, are skipped.
- **Applied right away:** packages, sysctl settings, the time zone, resolv.conf and
  the other files.
- **Applied at the next boot:** `/tmp` as tmpfs, the kernel consoles and the GRUB
  settings.
- **Replaced files:** resolv.conf, `/etc/mailname`, the sysctl file, the GRUB file,
  `/etc/sudoers.d/timeout`, `/etc/vim/vimrc.local`, and the motd and banner files
  that are set are replaced in full. Only the `127.0.1.1` line of `/etc/hosts` changes, and it's never added, since
  hosts such as Proxmox VE need their name to resolve to their real address.
- **Rollback:** none. Purged packages have to be installed again by hand.

## License

Apache-2.0

## Author

pypb
