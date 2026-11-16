# Copyright: (c) 2026, pypb
# Apache License 2.0 (see LICENSE or https://www.apache.org/licenses/LICENSE-2.0)

from __future__ import annotations

import pytest
from ansible.errors import AnsibleFilterError
from ansible_collections.pypb.homelab.plugins.filter.routeros import (
    routeros_config_plan,
    routeros_config_ports,
    routeros_ssh_fingerprint,
)

API_MODIFY = "community.routeros.api_modify"
FIND = "community.routeros.api_find_and_modify"
COMMAND = "community.routeros.command"


def steps_of(plan):
    return [(item["step"], item["module"], item["path"]) for item in plan]


def test_orders_steps_by_number_then_operations_as_listed():
    plan = routeros_config_plan(
        {
            "1000_late": [
                {"path": "disk settings", "data": [{"auto-smb-sharing": False}]}
            ],
            "900_early": [
                {"command": "/one"},
                {
                    "path": "system leds",
                    "find": {"interface": "ether1"},
                    "values": {"disabled": True},
                },
                {"path": "system identity", "data": [{"name": "r1"}]},
            ],
        }
    )
    assert steps_of(plan) == [
        ("900_early", COMMAND, ""),
        ("900_early", FIND, "system leds"),
        ("900_early", API_MODIFY, "system identity"),
        ("1000_late", API_MODIFY, "disk settings"),
    ]
    assert plan[0]["args"] == {"commands": ["/one"]}


def test_layers_appended_to_one_step_keep_all_entries():
    # What merge_variables produces from a global and a host layer that both use
    # 0100_system: the host's leds no longer replace the global identity.
    plan = routeros_config_plan(
        {
            "0100_system": [
                {
                    "path": "system clock",
                    "data": [{"time-zone-name": "Europe/Stockholm"}],
                },
                {"path": "system identity", "data": [{"name": "ap1"}]},
                {
                    "path": "system leds settings",
                    "data": [{"all-leds-off": "after-1min"}],
                },
            ]
        }
    )
    assert [item["path"] for item in plan] == [
        "system clock",
        "system identity",
        "system leds settings",
    ]


def test_same_path_in_a_step_is_one_call():
    plan = routeros_config_plan(
        {
            "0150_users": [
                {"path": "user", "data": [{"name": "a"}]},
                {
                    "path": "user",
                    "data": [{"name": "b"}],
                    "handle_absent_entries": "remove",
                },
                {"path": "user  ", "data": [{"name": "c"}]},
            ]
        }
    )
    assert len(plan) == 1
    assert plan[0]["args"]["data"] == [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    assert plan[0]["args"]["handle_absent_entries"] == "remove"


def test_default_handle_absent_entries():
    plan = routeros_config_plan(
        {"0300_ip": [{"path": "ip pool", "data": []}]}, "remove"
    )
    assert plan[0]["args"]["handle_absent_entries"] == "remove"
    plan = routeros_config_plan({"0300_ip": [{"path": "ip pool", "data": []}]})
    assert plan[0]["args"]["handle_absent_entries"] == "ignore"


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        ({"0900_tool": [{"path": "tool mac-server", "modify": []}]}, "exactly one of"),
        (
            {"0900_tool": [{"path": "tool mac-server", "data": [], "find": {}}]},
            "exactly one of",
        ),
        ({"0900_tool": [{"path": "x", "data": [], "vals": {}}]}, "unknown keys"),
        ({"0900_tool": [{"path": "x", "find": {"a": 1}, "vals": {}}]}, "unknown keys"),
        ({"0900_tool": [{"path": "x", "find": {"a": 1}}]}, "values is required"),
        ({"0900_tool": [{"data": []}]}, "path is required"),
        ({"0900_tool": [{"path": "x", "data": {}}]}, "list of dicts"),
        ({"0900_tool": [{"command": []}]}, "string or a list"),
        ({"tool": []}, "the name must be"),
        ({"0900_tool": {"path": "x"}}, "must be a list"),
        (
            {
                "0900_tool": [
                    {"path": "x", "data": [], "ensure_order": True},
                    {"path": "x", "data": [], "ensure_order": False},
                ]
            },
            "ensure_order",
        ),
        (
            {
                "0100_a": [
                    {"path": "x", "data": [], "handle_absent_entries": "remove"}
                ],
                "0200_b": [{"path": "x", "data": []}],
            },
            "in one step",
        ),
    ],
)
def test_invalid_steps_fail(steps, message):
    with pytest.raises(AnsibleFilterError, match=message):
        routeros_config_plan(steps)


