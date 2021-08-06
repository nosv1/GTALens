import discord
from discord.ext import tasks
from random import choice


# randomly choose an 'activity' every 5 minutes

@tasks.loop(minutes=5)
async def update_status(client):

    activities: list[discord.Activity] = [
        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens commands"),

        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens donate - support the developers"
        )
    ]

    await client.change_presence(
        activity=choice(activities),
        status=discord.Status.online
    )
