
import discord
import logging
import os

import Jobs
import Support
from Tasks import update_status
import Vehicles
import Weather

from dotenv import load_dotenv

load_dotenv()

# intents = discord.Intents.all()
# client = discord.Client(intents=intents)
client = discord.Client()

# Logging to console and file

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
formatter.default_msec_format = "%s.%03d"  # the default uses %s,%03d pfft

file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="a+")
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


@client.event
async def on_message(message):
    await client.wait_until_ready()

    args, message_content = Support.get_args_from_content(message.content)

    if message.author == client.user:  # is GTALens
        return

    if args[0] == ".lens":  # command attempted
        logger.info(f"Message Content: {message_content}")

        ''' COMMANDS  '''

        if args[1].lower() == "test":
            await Jobs.add_sc_member_jobs(45653182)

            ''' TEST '''

        elif args[1].lower() == "updatevehicles" and message.author.id in Support.DEVS:
            msg = await message.channel.send('updating...')
            await Vehicles.update_vehicles()
            await msg.delete()

            ''' UPDATE VEHICLES MANUALLY - MUST BE DEV'''

        elif args[1].lower() in Jobs.ALIASES:

            job_name = " ".join(args[2:-1])
            possible_jobs = Jobs.get_possible_jobs(job_name)
            await Jobs.send_possible_jobs(message, possible_jobs, job_name)

            ''' TRACK LOOKUP '''

        elif args[1].lower() in Vehicles.ALIASES:

            vehicle_name = " ".join(args[2:-1])
            possible_vehicles = Vehicles.get_possible_vehicles(vehicle_name)
            await Vehicles.send_possible_vehicles(message, client, possible_vehicles, vehicle_name)

            ''' CAR LOOKUP '''

        elif args[1].lower() in Weather.ALIASES:

            await Weather.send_weather(message)

        elif args[1].lower() == "invite":  # send invite link

            embed = discord.Embed(
                colour=discord.Colour(Support.GTALENS_ORANGE),
                title="**Invite GTALens to your server!**",
                description=Support.INVITE_LINK,
            )

            await message.channel.send(embed=embed)

            ''' INVITE LINK '''

        elif args[1].lower() == "donate":  # send donate link

            embed = discord.Embed(
                colour=discord.Colour(Support.GTALENS_ORANGE),
                title="**Support the Developers!**",
                description=f"[GTALens](https://gtalens.com) **|** [Donate]({Support.DONATE_LINK})"
                            f"\n\nGTALens is a free resource, but it is not without its costs. "
                            f"If you have a spare dollar, feel free to show your support <3."
            )
            await message.channel.send(embed=embed)

            ''' DONATE LINK '''

        else:
            embed = discord.Embed(
                color=discord.Colour(Support.GTALENS_ORANGE),
                title="**Coming Soon**",
                description="The GTALens discord bot will replace the MoBot functionality of searching for cars and "
                            "jobs, as well as, providing other useful GTA V related features. Currently, "
                            "the [GTALens](https://gtalens.com/) website needs some backend updates "
                            "before this bot is available for use.",
            )
            await message.channel.send(embed=embed)


@client.event
async def on_raw_message_edit(payload):
    await client.wait_until_ready()

    payload: dict = payload.data

    if "channel_id" in payload:
        channel_id = payload["channel_id"]
        channel = client.get_channel(channel_id)

        if not channel:
            channel = await client.fetch_channel(channel_id)

        if "id" in payload:
            await on_message(await channel.fetch_message(payload["id"]))


@client.event
async def on_raw_reaction_add(payload):
    await client.wait_until_ready()

    m = [m for m in client.cached_messages if m.id == payload.message_id]
    message = m[0] if m else m

    if not message:  # message not in cache

        # get channel
        channel = client.get_channel(payload.channel_id)
        if not channel:
            channel = await client.fetch_channel(payload.channel_id)

        # get message
        message = await channel.fetch_message(payload.message_id)

    # get user
    user = client.get_user(payload.user_id)
    if not user:
        user = await client.fetch_user(payload.user_id)

    emoji = payload.emoji.name

    if user.id != client.user.id:  # not GTALens reaction

        if message.author.id == client.user.id:  # is GTALens message

            logger.info(f"Reacted to GTALens: {emoji}")

            if message.embeds:  # is an embed
                embed = message.embeds[0]

                if embed.description:  # has description

                    if 'embed_meta' in embed.description:  # has info about the embed

                        embed_meta = embed.description.split("embed_meta/")[1]
                        embed_type = embed_meta.split("type=")[1].split("/")[0]

                        if embed_type in Vehicles.EMBED_TYPES:  # is vehicle embed
                            await Vehicles.on_reaction_add(message, emoji, user, client, embed_meta)

                        elif embed_type in Jobs.EMBED_TYPES:  # is job embed
                            await Jobs.on_reaction_add(message, emoji, user, client, embed_meta)

                        elif embed_type in Weather.EMBED_TYPES:
                            await Weather.on_reaction_add(message, emoji, user, client, embed_meta)


@client.event
async def on_raw_reaction_remove(payload):
    await client.wait_until_ready()

    # check the cache before fetching the message
    m = [m for m in client.cached_messages if m.id == payload.message_id]
    message = m[0] if m else m

    if not message:  # message not in cache

        # get channel
        channel = client.get_channel(payload.channel_id)
        if not channel:
            channel = await client.fetch_channel(payload.channel_id)

        # get message
        message = await channel.fetch_message(payload.message_id)

    # get user
    user = client.get_user(payload.user_id)
    if not user:
        user = await client.fetch_user(payload.user_id)

    emoji = payload.emoji.name

    if user.id != client.user.id:  # not GTALens reaction

        if message.author.id == client.user.id:  # is GTALens message

            logger.info(f"Un-reacted to GTALens: {emoji}")

            if message.embeds:  # is an embed
                embed = message.embeds[0]

                if embed.description:  # has description

                    if 'embed_meta' in embed.description:  # has info about the embed

                        embed_meta = embed.description.split("embed_meta/")[1]
                        embed_type = embed_meta.split("type=")[1].split("/")[0]

                        if embed_type in Vehicles.EMBED_TYPES:  # is vehicle embed
                            await Vehicles.on_reaction_remove(message, emoji, user, client, embed_meta)

                        elif embed_type in Weather.EMBED_TYPES:
                            await Weather.on_reaction_remove(message, emoji, user, client, embed_meta)


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
