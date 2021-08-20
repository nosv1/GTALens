import aiohttp
import asyncio
from datetime import datetime
import logging

import discord
import gspread
import json
import re

logger = logging.getLogger('discord')

# COLORS

GTALENS_ORANGE = int(0xF03C00)

# IDS
GTALENS_GUILD_ID = 873054419636334633
GTALENS_CLIENT_ID = 872899427457716234
GTALENS_ERRORS_CHANNEL_ID = 876587516701048883
DEVS = {
    'Mo#9991': 405944496665133058
}

# CHARACTERS
ZERO_WIDTH = chr(8203)  # or the thing in between the dashes -​-
SPACE_CHAR = "⠀"
HEAVY_CHECKMARK = "✔"
BALLOT_CHECKMARK = "☑️"
WRENCH = "🔧"
FLAG_ON_POST = "🚩"
COUNTER_CLOCKWISE = "🔄"
CALENDAR = "📆"
RAIN_WITH_SUN = "🌦️"

NUMBERS_EMOJIS = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
LETTERS_EMOJIS = {
    "a": "🇦", "b": "🇧", "c": "🇨", "d": "🇩", "e": "🇪", "f": "🇫", "g": "🇬", "h": "🇭", "i": "🇮",
    "j": "🇯", "k": "🇰", "l": "🇱", "m": "🇲", "n": "🇳", "o": "🇴", "p": "🇵", "q": "🇶", "r": "🇷",
    "s": "🇸", "t": "🇹", "u": "🇺", "v": "🇻", "w": "🇼", "x": "🇽", "y": "🇾", "z": "🇿"
}

# SCAPI
SCAPI_HEADERS = {
    "Host": "scapi.rockstargames.com",
    # "Connection": "keep-alive",
    # "sec-ch-ua": "Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"
    "DNT": "1",
    # "sec-ch-ua-mobile": ?0
    "Authorization": "None",
    "X-AMC": "true",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "X-Lang": "en-US",
    "X-Cache-Ver": "0",
    "Accept": "*/*",
    "Origin": "https://socialclub.rockstargames.com",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://socialclub.rockstargames.com/",
    # "Accept-Encoding": gzip, deflate, br
    # "Accept-Language": en-US,en;q=0.9
}

# RANDOM
mph_to_kph = 1.61
kph_to_mph = 0.62

# GTALENS
SERVER_LINK = "https://discord.gg/xvsTZNefm5"
DONATE_LINK = "https://ko-fi.com/gtalens"
GTALENS_LOGO = "https://gtalens.com/assets/images/logo-new.5336b3.png"
INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=872899427457716234&permissions=36507577408&scope=bot"
"""
    View Channels
    Send Messages
    Public Threads
    Manage Messages
    Embed Links
    Read Message History
    Use External Emojis
    Add Reactions
    Use Slash Commands
"""


# GSPREAD

def get_g_client() -> gspread.Client:
    gc = gspread.service_account(filename="Secrets/phyner-a9859c6daae5.json")
    return gc


# TIME

def minutes_seconds_to_seconds(time_str: str) -> float:
    """
    :param time_str: m:ss.000
    :return: float(miliseconds)
    """

    minutes, seconds = tuple(time_str.split(":"))
    seconds = int(minutes) * 60 + float(seconds)
    return seconds


def seconds_to_minutes_seconds(seconds: float) -> str:
    minutes = seconds // 60
    seconds = seconds - (minutes * 60)
    return f"{minutes:n}:{seconds:06.3f}"  # minutes as int, seconds with zero pad rounded to 3 decimals


def smart_day_time_format(date_format: str, dt: datetime) -> str:
    """
    :param date_format: day in format should be {S}
    :param dt: datetime
    :return: formatted time as String
    """

    return dt.strftime(date_format).replace("{S}", f"{num_suffix(dt.day)}")


def hours_to_HHMM(hours: float) -> str:
    hh = int(hours)
    mm = int((hours - hh) * 60)
    return f"{hh:02d}:{mm:02d}"


# RANDOM

def get_args_from_content(content: str = "") -> (list[str], str):
    content = re.sub(r"[“”]", '"', content)
    content = re.sub(r"[\n\t\r]", " ", content)
    content += " "
    while "  " in content:
        content = content.replace("  ", " ")

    args = content.split(
        " "
    )  # should always have at least element given addition of extra " " above

    return args, content


def num_suffix(num: int) -> str:
    """
    :param num: ex. 2
    :return: ex. 2nd
    """

    return f"{num}{'th' if 11 <= num <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th')}"


async def get_url(url: str, headers=None, params=None) -> json:
    if headers is None:
        headers = {}

    async with aiohttp.ClientSession() as cs:
        try:
            async with cs.get(url, headers=headers, params=params, timeout=10) as r:
                return json.loads(await r.text())

        except asyncio.exceptions.TimeoutError:
            return {'status': False, 'error': {'code': 'TimeoutError'}}

        except json.decoder.JSONDecodeError:
            return {'status': False, 'error': {'code': 'JSONDecodeError'}}



