import discord
from datetime import datetime, timedelta

import Support


ALIASES = ['weather', 'forecast']

EMBED_TYPES = ['current_weather_state']

WEATHER_PERIOD = 384
GAME_HOUR_LENGTH = 120
SUNRISE_TIME = 5
SUNSET_TIME = 21

WEEKDAYS = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', ' Sunday'
]

epoch: datetime = datetime(1970, 1, 1)  # used to get total_seconds


class Weather:
    def __init__(
            self, name: str, emoji: str, day_thumbnail: str, night_thumbnail: str
    ):
        self.name = name
        self.emoji = emoji
        self.day_thumbnail = day_thumbnail
        self.night_thumbnail = night_thumbnail


class GTATime:
    def __init__(
            self, hours_game_time: float, weekday, weather_period_time: float
    ):
        self.hours_game_time = hours_game_time
        self.str_game_time = Support.hours_to_HHMM(self.hours_game_time)
        self.weekday = weekday
        self.weather_period_time = weather_period_time

        self.is_day_time = SUNRISE_TIME <= self.hours_game_time < SUNSET_TIME


class RainETA:
    def __init__(self, sec_eta: int, is_raining: bool):
        self.sec_eta = sec_eta
        self.str_eta = self.seconds_to_verbose_interval()
        self.is_raining = is_raining

    def seconds_to_verbose_interval(self):
        if self.sec_eta < 60:
            return 'Less than 1 minute'

        minutes = self.sec_eta % 60
        hours = int(self.sec_eta / 3600 + (minutes / 6000))
        minutes = int((self.sec_eta - (hours * 3600)) / 60 + (minutes / 60))

        hours_str = f"{hours} hour{'s' if hours > 1 else ''}" if hours > 0 else ''
        minutes_str = f"{minutes} minute{'s' if minutes > 1 else ''}" if minutes > 0 else ''

        if hours_str and minutes_str:
            return f"{hours_str} and {minutes_str}"

        elif hours_str and not minutes_str:
            return hours_str

        else:
            return minutes_str


class WeatherState:
    def __init__(
            self, weather: Weather, gta_time: GTATime, rain_eta: RainETA
    ):
        self.weather = weather
        self.gta_time = gta_time
        self.rain_eta = rain_eta


WEATHER_STATES = {
    'clear': Weather(
        "Clear", "☀️", "https://i.imgur.com/LerUU1Z.png", "https://i.imgur.com/waFNkp1.png"
    ),
    'raining': Weather(
        "Raining", "🌧️", "https://i.imgur.com/qsAl41k.png", "https://i.imgur.com/jc98A0G.png"
    ),
    'drizzling': Weather(
        "Drizzling", "🌦️", "https://i.imgur.com/Qx18aHp.png", "https://i.imgur.com/EWSCz5d.png"
    ),
    'misty': Weather(
        "Misty", "🌁", "https://i.imgur.com/mjZwX2A.png", "https://i.imgur.com/Mh1PDXS.png"
    ),
    'foggy': Weather(
        "Foggy", "🌫️", "https://i.imgur.com/mjZwX2A.png", "https://i.imgur.com/Mh1PDXS.png"
    ),
    'hazy': Weather(
        "Hazy", "🌫️", "https://i.imgur.com/mjZwX2A.png", "https://i.imgur.com/Mh1PDXS.png"
    ), # 🏭
    'snowy': Weather(
        "Snowy", "❄️", "https://i.imgur.com/WJEjWM6.png", "https://i.imgur.com/1TxfthS.png"
    ),
    'cloudy': Weather(
        "Cloudy", "☁️", "https://i.imgur.com/1oMUp2V.png", "https://i.imgur.com/qSOc8XX.png"
    ),
    'mostly_cloudy': Weather(
        "Mostly cloudy", "🌥️", "https://i.imgur.com/aY4EQhE.png", "https://i.imgur.com/2LIbOFC.png"
    ),
    'partly_cloudy': Weather(
        "Partly cloudy", "⛅", "https://i.imgur.com/aY4EQhE.png", "https://i.imgur.com/2LIbOFC.png"
    ),
    'mostly_clear': Weather(
        "Mostly clear", "🌤️", "https://i.imgur.com/aY4EQhE.png", "https://i.imgur.com/2LIbOFC.png"
    )
}

