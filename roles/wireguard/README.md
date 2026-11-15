# pypb.homelab.wireguard

Sets up a WireGuard interface with wg-quick:

- Installs WireGuard's tools and generates a key pair on the host, in
  `/etc/wireguard/privatekey` and `publickey`, unless it has one. The private
  key never leaves the host: the configuration loads it from its file.
- Writes `/etc/wireguard/<interface>.conf` with listed peers, such as a
  gateway, and a mesh of inventory hosts that run the role too. A mesh peer's
  public key is read from the peer itself.
- Brings up `wg-quick@<interface>` at boot. A change of peers is applied with a
  reload, which keeps the sessions of the other peers, and a change of address
  with a restart.
- Optionally registers the host as a peer of a WireGuard instance on an
  OPNsense firewall, through its API.

## Requirements

- ansible-core 2.21 or newer
- `community.general` on the controller, for meshing whole groups as in the
  example
- An API key on the firewall, for the OPNsense registration

## Supported platforms

- Debian 13
- Ubuntu 24.04 and 26.04

## Role variables

| Variable | Default | Description |
|---|---|---|
| `wireguard_interface` | `wg0` | Name of the interface |
| `wireguard_addresses` | required | Addresses of the interface with their prefix length, such as `[10.0.0.2/24]` |
| `wireguard_port` | `51820` | UDP port to listen on |
| `wireguard_peers` | `[]` | Peers that aren't inventory hosts, each with `public_key`, `allowed_ips` and optionally `name`, `endpoint` and `persistent_keepalive` |
| `wireguard_mesh_peers` | `[]` | Inventory hosts to mesh with, each with `host` and optionally `endpoint` |
| `wireguard_mesh_persistent_keepalive` | `0` | Seconds between keepalives to mesh peers, or 0 for none |
| `wireguard_ip_forward` | `false` | Forward packets, to route between the tunnel and other networks |
| `wireguard_opnsense` | `{}` | Register the host as a peer on OPNsense, see below |

### Mesh

Each host in `wireguard_mesh_peers` gets a peer with its public key, read from
the host, and its `wireguard_addresses` as allowed IPs. It's reached on its
`wireguard_port`, at the mesh peer's `endpoint`, or else the host's
`wireguard_mesh_endpoint`, or else its inventory hostname. The host running the
role is skipped, so a whole group can share one list. Set
`wireguard_addresses`, `wireguard_port` and `wireguard_mesh_endpoint` in the
inventory, where the other hosts can read them.

A peer that has no key yet is left out with a message, and added on the next
run. Hosts set up in the same run already see each other.

### OPNsense

`wireguard_opnsense` takes:

| Key | Default | Description |
|---|---|---|
| `host` | required | Address or hostname of the firewall |
| `api_key`, `api_secret` | required | API credentials |
| `instance` | required | Name of the WireGuard instance on the firewall |
| `name` | short inventory hostname | Name of the peer |
| `endpoint` | address of the default IPv4 route | Address the firewall connects to, on `wireguard_port` |
| `keepalive` | `25` | Seconds between keepalives from the firewall, or 0 for none |
| `validate_certs` | `true` | Validate the firewall's certificate |

The peer is found by its public key, then by its name, so that a new key
replaces the old one. It's only updated when it differs, and the firewall's
WireGuard service is then reconfigured once.

With a firewall behind a dynamic address, leave out the firewall peer's
`endpoint` in `wireguard_peers`. The firewall connects to this host instead,
and its keepalives bring the tunnel back up when its address changes.

## Example playbook

```yaml
- name: Connect the public servers to the gateway
  hosts: public
  become: true
  roles:
    - role: pypb.homelab.wireguard
      vars:
        wireguard_addresses: ["{{ tunnel_address }}/24"]
        wireguard_peers:
          - name: gateway
            public_key: "{{ gateway_public_key }}"
            allowed_ips: [10.0.0.0/16]
        wireguard_mesh_peers: "{{ groups['public'] | map('community.general.dict_kv', 'host') }}"
        wireguard_opnsense:
          host: gateway.example.org
          api_key: "{{ vault_opnsense_key }}"
          api_secret: "{{ vault_opnsense_secret }}"
          instance: wg0
```

## Behaviour

- **Idempotent:** yes, also on OPNsense.
- **Atomic:** no.
- **Check mode:** yes. On a host without a key yet, the OPNsense registration
  is skipped. The changes to the OPNsense peer are shown as a message.
- **Applied right away:** yes, with a reload, or a restart for a change of
  address.
- **Replaced files:** `/etc/wireguard/<interface>.conf`. The key pair is kept.
- **Rollback:** none.

## License

Apache-2.0

## Author

pypb
