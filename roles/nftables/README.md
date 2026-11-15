# pypb.homelab.nftables

A host firewall with nftables. It writes `/etc/nftables.conf` with an
`inet filter` table, checks it with `nft --check`, loads it, and enables the
nftables service so that it loads at boot.

The input chain accepts:

- loopback traffic, and packets of established connections
- DHCP replies, ICMP, IPv6 echo requests and neighbour discovery
- what `nftables_input_rules` and `nftables_input_extra_rules` accept

It drops everything else, optionally logging it first. Forwarded and outgoing
traffic is accepted.

Only the `inet filter` table is replaced. Tables of other tools stay, such as
fail2ban's, or those of Kubernetes and its network plugins.

## Requirements

- ansible-core 2.21 or newer

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04, including on a Raspberry Pi

## Role variables

| Variable | Default | Description |
|---|---|---|
| `nftables_input_rules` | `[]` | Input rules, one nft rule per item |
| `nftables_input_extra_rules` | `[]` | More input rules after those |
| `nftables_input_log_prefix` | `""` | Log dropped input packets with this prefix. Not logged when empty |

The two rule lists let a group and a host each add rules without repeating
the other's: for example SSH from the admin network for every server in
`group_vars/all`, and a web server's ports in its `host_vars`.

## Example playbook

```yaml
- name: Configure the firewall
  hosts: servers
  become: true
  roles:
    - role: pypb.homelab.nftables
      vars:
        nftables_input_rules:
          - tcp dport 22 ip saddr { 192.0.2.0/24 } ct state new accept
          - tcp dport 9100 ip saddr { 192.0.2.10 } ct state new accept
        nftables_input_extra_rules:
          - tcp dport { 80, 443 } ct state new accept
        nftables_input_log_prefix: "inet_filter_drop: "
```

Make sure the rules accept SSH from where Ansible connects before the first
run, since the next connection would otherwise be dropped.

## Behaviour

- **Idempotent:** yes.
- **Atomic:** yes for the rules. The table is deleted and created again in one
  nft transaction, so a rule that fails to load leaves the old ones in place.
- **Check mode:** yes.
- **Applied right away:** the rules are loaded when the file changes.
- **Replaced files:** `/etc/nftables.conf`.
- **Rollback:** none. Earlier versions of the file aren't kept.

## License

Apache-2.0

## Author

pypb
