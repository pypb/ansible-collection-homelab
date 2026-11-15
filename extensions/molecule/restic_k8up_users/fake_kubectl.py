"""Stands in for kubectl in the tests, keeping Schedules and Secrets as files.

Usage: fake_kubectl.py STATE_DIR <kubectl arguments>
Understands only the commands that the restic_k8up_users role runs.
"""

import base64
import json
import pathlib
import sys


def secret_path(state, namespace, name):
    return state / "secrets" / f"{namespace}_{name}.json"


def get_secret(state, args):
    namespace = args[args.index("--namespace") + 1]
    name = args[args.index("--namespace") + 2]
    output = args[args.index("--output") + 1]
    path = secret_path(state, namespace, name)
    if not path.exists():
        return
    key = output.removeprefix("jsonpath={.data.").removesuffix("}").replace("\\.", ".")
    data = json.loads(path.read_text())["data"]
    sys.stdout.write(data.get(key, ""))


def apply(state):
    secret = json.loads(sys.stdin.read())
    meta = secret["metadata"]
    data = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in secret.pop("stringData").items()
    }
    secret["data"] = data
    path = secret_path(state, meta["namespace"], meta["name"])
    if not path.exists():
        verb = "created"
    elif json.loads(path.read_text()) == secret:
        verb = "unchanged"
    else:
        verb = "configured"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(secret))
    print(f"secret/{meta['name']} {verb}")


def main():
    state = pathlib.Path(sys.argv[1])
    args = sys.argv[2:]
    if args[:2] == ["get", "schedules.k8up.io"]:
        print((state / "schedules.json").read_text())
    elif args[:2] == ["get", "secret"]:
        get_secret(state, args)
    elif args[:3] == ["apply", "--filename", "-"]:
        apply(state)
    else:
        sys.exit(f"fake_kubectl: unsupported arguments {args}")


if __name__ == "__main__":
    main()
