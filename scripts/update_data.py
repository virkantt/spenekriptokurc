#!/usr/bin/env python3
"""Refresh static market snapshots and news for the Atlas Markets GitHub Pages app.

The website itself is static. This script is intended to run in GitHub Actions so
API keys stay in repository secrets rather than in public browser JavaScript.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MARKET_PATH = DATA_DIR / "market-data.json"
NEWS_PATH = DATA_DIR / "news.json"
USER_AGENT = "spenekriptokurc-market-dashboard/1.0 (+https://github.com/virkantt/spenekriptokurc)"
TIMEOUT = 30

ASSETS = [{'id': 'crypto:bitcoin', 'provider': 'coingecko', 'providerId': 'bitcoin', 'name': 'Bitcoin', 'symbol': 'BTC', 'assetClass': 'crypto'}, {'id': 'crypto:ethereum', 'provider': 'coingecko', 'providerId': 'ethereum', 'name': 'Ethereum', 'symbol': 'ETH', 'assetClass': 'crypto'}, {'id': 'crypto:solana', 'provider': 'coingecko', 'providerId': 'solana', 'name': 'Solana', 'symbol': 'SOL', 'assetClass': 'crypto'}, {'id': 'crypto:binancecoin', 'provider': 'coingecko', 'providerId': 'binancecoin', 'name': 'BNB', 'symbol': 'BNB', 'assetClass': 'crypto'}, {'id': 'crypto:ripple', 'provider': 'coingecko', 'providerId': 'ripple', 'name': 'XRP', 'symbol': 'XRP', 'assetClass': 'crypto'}, {'id': 'crypto:cardano', 'provider': 'coingecko', 'providerId': 'cardano', 'name': 'Cardano', 'symbol': 'ADA', 'assetClass': 'crypto'}, {'id': 'crypto:dogecoin', 'provider': 'coingecko', 'providerId': 'dogecoin', 'name': 'Dogecoin', 'symbol': 'DOGE', 'assetClass': 'crypto'}, {'id': 'crypto:avalanche-2', 'provider': 'coingecko', 'providerId': 'avalanche-2', 'name': 'Avalanche', 'symbol': 'AVAX', 'assetClass': 'crypto'}, {'id': 'crypto:chainlink', 'provider': 'coingecko', 'providerId': 'chainlink', 'name': 'Chainlink', 'symbol': 'LINK', 'assetClass': 'crypto'}, {'id': 'crypto:polkadot', 'provider': 'coingecko', 'providerId': 'polkadot', 'name': 'Polkadot', 'symbol': 'DOT', 'assetClass': 'crypto'}, {'id': 'crypto:litecoin', 'provider': 'coingecko', 'providerId': 'litecoin', 'name': 'Litecoin', 'symbol': 'LTC', 'assetClass': 'crypto'}, {'id': 'crypto:tron', 'provider': 'coingecko', 'providerId': 'tron', 'name': 'TRON', 'symbol': 'TRX', 'assetClass': 'crypto'}, {'id': 'crypto:stellar', 'provider': 'coingecko', 'providerId': 'stellar', 'name': 'Stellar', 'symbol': 'XLM', 'assetClass': 'crypto'}, {'id': 'crypto:uniswap', 'provider': 'coingecko', 'providerId': 'uniswap', 'name': 'Uniswap', 'symbol': 'UNI', 'assetClass': 'crypto'}, {'id': 'crypto:bitcoin-cash', 'provider': 'coingecko', 'providerId': 'bitcoin-cash', 'name': 'Bitcoin Cash', 'symbol': 'BCH', 'assetClass': 'crypto'}, {'id': 'stock:aapl', 'provider': 'finance', 'providerId': 'AAPL', 'name': 'Apple', 'symbol': 'AAPL', 'assetClass': 'stock'}, {'id': 'stock:msft', 'provider': 'finance', 'providerId': 'MSFT', 'name': 'Microsoft', 'symbol': 'MSFT', 'assetClass': 'stock'}, {'id': 'stock:nvda', 'provider': 'finance', 'providerId': 'NVDA', 'name': 'NVIDIA', 'symbol': 'NVDA', 'assetClass': 'stock'}, {'id': 'stock:amzn', 'provider': 'finance', 'providerId': 'AMZN', 'name': 'Amazon', 'symbol': 'AMZN', 'assetClass': 'stock'}, {'id': 'stock:googl', 'provider': 'finance', 'providerId': 'GOOGL', 'name': 'Alphabet', 'symbol': 'GOOGL', 'assetClass': 'stock'}, {'id': 'stock:meta', 'provider': 'finance', 'providerId': 'META', 'name': 'Meta Platforms', 'symbol': 'META', 'assetClass': 'stock'}, {'id': 'stock:tsla', 'provider': 'finance', 'providerId': 'TSLA', 'name': 'Tesla', 'symbol': 'TSLA', 'assetClass': 'stock'}, {'id': 'stock:brk-b', 'provider': 'finance', 'providerId': 'BRK-B', 'name': 'Berkshire Hathaway', 'symbol': 'BRK.B', 'assetClass': 'stock'}, {'id': 'stock:jpm', 'provider': 'finance', 'providerId': 'JPM', 'name': 'JPMorgan Chase', 'symbol': 'JPM', 'assetClass': 'stock'}, {'id': 'stock:v', 'provider': 'finance', 'providerId': 'V', 'name': 'Visa', 'symbol': 'V', 'assetClass': 'stock'}, {'id': 'stock:avgo', 'provider': 'finance', 'providerId': 'AVGO', 'name': 'Broadcom', 'symbol': 'AVGO', 'assetClass': 'stock'}, {'id': 'stock:lly', 'provider': 'finance', 'providerId': 'LLY', 'name': 'Eli Lilly', 'symbol': 'LLY', 'assetClass': 'stock'}, {'id': 'stock:wmt', 'provider': 'finance', 'providerId': 'WMT', 'name': 'Walmart', 'symbol': 'WMT', 'assetClass': 'stock'}, {'id': 'stock:xom', 'provider': 'finance', 'providerId': 'XOM', 'name': 'Exxon Mobil', 'symbol': 'XOM', 'assetClass': 'stock'}, {'id': 'stock:jnj', 'provider': 'finance', 'providerId': 'JNJ', 'name': 'Johnson & Johnson', 'symbol': 'JNJ', 'assetClass': 'stock'}, {'id': 'etf:spy', 'provider': 'finance', 'providerId': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'symbol': 'SPY', 'assetClass': 'etf'}, {'id': 'etf:voo', 'provider': 'finance', 'providerId': 'VOO', 'name': 'Vanguard S&P 500 ETF', 'symbol': 'VOO', 'assetClass': 'etf'}, {'id': 'etf:ivv', 'provider': 'finance', 'providerId': 'IVV', 'name': 'iShares Core S&P 500 ETF', 'symbol': 'IVV', 'assetClass': 'etf'}, {'id': 'etf:qqq', 'provider': 'finance', 'providerId': 'QQQ', 'name': 'Invesco QQQ Trust', 'symbol': 'QQQ', 'assetClass': 'etf'}, {'id': 'etf:vti', 'provider': 'finance', 'providerId': 'VTI', 'name': 'Vanguard Total Stock Market ETF', 'symbol': 'VTI', 'assetClass': 'etf'}, {'id': 'etf:dia', 'provider': 'finance', 'providerId': 'DIA', 'name': 'SPDR Dow Jones Industrial Average ETF', 'symbol': 'DIA', 'assetClass': 'etf'}, {'id': 'etf:iwm', 'provider': 'finance', 'providerId': 'IWM', 'name': 'iShares Russell 2000 ETF', 'symbol': 'IWM', 'assetClass': 'etf'}, {'id': 'etf:vxus', 'provider': 'finance', 'providerId': 'VXUS', 'name': 'Vanguard Total International Stock ETF', 'symbol': 'VXUS', 'assetClass': 'etf'}, {'id': 'etf:efa', 'provider': 'finance', 'providerId': 'EFA', 'name': 'iShares MSCI EAFE ETF', 'symbol': 'EFA', 'assetClass': 'etf'}, {'id': 'etf:eem', 'provider': 'finance', 'providerId': 'EEM', 'name': 'iShares MSCI Emerging Markets ETF', 'symbol': 'EEM', 'assetClass': 'etf'}, {'id': 'etf:schd', 'provider': 'finance', 'providerId': 'SCHD', 'name': 'Schwab U.S. Dividend Equity ETF', 'symbol': 'SCHD', 'assetClass': 'etf'}, {'id': 'etf:bnd', 'provider': 'finance', 'providerId': 'BND', 'name': 'Vanguard Total Bond Market ETF', 'symbol': 'BND', 'assetClass': 'etf'}, {'id': 'etf:agg', 'provider': 'finance', 'providerId': 'AGG', 'name': 'iShares Core U.S. Aggregate Bond ETF', 'symbol': 'AGG', 'assetClass': 'etf'}, {'id': 'etf:tlt', 'provider': 'finance', 'providerId': 'TLT', 'name': 'iShares 20+ Year Treasury Bond ETF', 'symbol': 'TLT', 'assetClass': 'etf'}, {'id': 'etf:gld', 'provider': 'finance', 'providerId': 'GLD', 'name': 'SPDR Gold Shares', 'symbol': 'GLD', 'assetClass': 'etf'}, {'id': 'etf:slv', 'provider': 'finance', 'providerId': 'SLV', 'name': 'iShares Silver Trust', 'symbol': 'SLV', 'assetClass': 'etf'}, {'id': 'etf:uso', 'provider': 'finance', 'providerId': 'USO', 'name': 'United States Oil Fund', 'symbol': 'USO', 'assetClass': 'etf'}, {'id': 'etf:ung', 'provider': 'finance', 'providerId': 'UNG', 'name': 'United States Natural Gas Fund', 'symbol': 'UNG', 'assetClass': 'etf'}, {'id': 'etf:ibit', 'provider': 'finance', 'providerId': 'IBIT', 'name': 'iShares Bitcoin Trust ETF', 'symbol': 'IBIT', 'assetClass': 'etf'}, {'id': 'fund:vfiax', 'provider': 'finance', 'providerId': 'VFIAX', 'name': 'Vanguard 500 Index Fund Admiral', 'symbol': 'VFIAX', 'assetClass': 'fund'}, {'id': 'fund:fxaix', 'provider': 'finance', 'providerId': 'FXAIX', 'name': 'Fidelity 500 Index Fund', 'symbol': 'FXAIX', 'assetClass': 'fund'}, {'id': 'fund:swppx', 'provider': 'finance', 'providerId': 'SWPPX', 'name': 'Schwab S&P 500 Index Fund', 'symbol': 'SWPPX', 'assetClass': 'fund'}, {'id': 'fund:vtsax', 'provider': 'finance', 'providerId': 'VTSAX', 'name': 'Vanguard Total Stock Market Index Fund', 'symbol': 'VTSAX', 'assetClass': 'fund'}, {'id': 'fund:fskax', 'provider': 'finance', 'providerId': 'FSKAX', 'name': 'Fidelity Total Market Index Fund', 'symbol': 'FSKAX', 'assetClass': 'fund'}, {'id': 'fund:vbtlx', 'provider': 'finance', 'providerId': 'VBTLX', 'name': 'Vanguard Total Bond Market Index Fund', 'symbol': 'VBTLX', 'assetClass': 'fund'}, {'id': 'index:gspc', 'provider': 'finance', 'providerId': '^GSPC', 'name': 'S&P 500 Index', 'symbol': 'S&P 500', 'assetClass': 'index'}, {'id': 'index:ndx', 'provider': 'finance', 'providerId': '^NDX', 'name': 'NASDAQ-100 Index', 'symbol': 'NASDAQ 100', 'assetClass': 'index'}, {'id': 'index:ixic', 'provider': 'finance', 'providerId': '^IXIC', 'name': 'NASDAQ Composite', 'symbol': 'NASDAQ', 'assetClass': 'index'}, {'id': 'index:dji', 'provider': 'finance', 'providerId': '^DJI', 'name': 'Dow Jones Industrial Average', 'symbol': 'DJIA', 'assetClass': 'index'}, {'id': 'index:rut', 'provider': 'finance', 'providerId': '^RUT', 'name': 'Russell 2000 Index', 'symbol': 'RUT', 'assetClass': 'index'}, {'id': 'index:vix', 'provider': 'finance', 'providerId': '^VIX', 'name': 'CBOE Volatility Index', 'symbol': 'VIX', 'assetClass': 'index'}, {'id': 'index:ftse', 'provider': 'finance', 'providerId': '^FTSE', 'name': 'FTSE 100 Index', 'symbol': 'FTSE', 'assetClass': 'index'}, {'id': 'index:gdaxi', 'provider': 'finance', 'providerId': '^GDAXI', 'name': 'DAX Index', 'symbol': 'DAX', 'assetClass': 'index'}, {'id': 'index:n225', 'provider': 'finance', 'providerId': '^N225', 'name': 'Nikkei 225', 'symbol': 'NIKKEI', 'assetClass': 'index'}, {'id': 'index:hsi', 'provider': 'finance', 'providerId': '^HSI', 'name': 'Hang Seng Index', 'symbol': 'HSI', 'assetClass': 'index'}, {'id': 'commodity:gold', 'provider': 'finance', 'providerId': 'GC=F', 'name': 'Gold Futures', 'symbol': 'GOLD', 'assetClass': 'commodity'}, {'id': 'commodity:silver', 'provider': 'finance', 'providerId': 'SI=F', 'name': 'Silver Futures', 'symbol': 'SILVER', 'assetClass': 'commodity'}, {'id': 'commodity:wti-oil', 'provider': 'finance', 'providerId': 'CL=F', 'name': 'WTI Crude Oil', 'symbol': 'WTI', 'assetClass': 'commodity'}, {'id': 'commodity:brent-oil', 'provider': 'finance', 'providerId': 'BZ=F', 'name': 'Brent Crude Oil', 'symbol': 'BRENT', 'assetClass': 'commodity'}, {'id': 'commodity:natural-gas', 'provider': 'finance', 'providerId': 'NG=F', 'name': 'Natural Gas', 'symbol': 'NATGAS', 'assetClass': 'commodity'}, {'id': 'commodity:copper', 'provider': 'finance', 'providerId': 'HG=F', 'name': 'Copper Futures', 'symbol': 'COPPER', 'assetClass': 'commodity'}, {'id': 'commodity:platinum', 'provider': 'finance', 'providerId': 'PL=F', 'name': 'Platinum Futures', 'symbol': 'PLAT', 'assetClass': 'commodity'}, {'id': 'commodity:palladium', 'provider': 'finance', 'providerId': 'PA=F', 'name': 'Palladium Futures', 'symbol': 'PALL', 'assetClass': 'commodity'}, {'id': 'commodity:corn', 'provider': 'finance', 'providerId': 'ZC=F', 'name': 'Corn Futures', 'symbol': 'CORN', 'assetClass': 'commodity'}, {'id': 'commodity:wheat', 'provider': 'finance', 'providerId': 'ZW=F', 'name': 'Wheat Futures', 'symbol': 'WHEAT', 'assetClass': 'commodity'}, {'id': 'commodity:soybeans', 'provider': 'finance', 'providerId': 'ZS=F', 'name': 'Soybean Futures', 'symbol': 'SOY', 'assetClass': 'commodity'}, {'id': 'commodity:coffee', 'provider': 'finance', 'providerId': 'KC=F', 'name': 'Coffee Futures', 'symbol': 'COFFEE', 'assetClass': 'commodity'}, {'id': 'commodity:cocoa', 'provider': 'finance', 'providerId': 'CC=F', 'name': 'Cocoa Futures', 'symbol': 'COCOA', 'assetClass': 'commodity'}, {'id': 'currency:eurusd', 'provider': 'finance', 'providerId': 'EURUSD=X', 'name': 'EUR / USD', 'symbol': 'EURUSD', 'assetClass': 'currency'}, {'id': 'currency:gbpusd', 'provider': 'finance', 'providerId': 'GBPUSD=X', 'name': 'GBP / USD', 'symbol': 'GBPUSD', 'assetClass': 'currency'}, {'id': 'currency:usdjpy', 'provider': 'finance', 'providerId': 'USDJPY=X', 'name': 'USD / JPY', 'symbol': 'USDJPY', 'assetClass': 'currency'}, {'id': 'currency:usdchf', 'provider': 'finance', 'providerId': 'USDCHF=X', 'name': 'USD / CHF', 'symbol': 'USDCHF', 'assetClass': 'currency'}, {'id': 'currency:dxy', 'provider': 'finance', 'providerId': 'DX-Y.NYB', 'name': 'U.S. Dollar Index', 'symbol': 'DXY', 'assetClass': 'currency'}]
FX_SYMBOLS = {"EUR": "EURUSD=X", "GBP": "GBPUSD=X", "JPY": "USDJPY=X", "CHF": "USDCHF=X"}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def safe_float(value: Any) -> float | None:
    try:
        n = float(value)
        return n if n == n and abs(n) != float("inf") else None
    except (TypeError, ValueError):
        return None


def yahoo_chart(symbol: str, range_: str, interval: str) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(symbol, safe='')}"
    params = {"range": range_, "interval": interval, "includePrePost": "false", "events": "div,splits"}
    last_error: Exception | None = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            current_url = url.replace("query1.finance.yahoo.com", host)
            response = requests.get(current_url, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
            result = payload.get("chart", {}).get("result") or []
            if not result:
                raise RuntimeError(payload.get("chart", {}).get("error") or f"No data for {symbol}")
            return result[0]
        except Exception as exc:  # retry alternate Yahoo host
            last_error = exc
    raise RuntimeError(f"Yahoo chart failed for {symbol}: {last_error}")


def chart_points(result: dict[str, Any], field: str = "close") -> list[list[float]]:
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    values = quote.get(field) or []
    points: list[list[float]] = []
    for ts, value in zip(timestamps, values):
        n = safe_float(value)
        if n is not None:
            points.append([int(ts) * 1000, n])
    return points


def latest_value(points: list[list[float]]) -> float | None:
    return points[-1][1] if points else None


def fetch_finance_asset(asset: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    symbol = asset["providerId"]
    daily = yahoo_chart(symbol, "1y", "1d")
    daily_close = chart_points(daily, "close")
    if len(daily_close) < 2:
        raise RuntimeError(f"Insufficient daily history for {symbol}")

    meta = daily.get("meta") or {}
    price = safe_float(meta.get("regularMarketPrice")) or latest_value(daily_close)
    previous_close = safe_float(meta.get("chartPreviousClose")) or safe_float(meta.get("previousClose")) or daily_close[-2][1]
    week_anchor = daily_close[-6][1] if len(daily_close) >= 6 else daily_close[0][1]
    daily_high = chart_points(daily, "high")
    daily_low = chart_points(daily, "low")
    quote = ((daily.get("indicators") or {}).get("quote") or [{}])[0]
    volumes = [safe_float(v) for v in (quote.get("volume") or [])]
    volume = safe_float(meta.get("regularMarketVolume")) or next((v for v in reversed(volumes) if v is not None), None)
    high_24h = safe_float(meta.get("regularMarketDayHigh")) or (daily_high[-1][1] if daily_high else price)
    low_24h = safe_float(meta.get("regularMarketDayLow")) or (daily_low[-1][1] if daily_low else price)
    market_time = safe_float(meta.get("regularMarketTime"))
    updated = (
        dt.datetime.fromtimestamp(market_time, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        if market_time
        else dt.datetime.fromtimestamp(daily_close[-1][0] / 1000, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    )
    return asset["id"], {
        "price": price,
        "previousClose": previous_close,
        "change24h": ((price / previous_close) - 1) * 100 if previous_close else 0,
        "change7d": ((price / week_anchor) - 1) * 100 if week_anchor else 0,
        "high24h": high_24h,
        "low24h": low_24h,
        "volume": volume,
        "marketCap": None,
        "high52w": max((v for _, v in daily_high), default=max(v for _, v in daily_close)),
        "low52w": min((v for _, v in daily_low), default=min(v for _, v in daily_close)),
        "historyDaily": daily_close,
        "historyIntraday": [],
        "source": "Yahoo Finance scheduled snapshot",
        "updatedAt": updated,
        "exchangeTimezone": meta.get("exchangeTimezoneName"),
        "currency": meta.get("currency"),
        "mode": "snapshot",
    }


def fx_from_assets(updated_assets: dict[str, Any], existing_fx: dict[str, Any]) -> dict[str, float]:
    fx = {"USD": 1.0, **{k: v for k, v in existing_fx.items() if safe_float(v)}}
    pairs = {
        "EUR": ("currency:eurusd", True),
        "GBP": ("currency:gbpusd", True),
        "JPY": ("currency:usdjpy", False),
        "CHF": ("currency:usdchf", False),
    }
    for currency, (asset_id, invert) in pairs.items():
        rate = safe_float((updated_assets.get(asset_id) or {}).get("price"))
        if rate:
            fx[currency] = 1 / rate if invert else rate
    return fx


def update_market_data() -> None:
    existing = load_json(MARKET_PATH, {"assets": {}, "fx": {"USD": 1}})
    updated_assets = dict(existing.get("assets") or {})
    finance_assets = [a for a in ASSETS if a["provider"] == "finance"]
    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fetch_finance_asset, asset): asset for asset in finance_assets}
        for future in concurrent.futures.as_completed(future_map):
            asset = future_map[future]
            try:
                asset_id, data = future.result()
                updated_assets[asset_id] = data
                print(f"updated {asset_id}")
            except Exception as exc:
                failures.append(asset["id"])
                print(f"market warning {asset['id']}: {exc}", file=sys.stderr)
    if len(failures) == len(finance_assets):
        raise RuntimeError("All finance downloads failed; preserving previous market snapshot")
    payload = {
        "version": 1,
        "generatedAt": utc_now(),
        "source": "Yahoo Finance scheduled snapshots; crypto is refreshed directly from CoinGecko in the browser",
        "fx": fx_from_assets(updated_assets, existing.get("fx") or {}),
        "assets": updated_assets,
        "failedAssets": failures,
    }
    write_json(MARKET_PATH, payload)


def clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_gdelt_date(value: str | None) -> str:
    if not value:
        return utc_now()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return dt.datetime.strptime(value, fmt).replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return value


def gdelt_news(query: str, category: str, limit: int = 18) -> list[dict[str, Any]]:
    params = {
        "query": f"({query}) sourcelang:english",
        "mode": "artlist",
        "maxrecords": str(limit),
        "format": "json",
        "sort": "datedesc",
        "timespan": "48h",
    }
    response = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    articles = response.json().get("articles") or []
    items = []
    for article in articles:
        url = article.get("url")
        title = clean_title(article.get("title"))
        if not url or not title:
            continue
        items.append({
            "category": category,
            "title": title,
            "url": url,
            "image": article.get("socialimage") or "",
            "source": article.get("domain") or urlparse(url).netloc,
            "publishedAt": parse_gdelt_date(article.get("seendate")),
            "summary": "",
            "provider": "GDELT",
        })
    return items


def coingecko_news() -> list[dict[str, Any]]:
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    if not key:
        return []
    response = requests.get(
        "https://pro-api.coingecko.com/api/v3/news",
        params={"page": 1, "per_page": 20, "language": "en", "type": "news"},
        headers={"x-cg-pro-api-key": key, "Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    items = []
    for article in response.json():
        if not article.get("url") or not article.get("title"):
            continue
        items.append({
            "category": "crypto",
            "title": clean_title(article["title"]),
            "url": article["url"],
            "image": article.get("image") or "",
            "source": article.get("source_name") or "CoinGecko",
            "publishedAt": article.get("posted_at") or utc_now(),
            "summary": "",
            "provider": "CoinGecko",
        })
    return items


def dedupe_news(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda x: x.get("publishedAt", ""), reverse=True):
        url = (item.get("url") or "").split("#")[0]
        title_key = re.sub(r"[^a-z0-9]+", "", (item.get("title") or "").lower())[:140]
        if not url or not title_key or url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url)
        seen_titles.add(title_key)
        item["url"] = url
        out.append(item)
    return out


def update_news() -> None:
    items: list[dict[str, Any]] = []
    crypto_provider = "CoinGecko"
    try:
        crypto = coingecko_news()
        if not crypto:
            crypto_provider = "GDELT fallback (COINGECKO_API_KEY not configured)"
            crypto = gdelt_news('bitcoin OR ethereum OR cryptocurrency OR blockchain', "crypto", 20)
        items.extend(crypto)
    except Exception as exc:
        crypto_provider = "GDELT fallback"
        print(f"CoinGecko news warning: {exc}", file=sys.stderr)
        try:
            items.extend(gdelt_news('bitcoin OR ethereum OR cryptocurrency OR blockchain', "crypto", 20))
        except Exception as fallback_exc:
            print(f"Crypto fallback warning: {fallback_exc}", file=sys.stderr)

    queries = [
        ("markets", '"stock market" OR equities OR "S&P 500" OR Nasdaq OR earnings'),
        ("macro", 'inflation OR "interest rates" OR "central bank" OR "Federal Reserve" OR ECB OR GDP'),
        ("commodities", 'gold OR silver OR "crude oil" OR "natural gas" OR copper'),
        ("etfs", 'ETF OR "exchange traded fund" OR "index fund"'),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {executor.submit(gdelt_news, query, category, 18): category for category, query in queries}
        for future in concurrent.futures.as_completed(future_map):
            category = future_map[future]
            try:
                items.extend(future.result())
            except Exception as exc:
                print(f"news warning {category}: {exc}", file=sys.stderr)

    items = dedupe_news(items)[:80]
    if not items:
        existing = load_json(NEWS_PATH, {"items": []})
        if existing.get("items"):
            print("No fresh news; preserving previous feed", file=sys.stderr)
            return
    write_json(NEWS_PATH, {
        "version": 1,
        "generatedAt": utc_now(),
        "providers": {"crypto": crypto_provider, "global": "GDELT DOC 2.0"},
        "items": items,
    })


def main() -> int:
    failures = 0
    try:
        update_market_data()
    except Exception as exc:
        failures += 1
        print(f"Market update failed: {exc}", file=sys.stderr)
    try:
        update_news()
    except Exception as exc:
        failures += 1
        print(f"News update failed: {exc}", file=sys.stderr)
    return 1 if failures == 2 else 0


if __name__ == "__main__":
    raise SystemExit(main())