WEATHER_STATE_CHANGES = [
    [0, WEATHER_STATES['partly_cloudy']],
    [4, WEATHER_STATES['misty']],
    [7, WEATHER_STATES['mostly_cloudy']],
    [11, WEATHER_STATES['clear']],
    [14, WEATHER_STATES['misty']],
    [16, WEATHER_STATES['clear']],
    [28, WEATHER_STATES['misty']],
    [31, WEATHER_STATES['clear']],
    [41, WEATHER_STATES['hazy']],
    [45, WEATHER_STATES['partly_cloudy']],
    [52, WEATHER_STATES['misty']],
    [55, WEATHER_STATES['cloudy']],
    [62, WEATHER_STATES['foggy']],
    [66, WEATHER_STATES['cloudy']],
    [72, WEATHER_STATES['partly_cloudy']],
    [78, WEATHER_STATES['foggy']],
    [82, WEATHER_STATES['cloudy']],
    [92, WEATHER_STATES['mostly_clear']],
    [104, WEATHER_STATES['partly_cloudy']],
    [105, WEATHER_STATES['drizzling']],
    [108, WEATHER_STATES['partly_cloudy']],
    [125, WEATHER_STATES['misty']],
    [128, WEATHER_STATES['partly_cloudy']],
    [131, WEATHER_STATES['raining']],
    [134, WEATHER_STATES['drizzling']],
    [137, WEATHER_STATES['cloudy']],
    [148, WEATHER_STATES['misty']],
    [151, WEATHER_STATES['mostly_cloudy']],
    [155, WEATHER_STATES['foggy']],
    [159, WEATHER_STATES['clear']],
    [176, WEATHER_STATES['mostly_clear']],
    [196, WEATHER_STATES['foggy']],
    [201, WEATHER_STATES['partly_cloudy']],
    [220, WEATHER_STATES['misty']],
    [222, WEATHER_STATES['mostly_clear']],
    [244, WEATHER_STATES['misty']],
    [246, WEATHER_STATES['mostly_clear']],
    [247, WEATHER_STATES['raining']],
    [250, WEATHER_STATES['drizzling']],
    [252, WEATHER_STATES['partly_cloudy']],
    [268, WEATHER_STATES['misty']],
    [270, WEATHER_STATES['partly_cloudy']],
    [272, WEATHER_STATES['cloudy']],
    [277, WEATHER_STATES['partly_cloudy']],
    [292, WEATHER_STATES['misty']],
    [295, WEATHER_STATES['partly_cloudy']],
    [300, WEATHER_STATES['mostly_cloudy']],
    [306, WEATHER_STATES['partly_cloudy']],
    [318, WEATHER_STATES['mostly_cloudy']],
    [330, WEATHER_STATES['partly_cloudy']],
    [337, WEATHER_STATES['clear']],
    [367, WEATHER_STATES['partly_cloudy']],
    [369, WEATHER_STATES['raining']],
    [376, WEATHER_STATES['drizzling']],
    [377, WEATHER_STATES['partly_cloudy']]
]


async def on_reaction_add(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:

    embed_type = embed_meta.split('type=')[1].split('/')[0]

    if embed_type == 'current_weather_state':

        if emoji == Support.COUNTER_CLOCKWISE:
            await send_weather(msg)


async def on_reaction_remove(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:

    embed_type = embed_meta.split('type=')[1].split('/')[0]

    if embed_type == 'current_weather_state':

        if emoji == Support.COUNTER_CLOCKWISE:
            await send_weather(msg)


def get_gta_time(date: datetime) -> GTATime:
    timestamp: int = int((date - epoch).total_seconds())
    total_gta_hours: float = timestamp / GAME_HOUR_LENGTH
    weekday = WEEKDAYS[int(total_gta_hours % 168 / 24)-1]
    current_gta_hour: float = total_gta_hours % 24

    return GTATime(
        current_gta_hour, weekday, total_gta_hours % WEATHER_PERIOD
    )


def get_weather_for_period_time(weather_period_time: float) -> Weather:

    for i, period in enumerate(WEATHER_STATE_CHANGES):
        if period[0] > weather_period_time:
            return WEATHER_STATE_CHANGES[i-1][1]

    return WEATHER_STATE_CHANGES[-1][1]


def check_is_raining(weather: Weather):
    return weather is WEATHER_STATES['raining'] or weather is WEATHER_STATES['drizzling']


def get_rain_eta(weather_period_time: float, weather: Weather) -> RainETA:

    is_raining = check_is_raining(weather)

    # some how, this bit gets eta in seconds
    len_weather_state_changes = len(WEATHER_STATE_CHANGES)
    for i in range(len_weather_state_changes * 2):

        index = i % len_weather_state_changes
        offset = int(i / len_weather_state_changes) * WEATHER_PERIOD

        if WEATHER_STATE_CHANGES[index][0] + offset >= weather_period_time:

            if is_raining ^ check_is_raining(WEATHER_STATE_CHANGES[index][1]):

                return RainETA(
                    sec_eta=(
                        ((WEATHER_STATE_CHANGES[index][0] + offset) - weather_period_time) * GAME_HOUR_LENGTH
                    ),
                    is_raining=is_raining
                )


def get_weather_state(date: datetime) -> WeatherState:
    gta_time: GTATime = get_gta_time(date)
    weather: Weather = get_weather_for_period_time(gta_time.weather_period_time)
    rain_eta = get_rain_eta(gta_time.weather_period_time, weather)

    return WeatherState(
        weather, gta_time, rain_eta
    )


async def send_weather(message: discord.Message) -> discord.Message:

    utc_now = datetime.utcnow()

    weather_state = get_weather_state(utc_now)
    future_weather_state = get_weather_state(utc_now + timedelta(seconds=weather_state.rain_eta.sec_eta, minutes=1))

    rain_str = f"Rain will {'end' if weather_state.rain_eta.is_raining else 'begin'} " \
               f"in {weather_state.rain_eta.str_eta}." \
               f"\nRoads will be {'dry' if weather_state.rain_eta.is_raining else 'wet'} " \
               f"for {future_weather_state.rain_eta.str_eta}."

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f'**It is {weather_state.weather.name.lower()} at '
              f'{weather_state.gta_time.str_game_time} on {weather_state.gta_time.weekday}!**',
        description=f"{rain_str}"
                    f"[{Support.ZERO_WIDTH}](embed_meta/type=current_weather_state/)"
    )

    embed.set_thumbnail(
        url=weather_state.weather.day_thumbnail if weather_state.gta_time.is_day_time else weather_state.weather.night_thumbnail
    )

    embed.set_footer(text=f"Updated: {Support.smart_day_time_format('%H:%M UTC %A, {S} %B %Y', utc_now)}")

    msg = message
    if message.author.id == Support.GTALENS_CLIENT_ID:
        await msg.edit(embed=embed)

    else:
        msg = await message.channel.send(embed=embed)
        await msg.add_reaction(Support.COUNTER_CLOCKWISE)

    return msg

