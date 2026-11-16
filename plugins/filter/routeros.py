# Copyright: (c) 2026, pypb
# Apache License 2.0 (see LICENSE or https://www.apache.org/licenses/LICENSE-2.0)

"""Filters that turn RouterOS configuration data into an ordered plan."""

from __future__ import annotations

import base64
import binascii
import hashlib
import re

from ansible.errors import AnsibleFilterError

_STEP_RE = re.compile(r"^(\d+)_\S+$")

_MODULE_OPTIONS = {
    "community.routeros.api_modify": frozenset(
        (
            "path",
            "data",
            "ensure_order",
            "handle_absent_entries",
            "handle_entries_content",
            "handle_read_only",
            "handle_write_only",
        )
    ),
    "community.routeros.api_find_and_modify": frozenset(
        (
            "path",
            "find",
            "values",
            "allow_no_matches",
            "ignore_builtin",
            "ignore_dynamic",
            "require_matches_min",
            "require_matches_max",
        )
    ),
    "community.routeros.command": frozenset(("command",)),
}

_DEFAULT_PORT_STEPS = {
    "bridge": "0200_bridge",
    "ethernet": "0200_ethernet",
    "port": "0220_bridge_port",
    "vlan": "0230_bridge_vlan",
}


def _fail(msg):
    raise AnsibleFilterError(msg)


def _step_sort_key(step):
    match = _STEP_RE.match(step)
    return (int(match.group(1)), step)


def _module_for(where, op):
    kinds = [key for key in ("data", "find", "command") if key in op]
    if len(kinds) != 1:
        found = (
            f"it has {' and '.join(kinds)}" if kinds else f"it has only {sorted(op)}"
        )
        _fail(
            f"{where}: an operation needs exactly one of data, find or command, but {found}"
        )
    module = {
        "data": "community.routeros.api_modify",
        "find": "community.routeros.api_find_and_modify",
        "command": "community.routeros.command",
    }[kinds[0]]
    unknown = sorted(set(op) - _MODULE_OPTIONS[module])
    if unknown:
        _fail(f"{where}: unknown keys {unknown} for {module}")
    return module


def _check_op(where, module, op):
    if module == "community.routeros.command":
        commands = op["command"]
        if isinstance(commands, str):
            commands = [commands]
        if (
            not isinstance(commands, list)
            or not commands
            or not all(isinstance(c, str) for c in commands)
        ):
            _fail(f"{where}: command must be a string or a list of strings")
        return {"commands": commands}
    path = op.get("path")
    if not isinstance(path, str) or not path.strip():
        _fail(f"{where}: path is required")
    if module == "community.routeros.api_modify":
        if not isinstance(op["data"], list) or not all(
            isinstance(e, dict) for e in op["data"]
        ):
            _fail(f"{where}: data must be a list of dicts")
    else:
        if not isinstance(op["find"], dict):
            _fail(f"{where}: find must be a dict")
        if not isinstance(op.get("values"), dict):
            _fail(f"{where}: values is required with find, and must be a dict")
    return dict(op)


def routeros_config_plan(steps, handle_absent_entries_default="ignore"):
    """Turn a dict of steps into an ordered list of module calls.

    Steps run in the order of their number prefix, and the operations of a step in
    the order they are listed. Within a step, api_modify operations on the same
    path are joined into one call, so that each layer can add entries to it.
    """
    if steps is None:
        steps = {}
    if not isinstance(steps, dict):
        _fail("the steps must be a dict of step names to lists of operations")
    if handle_absent_entries_default not in ("ignore", "remove"):
        _fail("handle_absent_entries_default must be ignore or remove")

    for step in steps:
        if not isinstance(step, str) or not _STEP_RE.match(step):
            _fail(
                f"step {step!r}: the name must be a number, an underscore and a word, such as 0100_system"
            )

    plan = []
    removing = {}
    for step in sorted(steps, key=_step_sort_key):
        ops = steps[step]
        if ops is None:
            continue
        if not isinstance(ops, list):
            _fail(
                f"step {step}: must be a list of operations, not {type(ops).__name__}"
            )
        by_path = {}
        for index, op in enumerate(ops):
            where = f"step {step}, operation {index + 1}"
            if not isinstance(op, dict):
                _fail(f"{where}: must be a dict")
            module = _module_for(where, op)
            args = _check_op(where, module, op)
            if module != "community.routeros.api_modify":
                plan.append(
                    {
                        "step": step,
                        "module": module,
                        "path": args.get("path", ""),
                        "args": args,
                    }
                )
                continue
            path = " ".join(args["path"].split())
            args["path"] = path
            existing = by_path.get(path)
            if existing is None:
                args["data"] = list(args["data"])
                by_path[path] = args
                plan.append(
                    {"step": step, "module": module, "path": path, "args": args}
                )
                continue
            for key, value in args.items():
                if key in ("path", "data"):
                    continue
                if key in existing and existing[key] != value:
                    _fail(
                        f"{where}: {key} is {value!r} for {path}, but {existing[key]!r} earlier in the step"
                    )
                existing[key] = value
            existing["data"].extend(args["data"])

        for path, args in by_path.items():
            args.setdefault("handle_absent_entries", handle_absent_entries_default)
            if args["handle_absent_entries"] == "remove":
                removing.setdefault(path, []).append(step)

    api_modify_steps = {}
    for entry in plan:
        if entry["module"] == "community.routeros.api_modify":
            api_modify_steps.setdefault(entry["path"], []).append(entry["step"])
    for path, removing_steps in removing.items():
        if len(api_modify_steps[path]) > 1:
            _fail(
                f"{path} is set in steps {api_modify_steps[path]}, and removes absent entries in {removing_steps}, "
                "so one step would remove the entries of the other. Set it in one step."
            )
    return plan


