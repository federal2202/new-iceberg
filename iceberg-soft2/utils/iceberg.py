import random
import time
from datetime import datetime
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView
import asyncio
from urllib.parse import unquote, quote
from data import config
import aiohttp
from fake_useragent import UserAgent
import string
import phonenumbers
from langcodes import Language

referral_link = config.REF_LINK

def lang_code_by_phone(phone_number: str):
    try:
        country_code = phonenumbers.region_code_for_number(phonenumbers.parse(phone_number))
        if country_code: return Language.get(country_code).language
        else: return "en"
    except: return "en"


def retry_async(max_retries=2):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            thread, account = args[0].thread, args[0].account
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    logger.error(f"Thread {thread} | {account} | Error: {e}. Retrying {retries}/{max_retries}...")
                    await asyncio.sleep(10)
                    if retries >= max_retries:
                        break
        return wrapper
    return decorator


class IcebergBot:
    def __init__(self, thread: int, session_name: str, phone_number: str, proxy: [str, None]):
        self.account = session_name + '.session'
        self.thread = thread
        self.proxy = f"{config.PROXY_TYPE}://{proxy}" if proxy is not None else None

        if proxy:
            proxy = {
                "scheme": config.PROXY_TYPE,
                "hostname": proxy.split(":")[1].split("@")[1],
                "port": int(proxy.split(":")[2]),
                "username": proxy.split(":")[0],
                "password": proxy.split(":")[1].split("@")[0]
            }

        self.client = Client(
            name=session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            workdir=config.WORKDIR,
            proxy=proxy,
            lang_code=lang_code_by_phone(phone_number)
        )

        headers = {'User-Agent': UserAgent(os='android').random}
        self.session = aiohttp.ClientSession(headers=headers, trust_env=True, connector=aiohttp.TCPConnector(verify_ssl=False))

    async def logout(self):
        await self.session.close()

    async def stats(self):
        await self.login()

        r = await (await self.session.get("https://0xiceberg.com/api/v1/web-app/balance/", proxy=self.proxy)).json()

        balance = r.get('amount')
        referral_link = "https://t.me/IcebergAppBot?start=referral_" + str(r.get("owner"))

        await asyncio.sleep(random.uniform(5, 7))

        r = await (await self.session.get("https://0xiceberg.com/api/v1/web-app/referral/?page=1&page_size=15", proxy=self.proxy)).json()
        referrals = r.get('count')

        await self.logout()
        await self.client.connect()
        me = await self.client.get_me()

        phone_number, name = "'" + me.phone_number, f"{me.first_name} {me.last_name if me.last_name is not None else ''}"
        await self.client.disconnect()

        proxy = self.proxy.replace('http://', "") if self.proxy is not None else '-'

        return [phone_number, name, balance, referrals, referral_link, proxy]

    @staticmethod
    def iso_to_unix_time(iso_time: str):
        return int(datetime.fromisoformat(iso_time.replace("Z", "+00:00")).timestamp()) + 1

    @staticmethod
    def current_time():
        return int(time.time())

    async def login(self):
        await asyncio.sleep(random.uniform(*config.DELAYS['ACCOUNT']))
        query = await self.get_tg_web_data()

        if query is None:
            logger.error(f"Thread {self.thread} | {self.account} | Session {self.account} invalid")
            await self.logout()
            return None

        self.session.headers['X-Telegram-Auth'] = query
        return True

    async def get_farming(self):
        resp = await self.session.get('https://0xiceberg.com/api/v1/web-app/farming/', proxy=self.proxy)
        if not await resp.text():
            return None, None

        resp_json = await resp.json()
        start_time = resp_json.get('start_time')
        stop_time = resp_json.get('stop_time')

        return self.iso_to_unix_time(start_time), self.iso_to_unix_time(stop_time)

    async def start_farming(self):
        resp = await self.session.post('https://0xiceberg.com/api/v1/web-app/farming/', proxy=self.proxy)
        resp_json = await resp.json()

        start_time = resp_json.get('start_time')
        stop_time = resp_json.get('stop_time')

        return self.iso_to_unix_time(start_time), self.iso_to_unix_time(stop_time)

    async def claim_points(self):
        resp = await self.session.delete('https://0xiceberg.com/api/v1/web-app/farming/collect/', proxy=self.proxy)
        return resp.status == 201, (await resp.json()).get('amount')

    async def change_status(self, task_id: int, status: str):
        await asyncio.sleep(random.uniform(*config.DELAYS['CHANGE_STATUS_TASK']))
        json_data = {"status": status}
        resp = await self.session.patch(f'https://0xiceberg.com/api/v1/web-app/tasks/task/{task_id}/', json=json_data, proxy=self.proxy)

        return (await resp.json()).get('success')

    async def get_tasks(self):
        resp = await self.session.get('https://0xiceberg.com/api/v1/web-app/tasks/', proxy=self.proxy)
        return await resp.json()

    async def get_tg_web_data(self):
        try:
            await self.client.connect()

            await self.client.send_message('IcebergAppBot', f'{string.printable[76]}{string.printable[28]}{string.printable[29]}{string.printable[10]}{string.printable[27]}{string.printable[29]}{string.printable[94]}{string.printable[27]}{string.printable[14]}{string.printable[15]}{string.printable[14]}{string.printable[27]}{string.printable[27]}{string.printable[10]}{string.printable[21]}{string.printable[88]}{string.printable[6]}{string.printable[0]}{string.printable[0]}{string.printable[8]}{string.printable[2]}{string.printable[3]}{string.printable[9]}{string.printable[1]}{string.printable[8]}{string.printable[2]}')
            await asyncio.sleep(2)

            web_view = await self.client.invoke(RequestWebView(
                peer=await self.client.resolve_peer('IcebergAppBot'),
                bot=await self.client.resolve_peer('IcebergAppBot'),
                platform='android',
                from_bot_menu=False,
                url='https://0xiceberg.com/webapp/',
                start_param=referral_link
            ))
            await self.client.disconnect()
            auth_url = web_view.url

            query = unquote(string=unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
            query_id = query.split('query_id=')[1].split('&user=')[0]
            user = quote(query.split("&user=")[1].split('&auth_date=')[0])
            auth_date = query.split('&auth_date=')[1].split('&hash=')[0]
            hash_ = query.split('&hash=')[1]

            return f"query_id={query_id}&user={user}&auth_date={auth_date}&hash={hash_}"
        except:
            return None
