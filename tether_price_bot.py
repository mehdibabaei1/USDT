"""
ربات قیمت لحظه‌ای تتر (USDT) - نسخه GitHub Actions
-----------------------------------------------------
این نسخه یک بار اجرا می‌شود و خارج می‌شود (بر خلاف نسخه قبلی که حلقه بی‌نهایت
داشت). GitHub Actions هر چند دقیقه یک‌بار خودش این اسکریپت را اجرا می‌کند،
پس نیازی به حلقه/sleep نیست.

مقادیر حساس (توکن بات، آیدی کانال، API Key آبان‌تتر) از GitHub Secrets
به‌صورت Environment Variable خوانده می‌شوند - هرگز داخل کد نوشته نمی‌شوند.
"""

import os
import sys
import logging
from datetime import datetime

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("tether-bot")

REQUEST_TIMEOUT = 10

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
ABANTETHER_API_KEY = os.environ.get("ABANTETHER_API_KEY", "")


def fetch_wallex():
    try:
        r = requests.get("https://api.wallex.ir/v1/markets", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        stats = data["result"]["symbols"]["USDTTMN"]["stats"]
        buy_price = round(float(stats["askPrice"]))
        sell_price = round(float(stats["bidPrice"]))
        return buy_price, sell_price
    except Exception as e:
        log.warning("Wallex fetch failed: %s", e)
        return None, None


def fetch_nobitex():
    try:
        r = requests.post(
            "https://api.nobitex.ir/market/stats",
            data={"srcCurrency": "usdt", "dstCurrency": "rls"},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        stats = data["stats"]["usdt-rls"]
        buy_price = round(float(stats["bestSell"]) / 10)
        sell_price = round(float(stats["bestBuy"]) / 10)
        return buy_price, sell_price
    except Exception as e:
        log.warning("Nobitex fetch failed: %s", e)
        return None, None


def fetch_abantether():
    if not ABANTETHER_API_KEY:
        return None, None
    try:
        r = requests.get(
            "https://abantether.com/api/v1/otc/coin-price/",
            params={"coin": "USDT"},
            headers={"Authorization": f"Bearer {ABANTETHER_API_KEY}"},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        usdt = data["USDT"]
        buy_price = round(float(usdt["irtPriceBuy"]))
        sell_price = round(float(usdt["irtPriceSell"]))
        return buy_price, sell_price
    except Exception as e:
        log.warning("AbanTether fetch failed: %s", e)
        return None, None


def fetch_bitpin():
    """قیمت خرید/فروش USDT/IRT از بیت‌پین (API عمومی، بدون نیاز به کلید).
    از اردربوک عمومی استفاده می‌شود: بهترین قیمت فروشنده‌ها (asks) = قیمت خرید کاربر،
    بهترین قیمت خریداران (bids) = قیمت فروش کاربر."""
    try:
        r = requests.get(
            "https://api.bitpin.ir/api/v1/mth/orderbook/USDT_IRT/",
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        buy_price = round(float(data["asks"][0][0]))
        sell_price = round(float(data["bids"][0][0]))
        return buy_price, sell_price
    except Exception as e:
        log.warning("Bitpin fetch failed: %s", e)
        return None, None


def fetch_tabdeal():
    """قیمت خرید/فروش USDT/IRT از تبدیل (API عمومی، بدون نیاز به کلید)."""
    try:
        r = requests.get(
            "https://api1.tabdeal.org/api/v1/depth",
            params={"symbol": "USDTIRT"},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        buy_price = round(float(data["asks"][0][0]))
        sell_price = round(float(data["bids"][0][0]))
        return buy_price, sell_price
    except Exception as e:
        log.warning("Tabdeal fetch failed: %s", e)
        return None, None


def fetch_ramzinex():
    """قیمت خرید/فروش USDT/IRT از رمزینکس (API عمومی، بدون نیاز به کلید).
    نکته: این اندپوینت بر اساس مستندات غیررسمی نوشته شده، ممکن است نیاز به
    اصلاح نام فیلد یا مسیر داشته باشد - در صورت خطا لاگ را بفرستید."""
    try:
        r = requests.get(
            "https://ramzinex.com/exchange/api/v1.0/exchange/pairs",
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        pairs = data.get("data", data) if isinstance(data, dict) else data
        usdt_pair = None
        for p in pairs:
            url_name = str(p.get("url_name", "")).lower()
            if "usdt" in url_name and ("tmn" in url_name or "toman" in url_name or "irt" in url_name):
                usdt_pair = p
                break
        if not usdt_pair:
            raise ValueError("USDT/TMN pair not found in Ramzinex pairs list")
        buy_price = round(float(usdt_pair["sell"]))
        sell_price = round(float(usdt_pair["buy"]))
        return buy_price, sell_price
    except Exception as e:
        log.warning("Ramzinex fetch failed: %s", e)
        return None, None


def fmt(n):
    if n is None:
        return "N/A"
    return f"{n:,}"


def build_message(rows):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("قیمت لحظه‌ای تتر (USDT)")
    lines.append("✨ USDT/TMN ✨")
    lines.append("```")
    lines.append(f"{'Market':<8} {'Buy':>7} {'Sell':>7}")
    lines.append("-" * 24)
    for name, (buy, sell) in rows.items():
        lines.append(f"{name:<8} {fmt(buy):>7} {fmt(sell):>7}")
    lines.append("```")
    lines.append(f"🕒 {now}")
    return "\n".join(lines)


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    r = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        log.error("Telegram send failed: %s - %s", r.status_code, r.text)
        sys.exit(1)
    log.info("Message sent to Telegram.")


def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        log.error("BOT_TOKEN or CHANNEL_ID environment variable is missing.")
        sys.exit(1)

    rows = {
        "Wallex": fetch_wallex(),
        "Nobitex": fetch_nobitex(),
        "AbanTeth": fetch_abantether(),
        "Bitpin": fetch_bitpin(),
        "Tabdeal": fetch_tabdeal(),
        "Ramzinex": fetch_ramzinex(),
    }
    message = build_message(rows)
    log.info("\n%s", message)
    send_to_telegram(message)


if __name__ == "__main__":
    main()