def _vlan_ids(where, value):
    if value is None:
        return set()
    if not isinstance(value, list):
        value = [value]
    ids = set()
    for item in value:
        text = str(item).strip()
        for part in text.split(","):
            match = re.fullmatch(r"(\d+)(?:-(\d+))?", part.strip())
            if not match:
                _fail(f"{where}: {item!r} is not a VLAN ID or range")
            low = int(match.group(1))
            high = int(match.group(2) or low)
            if not 1 <= low <= high <= 4094:
                _fail(f"{where}: {item!r} is outside 1-4094")
            ids.update(range(low, high + 1))
    return ids


def _ranges(ids):
    ids = sorted(ids)
    parts = []
    start = prev = ids[0]
    for vid in ids[1:]:
        if vid == prev + 1:
            prev = vid
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = vid
    parts.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(parts)


_PORT_KEYS = frozenset(
    (
        "comment",
        "ethernet",
        "poe",
        "bridge",
        "pvid",
        "tagged",
        "frame_types",
        "hw",
        "bridge_port",
    )
)
_BRIDGE_KEYS = frozenset(
    ("vlan_filtering", "tagged_vlans", "group_vlans", "cpu_interface", "settings")
)


def routeros_config_ports(
    ports, bridges=None, steps=None, ethernet_pattern=r"^(ether|sfp|qsfp|combo)\d"
):
    """Turn a description of ports and bridges into configuration steps.

    Each port is described once: its comment, PoE, bridge, PVID and tagged VLANs.
    The result is a dict of steps for interface bridge, interface ethernet,
    interface ethernet poe, interface bridge port and interface bridge vlan, to be
    merged with the other steps before routeros_config_plan.

    RouterOS lists the members of a bridge VLAN in its own order of interfaces, and
    api_modify compares the lists as text, so the members are listed with the
    bridge itself first and then in the order of the ports.
    """
    ports = ports or {}
    bridges = bridges or {}
    if not isinstance(ports, dict) or not isinstance(bridges, dict):
        _fail("ports and bridges must be dicts")
    step_names = dict(_DEFAULT_PORT_STEPS)
    step_names.update(steps or {})
    unknown_steps = sorted(set(step_names) - set(_DEFAULT_PORT_STEPS))
    if unknown_steps:
        _fail(
            f"unknown port steps {unknown_steps}, expected {sorted(_DEFAULT_PORT_STEPS)}"
        )
    ethernet_re = re.compile(ethernet_pattern)

    bridge_data = []
    bridge_cpu_vlans = {}
    cpu_names = {}
    for name, bridge in bridges.items():
        bridge = bridge or {}
        where = f"bridge {name}"
        if not isinstance(bridge, dict):
            _fail(f"{where}: must be a dict")
        unknown = sorted(set(bridge) - _BRIDGE_KEYS)
        if unknown:
            _fail(f"{where}: unknown keys {unknown}")
        entry = {"name": name}
        if "vlan_filtering" in bridge:
            entry["vlan-filtering"] = bool(bridge["vlan_filtering"])
        entry.update(bridge.get("settings") or {})
        bridge_data.append(entry)
        bridge_cpu_vlans[name] = _vlan_ids(where, bridge.get("tagged_vlans"))
        cpu_interface = bridge.get("cpu_interface", name)
        if not isinstance(cpu_interface, str) or not cpu_interface:
            _fail(f"{where}: cpu_interface must be an interface name")
        cpu_names[name] = cpu_interface

    ethernet_data = []
    poe_data = []
    port_data = []
    members = {
        name: {} for name in bridges
    }  # bridge -> vlan -> {"tagged": set, "untagged": set}

    order = {}
    for name in ports:
        port = ports[name] or {}
        where = f"port {name}"
        if not isinstance(port, dict):
            _fail(f"{where}: must be a dict")
        unknown = sorted(set(port) - _PORT_KEYS)
        if unknown:
            _fail(f"{where}: unknown keys {unknown}")

        ethernet = port.get("ethernet")
        if ethernet is None:
            ethernet = {} if ethernet_re.search(name) else False
        if ethernet is not False:
            if not isinstance(ethernet, dict):
                _fail(f"{where}: ethernet must be a dict or false")
            entry = {"default-name": name}
            if "comment" in port:
                entry["comment"] = port["comment"]
            entry.update(ethernet)
            if len(entry) > 1:
                ethernet_data.append(entry)

        if port.get("poe") is not None:
            if not isinstance(port["poe"], dict):
                _fail(f"{where}: poe must be a dict")
            poe_data.append({"name": name, **port["poe"]})

        bridge = port.get("bridge")
        if bridge is None:
            for key in ("pvid", "tagged", "frame_types", "hw", "bridge_port"):
                if key in port:
                    _fail(f"{where}: {key} needs a bridge")
            continue
        if bridge not in bridges:
            _fail(f"{where}: bridge {bridge} is not in routeros_config_bridges")

        pvid = port.get("pvid", 1)
        if not isinstance(pvid, int) or not 1 <= pvid <= 4094:
            _fail(f"{where}: pvid must be a VLAN ID")
        frame_types = port.get("frame_types", "admit-all")
        tagged = _vlan_ids(where, port.get("tagged"))
        if tagged and frame_types == "admit-only-untagged-and-priority-tagged":
            _fail(
                f"{where}: tagged VLANs need frame_types admit-all or admit-only-vlan-tagged"
            )

        entry = {
            "bridge": bridge,
            "interface": name,
            "frame-types": frame_types,
            "pvid": pvid,
        }
        if "comment" in port:
            entry["comment"] = port["comment"]
        if "hw" in port:
            entry["hw"] = bool(port["hw"])
        entry.update(port.get("bridge_port") or {})
        port_data.append(entry)
        order[name] = len(order)

        vlans = members[bridge]
        for vid in tagged:
            vlans.setdefault(vid, {"tagged": set(), "untagged": set()})["tagged"].add(
                name
            )
        if pvid not in tagged and frame_types != "admit-only-vlan-tagged":
            vlans.setdefault(pvid, {"tagged": set(), "untagged": set()})[
                "untagged"
            ].add(name)

    vlan_data = []
    for bridge, vlans in members.items():
        for vid in bridge_cpu_vlans[bridge]:
            vlans.setdefault(vid, {"tagged": set(), "untagged": set()})["tagged"].add(
                cpu_names[bridge]
            )
        if not (bridges[bridge] or {}).get("vlan_filtering"):
            continue
        groups = {}
        for vid in sorted(vlans):
            membership = vlans[vid]
            key = (
                tuple(sorted(membership["tagged"])),
                tuple(sorted(membership["untagged"])),
            )
            if (bridges[bridge] or {}).get("group_vlans"):
                groups.setdefault(key, set()).add(vid)
            else:
                groups[(vid, *key)] = {vid}
        for ids in sorted(groups.values(), key=min):
            membership = vlans[min(ids)]
            # RouterOS reads a single VLAN ID back as a number.
            vlan_ids = _ranges(ids) if len(ids) > 1 else min(ids)
            entry = {"bridge": bridge, "vlan-ids": vlan_ids}
            for kind in ("tagged", "untagged"):
                names = sorted(membership[kind], key=lambda n: order.get(n, -1))
                if names:
                    entry[kind] = ",".join(names)
            vlan_data.append(entry)

    result = {}

    def add(kind, path, data):
        if data:
            result.setdefault(step_names[kind], []).append({"path": path, "data": data})

    add("bridge", "interface bridge", bridge_data)
    add("ethernet", "interface ethernet", ethernet_data)
    add("ethernet", "interface ethernet poe", poe_data)
    add("port", "interface bridge port", port_data)
    add("vlan", "interface bridge vlan", vlan_data)
    return result


def routeros_ssh_fingerprint(public_key):
    """Return the SHA256 fingerprint of an SSH public key the way RouterOS shows it."""
    if not isinstance(public_key, str):
        _fail("the SSH public key must be a string")
    parts = public_key.split()
    blob = parts[1] if len(parts) > 1 else (parts[0] if parts else "")
    try:
        raw = base64.b64decode(blob, validate=True)
    except (binascii.Error, ValueError):
        _fail(f"{public_key[:40]!r} is not an SSH public key")
    if not raw:
        _fail("the SSH public key is empty")
    return "SHA256:" + base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii")


class FilterModule:
    """RouterOS configuration filters."""

    def filters(self):
        return {
            "routeros_config_plan": routeros_config_plan,
            "routeros_config_ports": routeros_config_ports,
            "routeros_ssh_fingerprint": routeros_ssh_fingerprint,
        }
