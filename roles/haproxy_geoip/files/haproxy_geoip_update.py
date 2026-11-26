"""Keeps HAProxy's country lists up to date.

    haproxy-geoip-update [--config FILE]            download, then build
    haproxy-geoip-update [--config FILE] --offline  only build, from disk
    haproxy-geoip-update --seeds DIR COUNTRY...     write seeds to DIR

The prefixes come from DB-IP's IP to Country Lite, which places addresses
where they're used, rather than where the block is registered. IP
Geolocation by DB-IP (https://db-ip.com), CC BY 4.0. It's published
monthly, so a month that has been applied isn't downloaded again, unless a
country has no prefixes yet.

Each country's prefixes are kept in countries/<code>.lst, the last good
download, or a seed until there has been one. A
download that fails, or a country that looks broken in it (fewer IPv4
prefixes than the minimum, or less than half as many as before), keeps the
last good file. The lists are then built from those files, and HAProxy is
reloaded if one of them changed. So the lists always exist, and only get
older while the downloads fail. The exit status is 1 if something failed,
so that systemd retries.
"""

import argparse
import csv
import datetime
import gzip
import ipaddress
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

URL = "https://download.db-ip.com/free/dbip-country-lite-{month}.csv.gz"
ATTRIBUTION = "IP Geolocation by DB-IP (https://db-ip.com), CC BY 4.0"
# The whole database has over 700,000 ranges. Far fewer means it's cut off.
MIN_RANGES = 100_000


def log(message):
    print(message, file=sys.stderr)


def months():
    """This month and the one before, as DB-IP names them."""
    today = datetime.date.today()
    last = today.replace(day=1) - datetime.timedelta(days=1)
    return [today.strftime("%Y-%m"), last.strftime("%Y-%m")]


def download(month, path):
    """Downloads a month's database to path. False if it isn't out yet."""
    request = urllib.request.Request(
        URL.format(month=month), headers={"User-Agent": "haproxy-geoip-update"}
    )
    for attempt in range(3):
        try:
            with (
                urllib.request.urlopen(request, timeout=120) as response,
                open(path, "wb") as f,
            ):
                while chunk := response.read(1 << 20):
                    f.write(chunk)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            error = e
        except OSError as e:
            error = e
    raise OSError(f"downloading {month}: {error}")


def read_database(path, countries):
    """The prefixes of the countries, from a downloaded database."""
    ranges = {country: [] for country in countries}
    count = 0
    with gzip.open(path, "rt", newline="") as f:
        for row in csv.reader(f):
            count += 1
            country = row[2].lower()
            if country in ranges:
                first, last = ipaddress.ip_address(row[0]), ipaddress.ip_address(row[1])
                ranges[country].extend(ipaddress.summarize_address_range(first, last))
    if count < MIN_RANGES:
        raise ValueError(f"only {count} ranges in the database")
    return {country: collapse(networks) for country, networks in ranges.items()}


def collapse(networks):
    """Sorted, with neighbours joined, IPv4 first."""
    networks = list(networks)
    return [
        network
        for version in (4, 6)
        for network in ipaddress.collapse_addresses(
            n for n in networks if n.version == version
        )
    ]