def test_same_path_in_two_steps_is_allowed_without_remove():
    plan = routeros_config_plan(
        {"0100_a": [{"path": "x", "data": []}], "0200_b": [{"path": "x", "data": []}]}
    )
    assert len(plan) == 2


BRIDGES = {
    "bridge": {"vlan_filtering": False},
    "bridge1": {"vlan_filtering": True, "tagged_vlans": [1, "10-11"]},
}
PORTS = {
    "ether2": {
        "comment": "ap",
        "bridge": "bridge1",
        "tagged": ["1", "10-12"],
        "hw": True,
        "poe": {"poe-out": "forced-on"},
    },
    "ether10": {
        "comment": "printer",
        "bridge": "bridge1",
        "pvid": 13,
        "frame_types": "admit-only-untagged-and-priority-tagged",
    },
    "ether4": {"comment": "router", "bridge": "bridge1", "tagged": [10]},
    "ether17": {"comment": "nas port 1", "poe": {"poe-out": "off"}},
    "bond1": {
        "bridge": "bridge1",
        "tagged": "12",
        "frame_types": "admit-only-vlan-tagged",
    },
    "ether24": {"bridge": "bridge", "hw": False},
}


def ops(steps, path):
    for step_ops in steps.values():
        for op in step_ops:
            if op["path"] == path:
                return op["data"]
    return None


def test_ports_render_each_path():
    steps = routeros_config_ports(PORTS, BRIDGES)
    assert sorted(steps) == [
        "0200_bridge",
        "0200_ethernet",
        "0220_bridge_port",
        "0230_bridge_vlan",
    ]
    assert ops(steps, "interface bridge") == [
        {"name": "bridge", "vlan-filtering": False},
        {"name": "bridge1", "vlan-filtering": True},
    ]
    # Entries follow the order of the ports.
    assert ops(steps, "interface ethernet") == [
        {"default-name": "ether2", "comment": "ap"},
        {"default-name": "ether10", "comment": "printer"},
        {"default-name": "ether4", "comment": "router"},
        {"default-name": "ether17", "comment": "nas port 1"},
    ]
    assert ops(steps, "interface ethernet poe") == [
        {"name": "ether2", "poe-out": "forced-on"},
        {"name": "ether17", "poe-out": "off"},
    ]
    assert [p["interface"] for p in ops(steps, "interface bridge port")] == [
        "ether2",
        "ether10",
        "ether4",
        "bond1",
        "ether24",
    ]
    assert ops(steps, "interface bridge port")[0] == {
        "bridge": "bridge1",
        "interface": "ether2",
        "frame-types": "admit-all",
        "pvid": 1,
        "comment": "ap",
        "hw": True,
    }


def test_ports_bridge_vlan_membership():
    vlans = ops(routeros_config_ports(PORTS, BRIDGES), "interface bridge vlan")
    assert vlans == [
        # ether4 has PVID 1 and doesn't tag it, so it is untagged there.
        {
            "bridge": "bridge1",
            "vlan-ids": 1,
            "tagged": "bridge1,ether2",
            "untagged": "ether4",
        },
        {"bridge": "bridge1", "vlan-ids": 10, "tagged": "bridge1,ether2,ether4"},
        {"bridge": "bridge1", "vlan-ids": 11, "tagged": "bridge1,ether2"},
        # Members follow the order of the ports, as RouterOS lists them.
        {"bridge": "bridge1", "vlan-ids": 12, "tagged": "ether2,bond1"},
        {"bridge": "bridge1", "vlan-ids": 13, "untagged": "ether10"},
    ]


