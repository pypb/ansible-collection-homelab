# pypb.homelab.swap

Sets up swap in compressed RAM, and optionally encrypted swap on disk:

- **zram:** sets up `/dev/zram0` as swap with systemd-zram-generator, which
  creates the device at every boot.
- **Encrypted swap:** a file on disk, opened at every boot with a new random
  key, through `/etc/crypttab` and `/etc/fstab`. Whatever is swapped out to it
  can't be read after a reboot, nor from a copy of the disk.
- **Swap files:** turns off and deletes others, such as Ubuntu's `/swap.img`.
- **sysctl:** writes settings for swap in RAM, and any others you set.

## Requirements

- ansible-core 2.21 or newer
- `community.general`
- The `zram` kernel module, for zram swap. The role checks for it. On Ubuntu's
  `-generic` kernels, it's in `linux-modules-extra`.

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04

## Role variables

| Variable | Default | Description |
|---|---|---|
| `swap_zram_enabled` | `true` | Set up `/dev/zram0` as swap. False turns it off and purges systemd-zram-generator |
| `swap_zram_size` | `min(ram / 2, 4096)` | The size in MiB, as an expression of `ram`, the RAM in MiB |
| `swap_zram_compression_algorithm` | `zstd` | The compression algorithm |
| `swap_zram_priority` | `100` | The swap priority. Higher is used first |
| `swap_zram_settings` | `{}` | Other `zram-generator.conf` settings for the device |
| `swap_zram_sysctl` | See below | sysctl settings written while zram is on |
| `swap_encrypted_enabled` | `false` | Set up encrypted swap in a file. False turns it off and deletes the file |
| `swap_encrypted_name` | `cryptswap` | The device name in `/dev/mapper`. Letters, digits and `_` only |
| `swap_encrypted_file` | `/var/swap.crypt` | The file the swap is in |
| `swap_encrypted_size_mb` | `512` | The file's size in MiB |
| `swap_encrypted_cipher` | `aes-xts-plain64` | The dm-crypt cipher |
| `swap_encrypted_key_size` | `512` | The key size in bits. `aes-xts-plain64` splits it in two, so 512 is AES-256 |
| `swap_encrypted_priority` | `10` | The swap priority, lower than zram's, so that it's used once zram is full |
| `swap_removed_files` | `[]` | Swap files to turn off, remove from fstab and delete |
| `swap_sysctl` | `{}` | Other sysctl settings. These override `swap_zram_sysctl` |
| `swap_sysctl_file` | `90-swap.conf` | The file in `/etc/sysctl.d/` |

`swap_zram_sysctl` defaults to the settings the
[ArchWiki](https://wiki.archlinux.org/title/Zram#Optimizing_swap_on_zram) suggests
for swap in RAM, which is quick to read back, so the kernel can swap more and
read one page at a time:

```yaml
swap_zram_sysctl:
  vm.swappiness: 180
  vm.page-cluster: 0
  vm.watermark_boost_factor: 0
  vm.watermark_scale_factor: 125
```

## Example playbook

Use a quarter of the RAM for zram, with encrypted swap on disk behind it, and
delete the swap file the Ubuntu installer made:

```yaml
- name: Set up swap
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.swap
      vars:
        swap_zram_size: ram / 4
        swap_encrypted_enabled: true
        swap_encrypted_size_mb: 1024
        swap_removed_files:
          - /swap.img
```

Turn swap off entirely, such as on Kubernetes nodes:

```yaml
swap_zram_enabled: false
swap_removed_files:
  - /swap.img
```

## zram

The settings go to `/etc/systemd/zram-generator.conf`, which replaces the
package's `/usr/lib/systemd/zram-generator.conf`. Only `zram0` is set up: zram
compresses on all CPUs from one device, so a device per CPU isn't needed.

The role removes fstab lines for `/dev/zram` devices, since zram-generator
defines their swap units. Older setups may also have udev rules or
`modprobe.d` options for zram, which conflict with zram-generator and need to
go.

## Encrypted swap

The crypttab line opens the file in plain dm-crypt mode with a key from
`/dev/urandom`, and the `swap` option formats it as swap each time:

```text
cryptswap /var/swap.crypt /dev/urandom swap,plain,cipher=aes-xts-plain64,size=512
```

systemd-cryptsetup sets up a loop device for the file, after the file system
it's on is mounted. The file can't be hibernated to, since its key is gone at
every boot.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** no.
- **Check mode:** yes.
- **Applied right away:** new swap starts right away. A zram device or
  encrypted swap that's already in use keeps its size until the next boot.
  Turning swap off stops it right away. Removed sysctl settings stay until the
  next boot.
- **Containers:** only the files are written, since a container can't set up
  swap, and shares its host's sysctl settings.
- **Replaced files:** `/etc/systemd/zram-generator.conf` and the sysctl file.
  Only the role's lines in `/etc/fstab` and `/etc/crypttab` change.
- **Rollback:** set `swap_zram_enabled` and `swap_encrypted_enabled` to false.

## License

Apache-2.0

## Author

pypb
