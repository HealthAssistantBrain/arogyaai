#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json

import websockets
from websockets.exceptions import ConnectionClosedError


async def probe(url: str, timeout: float, expect_policy_close: bool) -> None:
    try:
        async with websockets.connect(url, open_timeout=timeout, close_timeout=timeout) as websocket:
            await websocket.send(json.dumps({"type": "ci.ping"}))
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            except asyncio.TimeoutError:
                message = "<no immediate message>"
            print(f"[WEBSOCKET] Connected to {url}; first_message={message}")
    except ConnectionClosedError as exc:
        if expect_policy_close and exc.code == 1008:
            print(f"[WEBSOCKET] Endpoint is reachable and enforced auth policy close code={exc.code}.")
            return
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe ArogyaAI websocket endpoint.")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--expect-policy-close", action="store_true")
    args = parser.parse_args()
    asyncio.run(probe(args.url, args.timeout, args.expect_policy_close))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
