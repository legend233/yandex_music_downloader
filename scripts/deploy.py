#!/usr/bin/env python3
"""Redeploy yandexdownloader using the definition and Env stored in Portainer.

Required: PORTAINER_URL and PORTAINER_API_TOKEN (X-API-Key).
Optional: PORTAINER_ENDPOINT_NAME, PORTAINER_STACK_NAME, PORTAINER_INSECURE.
--dry-run only reads Portainer. Response bodies and deployment messages are
never logged because they may contain secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_ENDPOINT_NAME = "pve-2-docker"
DEFAULT_STACK_NAME = "yandexdownloader"
HTTP_TIMEOUT_SECONDS = 30
# Older Portainer versions update synchronously, including the image pull.
UPDATE_TIMEOUT_SECONDS = 600
DEPLOY_TIMEOUT_SECONDS = 180
POLL_INTERVAL_SECONDS = 3

STACK_STATUS_ACTIVE = 1
STACK_STATUS_INACTIVE = 2
STACK_STATUS_DEPLOYING = 3
STACK_STATUS_ERROR = 4


class PortainerError(RuntimeError):
    """A safe-to-display Portainer error."""


def _ssl_context():
    context = ssl.create_default_context()
    if os.getenv("PORTAINER_INSECURE", "").strip().lower() in {"1", "true", "yes", "on"}:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _request(base_url, token, method, path, query=None, body=None,
             timeout=HTTP_TIMEOUT_SECONDS):
    url = base_url.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"X-API-Key": token, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, context=_ssl_context(), timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise PortainerError(f"{method} {path}: HTTP {exc.code}") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise PortainerError(f"{method} {path}: request failed") from None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        raise PortainerError(f"{method} {path}: invalid JSON response") from None


def _find_endpoint(base_url, token, name):
    for endpoint in _request(base_url, token, "GET", "/api/endpoints") or []:
        if endpoint.get("Name") == name:
            return endpoint
    raise PortainerError("Requested environment not found in Portainer")


def _find_stack(base_url, token, endpoint_id, name):
    stacks = _request(base_url, token, "GET", "/api/stacks",
                      query={"filters": json.dumps({"EndpointID": endpoint_id})})
    for stack in stacks or []:
        if stack.get("Name") == name and stack.get("EndpointId") == endpoint_id:
            return stack
    raise PortainerError("Requested stack not found on the selected environment")


def _wait_for_deploy(base_url, token, stack_id, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        stack = _request(base_url, token, "GET", f"/api/stacks/{stack_id}")
        status = stack.get("Status")
        if status == STACK_STATUS_ACTIVE:
            print("Stack is active")
            return
        if status == STACK_STATUS_INACTIVE:
            raise PortainerError("Stack is inactive after the update")
        if status == STACK_STATUS_ERROR:
            raise PortainerError("Portainer reported a failed deployment")
        time.sleep(POLL_INTERVAL_SECONDS)
    raise PortainerError(f"Deployment did not finish within {timeout}s")


def _required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise PortainerError(f"Environment variable {name} is required")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description="Redeploy yandexdownloader in Portainer")
    parser.add_argument("--dry-run", action="store_true", help="Only read; do not update the stack")
    args = parser.parse_args(argv)
    base_url = _required_env("PORTAINER_URL")
    token = _required_env("PORTAINER_API_TOKEN")
    endpoint_name = os.getenv("PORTAINER_ENDPOINT_NAME", "").strip() or DEFAULT_ENDPOINT_NAME
    stack_name = os.getenv("PORTAINER_STACK_NAME", "").strip() or DEFAULT_STACK_NAME
    endpoint_id = int(_find_endpoint(base_url, token, endpoint_name)["Id"])
    stack = _find_stack(base_url, token, endpoint_id, stack_name)
    stack_id = int(stack["Id"])
    if args.dry_run:
        print("Dry run: environment and stack found; no update requested")
        return 0

    # Never silently replace missing environment data with an empty list.
    if "Env" not in stack:
        raise PortainerError("Portainer stack response is missing Env")
    stack_file = _request(base_url, token, "GET", f"/api/stacks/{stack_id}/file")
    payload = {
        "StackFileContent": stack_file["StackFileContent"],
        "Env": stack["Env"],
        "Prune": False,
        # Support both synchronous and asynchronous Portainer versions.
        "PullImage": True,
        "RepullImageAndRedeploy": True,
    }
    _request(base_url, token, "PUT", f"/api/stacks/{stack_id}",
             query={"endpointId": str(endpoint_id)}, body=payload,
             timeout=UPDATE_TIMEOUT_SECONDS)
    _wait_for_deploy(base_url, token, stack_id, DEPLOY_TIMEOUT_SECONDS)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PortainerError as exc:
        print(f"Deploy failed: {exc}", file=sys.stderr)
        sys.exit(1)