def test_ports_cpu_interface_names_the_bridge_itself():
    bridges = {
        "bridge1": {
            "vlan_filtering": True,
            "tagged_vlans": [1],
            "cpu_interface": "bridge",
        }
    }
    vlans = ops(
        routeros_config_ports(
            {"ether1": {"bridge": "bridge1", "tagged": [1]}}, bridges
        ),
        "interface bridge vlan",
    )
    assert vlans == [{"bridge": "bridge1", "vlan-ids": 1, "tagged": "bridge,ether1"}]


def test_ports_group_vlans_with_the_same_members():
    bridges = {
        "bridge": {
            "vlan_filtering": True,
            "group_vlans": True,
            "tagged_vlans": [10, 11, 13, 14],
        }
    }
    ports = {
        f"ether{n}": {"bridge": "bridge", "tagged": ["10-11", "13-14"]}
        for n in range(1, 6)
    }
    vlans = ops(routeros_config_ports(ports, bridges), "interface bridge vlan")
    assert vlans == [
        {
            "bridge": "bridge",
            "vlan-ids": 1,
            "untagged": "ether1,ether2,ether3,ether4,ether5",
        },
        {
            "bridge": "bridge",
            "vlan-ids": "10-11,13-14",
            "tagged": "bridge,ether1,ether2,ether3,ether4,ether5",
        },
    ]


def test_ports_custom_steps_and_ethernet_override():
    steps = routeros_config_ports(
        {
            "wlan1": {"comment": "x", "ethernet": {"comment": "y", "l2mtu": 1600}},
            "ether1": {"ethernet": False, "comment": "z"},
        },
        steps={"ethernet": "0300_eth"},
    )
    assert steps == {
        "0300_eth": [
            {
                "path": "interface ethernet",
                "data": [{"default-name": "wlan1", "comment": "y", "l2mtu": 1600}],
            }
        ]
    }


@pytest.mark.parametrize(
    ("ports", "bridges", "message"),
    [
        ({"ether1": {"bridge": "nope"}}, {}, "not in routeros_config_bridges"),
        ({"ether1": {"pvid": 10}}, {}, "needs a bridge"),
        ({"ether1": {"colour": "red"}}, {}, "unknown keys"),
        ({"ether1": {"bridge": "b", "tagged": ["5000"]}}, {"b": {}}, "outside"),
        ({"ether1": {"bridge": "b", "tagged": ["a-b"]}}, {"b": {}}, "not a VLAN"),
        (
            {
                "ether1": {
                    "bridge": "b",
                    "tagged": [10],
                    "frame_types": "admit-only-untagged-and-priority-tagged",
                }
            },
            {"b": {}},
            "tagged VLANs need",
        ),
        ({}, {"b": {"vlan-filtering": True}}, "unknown keys"),
    ],
)
def test_invalid_ports_fail(ports, bridges, message):
    with pytest.raises(AnsibleFilterError, match=message):
        routeros_config_ports(ports, bridges)


def test_ports_output_feeds_the_plan():
    plan = routeros_config_plan(routeros_config_ports(PORTS, BRIDGES))
    assert [item["path"] for item in plan] == [
        "interface bridge",
        "interface ethernet",
        "interface ethernet poe",
        "interface bridge port",
        "interface bridge vlan",
    ]


def test_ssh_fingerprint_matches_routeros():
    # RouterOS keeps the base64 padding that OpenSSH leaves out.
    key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKe4oDqwC8kz4N9/BW8zdE7TroY3t4AFkUPInERixwLC ansible"
    assert (
        routeros_ssh_fingerprint(key)
        == "SHA256:RRt/48RS/Nvf4SfDf0JnY1/9V89jHJjZ4IATBWjOMrs="
    )
    assert routeros_ssh_fingerprint(key.split()[1]) == routeros_ssh_fingerprint(key)


@pytest.mark.parametrize("key", ["", "ssh-ed25519 not-base64!", 42])
def test_ssh_fingerprint_rejects_garbage(key):
    with pytest.raises(AnsibleFilterError):
        routeros_ssh_fingerprint(key)