def read_list(path):
    """The prefixes in a list file, or None if there's none."""
    try:
        with open(path) as f:
            return [
                ipaddress.ip_network(line.strip())
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        return None


def ipv4_count(networks):
    return sum(1 for network in networks if network.version == 4)


def write_if_changed(path, header, networks):
    """Writes the file atomically. True if its content changed."""
    content = "".join(f"# {line}\n" for line in header) + "".join(
        f"{n}\n" for n in networks
    )
    try:
        with open(path) as f:
            if f.read() == content:
                return False
    except FileNotFoundError:
        pass
    directory = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile("w", dir=directory, delete=False) as f:
        f.write(content)
    os.chmod(f.name, 0o644)
    os.replace(f.name, path)
    return True


def update_countries(directory, countries, minimum, month, path):
    """Writes the countries from a database. False if one looked broken."""
    ok = True
    for country, networks in read_database(path, countries).items():
        file = os.path.join(directory, f"{country}.lst")
        old = read_list(file) or []
        count, before = ipv4_count(networks), ipv4_count(old)
        if count < minimum or count < before // 2:
            log(
                f"{country}: {count} IPv4 prefixes in {month}, against {before} before; keeping the last good prefixes"
            )
            ok = False
            continue
        header = [f"{country.upper()} from dbip-country-lite-{month}", ATTRIBUTION]
        if write_if_changed(file, header, networks):
            print(
                f"{country}: updated from {month}, {count} IPv4 and {len(networks) - count} IPv6 prefixes"
            )
    return ok


def refresh(config):
    """Downloads the newest month, unless it has been applied. False on failure."""
    directory = os.path.join(config["dir"], "countries")
    state = os.path.join(config["dir"], "month")
    countries = sorted({c.lower() for codes in config["lists"].values() for c in codes})
    try:
        with open(state) as f:
            applied = f.read().strip()
    except FileNotFoundError:
        applied = None
    # A country added since the month was applied has nothing to keep yet.
    missing = any(
        not os.path.exists(os.path.join(directory, f"{c}.lst")) for c in countries
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "dbip.csv.gz")
        for month in months():
            if month == applied and not missing:
                return True
            try:
                if not download(month, path):
                    continue
                ok = update_countries(
                    directory, countries, config["min_prefixes"], month, path
                )
            except (OSError, ValueError, csv.Error, EOFError) as e:
                log(f"{month}: {e}; keeping the last good prefixes")
                return False
            # Also when a country looked broken: the same month would only
            # give the same prefixes again. It keeps its last good ones until
            # the next month is out.
            with open(state, "w") as f:
                f.write(f"{month}\n")
            return ok
    log(f"neither {' nor '.join(months())} is out; keeping the last good prefixes")
    return False


def build(config):
    """Builds the lists from the country files. Returns (changed, ok)."""
    directory = config["dir"]
    changed, ok = False, True
    for name, codes in sorted(config["lists"].items()):
        codes = [c.lower() for c in codes]
        networks = []
        for code in codes:
            country = read_list(os.path.join(directory, "countries", f"{code}.lst"))
            if not country:
                # The seed is always there, so this only happens if it was removed.
                log(f"{name}: no prefixes for {code}, leaving the list as it is")
                ok = False
                break
            networks.extend(country)
        else:
            header = [f"{name}: {', '.join(c.upper() for c in codes)}", ATTRIBUTION]
            if write_if_changed(
                os.path.join(directory, f"{name}.lst"), header, collapse(networks)
            ):
                print(f"{name}: changed")
                changed = True
    return changed, ok


def reload_haproxy():
    """Reloads HAProxy if it runs. False if that failed. The reload checks
    the configuration first, and HAProxy keeps running with the old lists if
    that fails."""
    try:
        active = subprocess.run(
            ["systemctl", "-q", "is-active", "haproxy"], check=False
        )
        if active.returncode == 0:
            subprocess.run(["systemctl", "reload", "haproxy"], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        log(f"reloading HAProxy: {e}")
        return False
    return True


def seeds(directory, countries):
    """Writes the countries to directory, from the newest month that's out."""
    os.makedirs(directory, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "dbip.csv.gz")
        for month in months():
            if download(month, path):
                return update_countries(
                    directory, [c.lower() for c in countries], 50, month, path
                )
    log(f"neither {' nor '.join(months())} is out")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    parser.add_argument("--config", default="/etc/haproxy/geoip/config.json")
    parser.add_argument(
        "--offline", action="store_true", help="only build, from the countries on disk"
    )
    parser.add_argument(
        "--seeds", metavar="DIR", help="write the countries to DIR, as seeds"
    )
    parser.add_argument(
        "countries", nargs="*", help="with --seeds: the countries' ISO codes"
    )
    args = parser.parse_args()

    if args.seeds:
        return 0 if seeds(args.seeds, args.countries) else 1

    with open(args.config) as f:
        config = json.load(f)
    ok = True
    if not args.offline:
        ok = refresh(config)
    changed, built = build(config)
    # Until a reload works, so that a failed one is tried again even though
    # the lists don't change again.
    pending = os.path.join(config["dir"], "reload-pending")
    if changed:
        open(pending, "w").close()
    reloaded = True
    if os.path.exists(pending):
        reloaded = reload_haproxy()
        if reloaded:
            os.remove(pending)
    return 0 if ok and built and reloaded else 1


if __name__ == "__main__":
    sys.exit(main())
