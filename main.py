import asyncio
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from curl_cffi.requests import AsyncSession

DEFAULT_MIN_AUM = float(os.getenv("DEFAULT_MIN_AUM", "50000"))
SCAN_PAGES = int(os.getenv("SCAN_PAGES", "3"))          # 3 sayfa ~ 60 lider (Render Free RAM dostu)
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "90"))    # Saniye cinsinden tarama aralığı
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "4"))

CACHE = {
    "last_updated": None,
    "scanned_leaders": 0,
    "min_aum": DEFAULT_MIN_AUM,
    "leaders": [],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "clienttype": "web",
}


def extract_entry_price(pos: dict) -> float:
    for key in ("entryPrice", "avgEntryPrice", "openPrice"):
        val = pos.get(key)
        if val is not None:
            try:
                price = float(val)
                if price > 0:
                    return price
            except (ValueError, TypeError):
                pass
    return 0.0


def build_coin_summary(leaders_data: list, min_aum: float):
    coin_map = defaultdict(
        lambda: {
            "long_count": 0,
            "short_count": 0,
            "long_vol": 0.0,
            "short_vol": 0.0,
            "total_vol": 0.0,
            "long_weighted_entry_sum": 0.0,
            "long_entry_vol_sum": 0.0,
            "short_weighted_entry_sum": 0.0,
            "short_entry_vol_sum": 0.0,
            "traders": [],
        }
    )

    filtered_leaders = 0
    visible_leaders = 0

    for leader in leaders_data:
        if leader["aum"] < min_aum:
            continue
        filtered_leaders += 1
        positions = leader["positions"]
        if positions:
            visible_leaders += 1

        for p in positions:
            sym = p["symbol"]
            amt = float(p.get("positionAmount", 0))
            notional = abs(float(p.get("notionalValue", 0)))
            entry = extract_entry_price(p)

            if notional <= 0 and entry > 0:
                notional = abs(amt) * entry

            side = p.get("positionSide", "BOTH")
            if side == "BOTH":
                side = "LONG" if amt > 0 else "SHORT"

            if side == "LONG":
                coin_map[sym]["long_count"] += 1
                coin_map[sym]["long_vol"] += notional
                if entry > 0 and notional > 0:
                    coin_map[sym]["long_weighted_entry_sum"] += entry * notional
                    coin_map[sym]["long_entry_vol_sum"] += notional
            elif side == "SHORT":
                coin_map[sym]["short_count"] += 1
                coin_map[sym]["short_vol"] += notional
                if entry > 0 and notional > 0:
                    coin_map[sym]["short_weighted_entry_sum"] += entry * notional
                    coin_map[sym]["short_entry_vol_sum"] += notional
            else:
                continue

            coin_map[sym]["total_vol"] += notional
            coin_map[sym]["traders"].append(
                {
                    "id": leader["id"],
                    "name": leader["name"],
                    "aum": round(leader["aum"], 2),
                    "side": side,
                    "notional": round(notional, 2),
                    "entry_price": round(entry, 6) if entry > 0 else 0.0,
                    "amount": abs(amt),
                }
            )

    formatted_coins = []
    for sym, d in coin_map.items():
        total = d["long_count"] + d["short_count"]
        long_pct = round((d["long_count"] / total) * 100, 1) if total > 0 else 0.0

        long_avg_entry = (
            d["long_weighted_entry_sum"] / d["long_entry_vol_sum"]
            if d["long_entry_vol_sum"] > 0
            else 0.0
        )
        short_avg_entry = (
            d["short_weighted_entry_sum"] / d["short_entry_vol_sum"]
            if d["short_entry_vol_sum"] > 0
            else 0.0
        )

        sorted_traders = sorted(d["traders"], key=lambda t: t["notional"], reverse=True)

        formatted_coins.append(
            {
                "symbol": sym,
                "total": total,
                "long_count": d["long_count"],
                "short_count": d["short_count"],
                "long_vol": round(d["long_vol"], 2),
                "short_vol": round(d["short_vol"], 2),
                "total_vol": round(d["total_vol"], 2),
                "long_avg_entry": round(long_avg_entry, 6),
                "short_avg_entry": round(short_avg_entry, 6),
                "long_pct": long_pct,
                "short_pct": round(100 - long_pct, 1),
                "traders": sorted_traders,
            }
        )

    formatted_coins.sort(key=lambda x: x["total"], reverse=True)
    return {
        "last_updated": CACHE["last_updated"],
        "scanned_leaders": CACHE["scanned_leaders"],
        "filtered_leaders": filtered_leaders,
        "visible_leaders": visible_leaders,
        "min_aum": min_aum,
        "coins": formatted_coins,
    }


async def fetch_leaders(session: AsyncSession, pages: int = SCAN_PAGES):
    url = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/home-page/query-list"
    leaders_by_id = {}

    for page in range(1, pages + 1):
        payload = {
            "pageNumber": page,
            "pageSize": 20,
            "timeRange": "30D",
            "dataType": "PNL",
            "favoriteOnly": False,
            "hideFull": False,
            "nickname": "",
            "order": "DESC",
        }
        try:
            resp = await session.post(url, json=payload, headers=HEADERS, timeout=12)
            data = resp.json()
            if data.get("success") and data.get("data", {}).get("list"):
                for item in data["data"]["list"]:
                    pid = item["leadPortfolioId"]
                    aum = float(item.get("aumAmount", 0) or 0)
                    leaders_by_id[pid] = {
                        "id": pid,
                        "name": item.get("nickname", "Unknown"),
                        "aum": aum,
                    }
        except Exception:
            pass
        await asyncio.sleep(0.25)

    return list(leaders_by_id.values())


async def fetch_positions(session: AsyncSession, semaphore: asyncio.Semaphore, leader: dict):
    url = (
        "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/"
        f"lead-data/positions?portfolioId={leader['id']}"
    )
    positions = []
    async with semaphore:
        try:
            await asyncio.sleep(0.2)
            resp = await session.get(url, headers=HEADERS, timeout=12)
            data = resp.json()
            if data.get("success") and data.get("data"):
                positions = [
                    p for p in data["data"] if float(p.get("positionAmount", 0)) != 0
                ]
        except Exception:
            pass

    return {
        "id": leader["id"],
        "name": leader["name"],
        "aum": leader["aum"],
        "positions": positions,
    }


async def scanner_loop():
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    while True:
        try:
            async with AsyncSession(impersonate="chrome120") as session:
                leaders = await fetch_leaders(session, pages=SCAN_PAGES)
                tasks = [fetch_positions(session, semaphore, leader) for leader in leaders]
                detailed_leaders = await asyncio.gather(*tasks)

                CACHE["last_updated"] = time.strftime("%H:%M:%S")
                CACHE["scanned_leaders"] = len(detailed_leaders)
                CACHE["leaders"] = detailed_leaders
        except Exception:
            pass

        await asyncio.sleep(SCAN_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scanner_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok", "last_updated": CACHE["last_updated"]})


@app.get("/")
async def serve_ui():
    html_path = Path("static/index.html")
    return FileResponse(html_path)


@app.get("/api/positions")
async def get_positions(min_aum: float = Query(default=DEFAULT_MIN_AUM, ge=0)):
    return build_coin_summary(CACHE["leaders"], min_aum=min_aum)
