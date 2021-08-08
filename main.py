import discord
import logging
import os
import re

import jobs
import Support
from tasks import update_status
import vehicles

from dotenv import load_dotenv

load_dotenv()

# Constants

INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=872899427457716234&permissions=36507241536&scope=bot"
"""
    View Channels
    Send Messages
    Public Threads
    Embed Links
    Add Reactions
    Use Slash Commands
"""

# intents = discord.Intents.all()
# client = discord.Client(intents=intents)
client = discord.Client()

# Logging to console and file

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
formatter.default_msec_format = "%s.%03d"

file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="a+")
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


@client.event
async def on_message(message):
    args, message_content = Support.get_args_from_content(message.content)

    if message.author == client.user:  # is GTALens
        return

    if args[0] == ".lens":  # command attempted

        logger.info(f"Message Content: {message_content}")

        if args[1].lower() == "test":
            for emoji in message.guild.emojis:
                print(emoji.name)

        elif args[1].lower() in jobs.ALIASES:  # Track Lookup
            job = jobs.get_job(args[2])
            msg = await job.send_job_embed(message)

        elif args[1].lower() in vehicles.ALIASES:  # Car Lookup
            vehicle = vehicles.get_vehicle(" ".join(args[2:]))
            msg = await vehicles.send_vehicle(vehicle, message, client)

        elif args[1].lower() == "invite":  # send invite link
            embed = discord.Embed(
                colour=discord.Colour(Support.GTALENS_ORANGE),
                title="**Invite GTALens to your server!**",
                description=INVITE_LINK,
            )

        else:
            embed = discord.Embed(
                title="**Coming Soon**",
                description="The GTALens discord bot will replace the MoBot functionality of searching for cars and "
                "jobs, as well as, providing other useful GTA V related features. Currently, the [GTALens]("
                "https://gtalens.com/) website needs some backend updates before this bot is available for "
                "use.",
            )
            await message.channel.send(embed=embed)


@client.event
async def on_raw_message_edit(payload):
    payload: dict = payload.data

    if "channel_id" in payload:
        channel_id = payload["channel_id"]
        channel = client.get_channel(channel_id)

        if not channel:
            channel = await client.fetch_channel(channel_id)

        if "id" in payload:
            await on_message(await channel.fetch_message(payload["id"]))


@client.event
async def on_reaction_add(reaction, user):
    message = reaction.message

    if user.id != client.user.id:  # not GTALens reaction

        if message.author.id == client.user.id:  # is GTALens message

            logger.info(f"Reacted to GTALens: {reaction.emoji}")

            if message.embeds:  # is an embed
                embed = message.embeds[0]

                if embed.description:  # has description

                    if 'embed_meta' in embed.description:  # has info about the embed

                        embed_meta = embed.description.split("embed_meta/")[1]
                        embed_type = embed_meta.split("type=")[1].split("/")[0]

                        if embed_type == "vehicle":  # is vehicle embed
                            await vehicles.on_reaction_add(message, reaction, user, client, embed_meta)


@client.event
async def on_reaction_remove(reaction, user):
    print('yes')
    message = reaction.message

    if user.id != client.user.id:  # not GTALens reaction

        if message.author.id == client.user.id:  # is GTALens message

            logger.info(f"Un-reacted to GTALens: {reaction.emoji}")

            if message.embeds:  # is an embed
                embed = message.embeds[0]

                if embed.description:  # has description

                    if 'embed_meta' in embed.description:  # has info about the embed

                        embed_meta = embed.description.split("embed_meta/")[1]
                        embed_type = embed_meta.split("type=")[1].split("/")[0]

                        if embed_type == "vehicle":  # is vehicle embed
                            await vehicles.on_reaction_remove(message, reaction, user, client, embed_meta)


@client.event
async def on_raw_reaction_remove(payload):
    print('yes')


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


async def startup():
    await client.wait_until_ready()

    await update_status.start(client)


def main():
    while True:
        client.loop.create_task(startup())
        client.run(os.getenv("TOKEN"))


if __name__ == "__main__":
    main()
