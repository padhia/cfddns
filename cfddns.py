#! /usr/bin/env python
"Update Cloudflare IP address for DNS A record"
import json
import os
from argparse import ArgumentParser, ArgumentTypeError
from dataclasses import dataclass
from http.client import HTTPSConnection
from pathlib import Path
from typing import Any

__version__ = "0.1.0"


@dataclass
class CloudflareAPI:
    client: HTTPSConnection
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}

    def get(self, url: str) -> dict[str, Any]:
        self.client.request("GET", url, headers=self.headers)
        return json.loads(self.client.getresponse().read().decode().strip())

    def put(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.client.request("PUT", url, json.dumps(payload), headers=self.headers)
        return json.loads(self.client.getresponse().read().decode().strip())


def get_zone_id(ep: CloudflareAPI, zone: str) -> str:
    resp = ep.get(f"/client/v4/zones?name={zone}&status=active")
    return resp["result"][0]["id"]


def get_dns_record_id(ep: CloudflareAPI, zone_id: str, dns_record: str) -> str:
    resp = ep.get(f"/client/v4/zones/{zone_id}/dns_records?type=A&name={dns_record}")
    return resp["result"][0]["id"]


def update_dns(ep: CloudflareAPI, zone_id: str, dns_record_id: str, dns_record: str, ip: str) -> str:
    resp = ep.put(
        f"/client/v4/zones/{zone_id}/dns_records/{dns_record_id}",
        {
            "content": ip,
            "name": dns_record,
            "proxied": False,
            "type": "A",
            "ttl": 1,
        },
    )
    return f"{resp['result']['name']} -> {resp['result']['content']}" if resp["success"] else resp["errors"]


def get_ip() -> str:
    conn = HTTPSConnection("checkip.amazonaws.com")
    conn.request("GET", "")

    return conn.getresponse().read().decode().strip()


def main(token: str | None, zone: str | None, sub_domain: list[str]) -> None:
    "for each DNS record, update with current IP"
    ip = get_ip()

    cf_api = CloudflareAPI(HTTPSConnection("api.cloudflare.com"), token or os.environ["CLOUDFLARE_API_TOKEN"])

    if zone is None:
        zone = ".".join(sub_domain[0].rsplit(".", 2)[-2:])

    for dns_record in sub_domain:
        zone_id = get_zone_id(cf_api, zone)
        dns_record_id = get_dns_record_id(cf_api, zone_id, dns_record)

        print(update_dns(cf_api, zone_id, dns_record_id, dns_record, ip))


def getargs() -> dict[str, Any]:
    def token_file(s: str) -> str:
        if (p := Path(s)).is_file():
            return p.read_text().strip()
        raise ArgumentTypeError("Token could not be read")

    p = ArgumentParser(description=__doc__)
    p.add_argument(
        "-f",
        "--file",
        type=token_file,
        metavar="FILE",
        required="CLOUDFLARE_API_TOKEN" not in os.environ,
        dest="token",
        help="file containing Cloudflare API token (default $CLOUDFLARE_API_TOKEN)",
    )
    p.add_argument("--zone", help="zone name (default: same as domain name)")
    p.add_argument("sub_domain", nargs="+", help="sub-domain (e.g. www.example.com)")
    p.add_argument("--version", action="version", version=__version__)

    return vars(p.parse_args())


if __name__ == "__main__":
    main(**getargs())
