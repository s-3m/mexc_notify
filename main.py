import asyncio
import pprint
import os
import datetime
import aiohttp
from aiogram import Bot
from dotenv import load_dotenv
from loguru import logger
import random

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


async def check_to_pump(session, pair):
    async with semaphore:
        while True:
            unique_pair.add(pair)
            end = datetime.datetime.now()
            start = datetime.datetime.now() - datetime.timedelta(minutes=15)
            param = {
                "interval": "Min15",
                "start": int(start.timestamp()),
                "end": int(end.timestamp()),
            }
            try:
                async with session.get(f"{BASE_URL}/api/v1/contract/kline/{pair}", params=param) as resp:
                    data = await resp.json()

                    open: float = data["data"]["open"][0]
                    close: float = data["data"]["close"][0]

                    percent: float = 100 * (close - open) / open

                    if percent > 3:
                        logger.success("find PUMP. Data was send")
                        pump_params = {
                            "currency": pair,
                            "open": f"{open:.20f}".rstrip("0").rstrip("."),
                            "close": f"{close:.20f}".rstrip("0").rstrip("."),
                            "percent": round(percent, 2),
                        }
                        await bot_notify(pump_params)
                        await asyncio.sleep(300)
                    else:
                        print(f"\r{pair} - {round(percent, 2)}%", end="")
                        unique_pair.add(pair)
                        print(len(unique_pair))
                        await asyncio.sleep(random.randint(10, 100))
            except Exception as e:
                logger.exception("Error find")
                await asyncio.sleep(60)


async def main():
    logger.info("Start parse mexc")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v1/contract/detail") as response:
            data = await response.json()
            cur_pairs = [i["symbol"] for i in data["data"]]
            tasks = []
            print(len(cur_pairs))
            for pair in cur_pairs:
                task = asyncio.create_task(check_to_pump(session, pair))
                tasks.append(task)
                await asyncio.sleep(0.3)
            await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
