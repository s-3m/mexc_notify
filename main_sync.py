import asyncio
import os
import json
import datetime
import time
from aiogram import Bot
from dotenv import load_dotenv
from loguru import logger
import requests
import aiohttp

BASE_URL = "https://contract.mexc.com"

load_dotenv(".env")
bot_token = os.getenv("BOT_TOKEN")
user_id = os.getenv("USER_ID")


async def bot_notify(data: dict):
    bot = Bot(token=bot_token)
    message = f"💵 <strong>{data['currency']}</strong>\n💹 PUMP на {data['percent']}%\n🟢 Open - {data['open']}$\n🔴 Close - {data['close']}$"
    await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")
    await bot.session.close()


async def check_to_pump(session, pair, settings):
    end = datetime.datetime.now()
    start = datetime.datetime.now() - datetime.timedelta(minutes=settings["duration"])
    param = {
        "interval": f"Min{settings["duration"]}",
        "start": int(start.timestamp()),
        "end": int(end.timestamp()),
    }
    try:
        async with session.get(f"{BASE_URL}/api/v1/contract/kline/{pair}", params=param) as response:
            data = await response.json()

        if not data["data"]["open"]:
            return

        open_price: float = data["data"]["open"][0]
        close_price: float = data["data"]["close"][0]

        percent: float = 100 * (close_price - open_price) / open_price

        if percent >= settings["percent"]:
            logger.success("Find PUMP. Data was send")
            pump_params = {
                "currency": pair,
                "open": f"{open_price:.10f}".rstrip("0").rstrip("."),
                "close": f"{close_price:.10f}".rstrip("0").rstrip("."),
                "percent": round(percent, 2),
            }
            await bot_notify(pump_params)
        else:
            print(f"\rОжидаем роста...{pair}", end="")
    except Exception as e:
        logger.exception(e)


def give_me_settings():
    with open("settings.json", "r") as f:
        settings = json.load(f)
    return settings["settings"]


async def main():
    logger.info("Start parse mexc")
    response = requests.get(f"{BASE_URL}/api/v1/contract/detail")
    data = response.json()
    cur_pairs = [i["symbol"] for i in data["data"]]
    print(len(cur_pairs))
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit_per_host=2, ssl=False)) as session:
        while True:
            settings = give_me_settings()
            tasks = [asyncio.create_task(check_to_pump(session, cur_pairs, settings)) for cur_pairs in cur_pairs]
            await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
