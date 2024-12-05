import asyncio
import pprint
import os
import datetime
import aiohttp
from aiogram import Bot
from dotenv import load_dotenv
from loguru import logger
import random
import requests

BASE_URL = "https://contract.mexc.com"

semaphore = asyncio.Semaphore(60)
unique_pair = set()
load_dotenv(".env")
bot_token = os.getenv("BOT_TOKEN")
user_id = os.getenv("USER_ID")


async def bot_notify(data: dict):
    bot = Bot(token=bot_token)
    message = f"💵 <strong>{data['currency']}</strong>\n💹 PUMP на {data['percent']}%\n🟢 Open - {data['open']}$\n🔴 Close - {data['close']}$"
    await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")
    await bot.session.close()


proxy_list = ["http://66Nvcj:RTrFW5@5.8.14.75:9436", "http://4XRUpQ:cKCEtZ@46.161.45.111:9374", None]


async def check_to_pump(session, pair):
    end = datetime.datetime.now()
    start = datetime.datetime.now() - datetime.timedelta(minutes=15)
    param = {
        "interval": "Min15",
        "start": int(start.timestamp()),
        "end": int(end.timestamp()),
    }
    proxy = random.choice(proxy_list)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/contract/kline/{pair}", params=param)
        data = response.json()

        if not data["data"]["open"]:
            return

        open_price: float = data["data"]["open"][0]
        close_price: float = data["data"]["close"][0]

        percent: float = 100 * (close_price - open_price) / open_price

        if percent > 8:
            logger.success("find PUMP. Data was send")
            pump_params = {
                "currency": pair,
                "open": f"{open_price:.10f}".rstrip("0").rstrip("."),
                "close": f"{close_price:.10f}".rstrip("0").rstrip("."),
                "percent": round(percent, 2),
            }
            await bot_notify(pump_params)
        else:
            unique_pair.add(pair)
            print(f"\r{pair} - {round(percent, 2)}% - unique {len(unique_pair)}", end="")
    except Exception as e:
        logger.exception("Error find")
        with open("error.txt", "a+") as f:
            f.write(f"{pair} - {e}\n")


async def main():
    logger.info("Start parse mexc")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v1/contract/detail") as response:
            data = await response.json()
            cur_pairs = [i["symbol"] for i in data["data"]]
            tasks = []
            print(len(cur_pairs))
            while True:
                for pair in cur_pairs:
                    await check_to_pump(session, pair)


if __name__ == '__main__':
    asyncio.run(main())
