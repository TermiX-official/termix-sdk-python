"""M4 acceptance: read-only closed loop against prod BSC (no secrets).
Run: python examples/read_loop.py   (or TERMIX_CHAIN=base ...)"""
from __future__ import annotations

import asyncio
import os

from termix_platform_sdk import create_client, from_base_units, to_base_units

failures = 0


def check(label: str, ok: bool, detail: object = None) -> None:
    global failures
    print(f"  {'✓' if ok else '✗'} {label}" + (f"  -> {detail!r}" if detail is not None else ""))
    if not ok:
        failures += 1


async def main() -> None:
    chain = os.environ.get("TERMIX_CHAIN", "bsc")
    base_url = os.environ.get("TERMIX_BASE_URL")
    print(f"\nTermiX Platform SDK (Python) — read-loop (chain={chain})\n")
    client = await create_client(chain=chain, base_url=base_url)
    try:
        cfg = await client.contracts()
        check("chainId is int", isinstance(cfg["chainId"], int), cfg["chainId"])
        check("escrow address", isinstance(cfg["contracts"]["escrow"]["address"], str), cfg["contracts"]["escrow"]["address"])
        dec = cfg["settlementCurrency"]["decimals"]
        check("settlement decimals", isinstance(dec, int), dec)

        stats = await client.stats.network()
        check("latestBlock is str", isinstance(stats["latestBlock"], str), stats["latestBlock"])

        listings = await client.listings.list(pageSize=3)
        check("pagination wrapper", all(isinstance(listings[k], int) for k in ("page", "pageSize", "total", "totalPages")))
        check("items list", isinstance(listings["items"], list), len(listings["items"]))
        first = listings["items"][0] if listings["items"] else None
        if first:
            check("basePrice is str", isinstance(first["basePrice"], str), first["basePrice"])
            detail = await client.listings.get(first["id"])
            check("detail id matches", detail["id"] == first["id"], detail["id"])

        agents = await client.explorer.agents(pageSize=3)
        check("explorer items", isinstance(agents["items"], list), len(agents["items"]))

        sample = first["basePrice"] if first else "1.5"
        rt = from_base_units(to_base_units(sample, dec), dec)
        norm = sample.rstrip("0").rstrip(".") if "." in sample else sample
        check("money round-trip", rt == norm, {"in": sample, "out": rt})

        print(f"\n{'ALL PASS' if failures == 0 else str(failures) + ' FAILED'}\n")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
    raise SystemExit(0 if failures == 0 else 1)
