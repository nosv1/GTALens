import asyncio
from datetime import datetime
import discord
import json
import logging
import os
from random import choice
import re
import subprocess
import traceback

import Database
import Jobs
import Support
import Tasks
import Vehicles
import Weather

from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("HOST")

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
# client = discord.Client()

# Logging to console and file

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO if HOST != 'PC' else logging.DEBUG)

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
formatter.default_msec_format = "%s.%03d"  # the default uses %s,%03d pfft

file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="a+")
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logger.level)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

#


@client.event
async def on_message(message: discord.Message):
    await client.wait_until_ready()

    args: list[str]
    message_content: str
    args, message_content = Support.get_args_from_content(message.content)

    if message.author == client.user:  # is GTALens
        return

    if str(client.user.id) in args[0]:
        embed = discord.Embed(
            colour=discord.Colour(Support.GTALENS_ORANGE),
            description=f"**{client.user.mention}'s prefix is `.lens`. Check out `.lens help` for available commands.**"
        )
        await message.channel.send(embed=embed)

    if (
            (
                HOST != 'PC' and any([args[0] == f"{p}lens" for p in [".", "?", "!"]])
            ) or (
                HOST == "PC" and args[0] == "`lens"
            )
    ):  # PC HOST means testing, this avoids double responses when PC and PI4 are both running
        logger.info(
            f"Message: "
            f"{message.guild.name if message.guild else ''} "
            f"#{message.channel.name if type(message.channel) == discord.TextChannel else 'DM'} "
            f"- {message_content}"
        )
        is_dev = message.author.id in Support.DEVS.values()

        ''' COMMANDS  '''

        if args[1].lower() == "test" and is_dev:
            pass
            for task in asyncio.all_tasks():
                if not task.done():
                    print(str(task.get_coro()))

            ''' TEST '''

        elif args[1].lower() == "servers":

            guilds: list[discord.Guild] = client.guilds

            embed = discord.Embed(
                colour=discord.Colour(Support.GTALENS_ORANGE),
            )
            for i, guild in enumerate(guilds):
                guilds[i] = [guild.name, guild.get_member(client.user.id).joined_at, guild.members]
            guilds.sort(key=lambda g: g[1])
            guilds: list[str, datetime, list[discord.Member]]

            guild_str = ""
            members = []
            for guild_name, joined_at, guild_members in guilds:

                guild_str += f"**{guild_name}** ({len(guild_members)}) - " \
                             f"{joined_at.strftime('%d %b %Y')}\n"
                members += guild_members

                if len(guild_str) > 900 and is_dev:
                    embed.add_field(
                        name=Support.SPACE_CHAR,
                        value=f"{guild_str} {Support.SPACE_CHAR}"
                    )
                    guild_str = ""

            if guild_str and is_dev:
                embed.add_field(
                    name=Support.SPACE_CHAR,
                    value=guild_str
                )

            embed.title = f"**Servers: {len(guilds)}\n" \
                          f"Unique Members: {len(set(members))}\n" \
                          f"Total Members: {len(members)}**"

            await message.channel.send(embed=embed)

        elif args[1].lower() in ["restart", "close"] and is_dev:

            json.dump({'action': args[1].lower()}, open("restart.json", "w+"))
            if args[1].lower() == "restart":
                await Tasks.update_status(client, restart=True)

            else:
                await Tasks.update_status(client, close=True)

            # wait for add_sc_member_jobs to finish before closing
            while any([
                'add_sc_member_jobs' in str(task.get_coro()) for task in asyncio.all_tasks() if not task.done()
            ]):
                await asyncio.sleep(1)

            await client.close()

            ''' RESTART/CLOSE BOT '''

        elif args[1].lower() == "db" and is_dev:
            await Database.send_rundown(message)

            ''' DATABASE RUNDOWN '''

        elif args[1].lower() == "updatevehicles" and is_dev:
            msg = await message.channel.send('updating...')
            await Vehicles.update_vehicles()
            await msg.delete()

            ''' UPDATE VEHICLES MANUALLY - MUST BE DEV'''

        elif args[1].lower() == "updatejobs" and is_dev:
            msg = await message.channel.send('updating...')
            await Tasks.update_jobs()
            await msg.delete()

            ''' UPDATE JOBS MANUALLY - MUST BE DEV'''

        elif args[1].lower() == "updatecrews" and is_dev:
            msg = await message.channel.send('updating...')
            await Tasks.update_crews()
            await msg.delete()

            ''' UPDATE CREWS MANUALLY - MUST BE DEV'''

        elif args[1].lower() in Jobs.JOB_SEARCH_ALIASES:

            job_name = " ".join(args[2:-1])

            if job_name:
                await message.channel.trigger_typing()

                msg = await message.channel.send(embed=discord.Embed(
                    colour=discord.Colour(Support.GTALENS_ORANGE),
                    title=f"**Searching: *{job_name}***"
                ))

                if job_name == ".random":
                    possible_jobs = Jobs.get_random_jobs()
                else:
                    possible_jobs = Support.get_possible(job_name.lower(), Jobs.get_pickled_jobs())
                await Jobs.send_possible_jobs(msg, client, possible_jobs, job_name)

            ''' TRACK LOOKUP '''

        elif args[1].lower() in Jobs.SYNC_ALIASES:
            await message.channel.trigger_typing()

            job_link = re.sub(r"[<>]", "", args[2])
            msg, job = await Jobs.sync_job(message, job_link)
            if job:
                await Jobs.send_job(message, client, job)
            Jobs.pickle_jobs()
            Jobs.pickle_creators()

            ''' SYNC JOB '''

        elif args[1].lower() in Jobs.PLAYLIST_SEARCH_ALIASES + Jobs.CREATOR_SEARCH_ALIASES:

            creator_name = " ".join(args[2:-1]).strip()

            if creator_name:
                await message.channel.trigger_typing()

                msg = await message.channel.send(embed=discord.Embed(
                    colour=discord.Colour(Support.GTALENS_ORANGE),
                    title=f"**Searching: *{creator_name}***"
                ))

                creators = list(Jobs.get_pickled_creators().values())
                possible_creators = Support.get_possible(creator_name.lower(), creators)

                embed_type = ""
                if args[1].lower() in Jobs.PLAYLIST_SEARCH_ALIASES:
                    embed_type = "creator_search_playlist"

                elif args[1].lower() in Jobs.CREATOR_SEARCH_ALIASES:
                    embed_type = "creator_search"

                await Jobs.send_possible_creators(
                    msg, client, possible_creators, creator_name, embed_type
                )

            ''' CREATOR LOOKUP'''

        elif args[1].lower() in Vehicles.SEARCH_ALIASES:

            vehicle_name = " ".join(args[2:-1])

            if vehicle_name:
                await message.channel.trigger_typing()

                msg = await message.channel.send(embed=discord.Embed(
                    colour=discord.Colour(Support.GTALENS_ORANGE),
                    title=f"**Searching: *{vehicle_name}***"
                ))

                possible_vehicles = Support.get_possible(
                    vehicle_name.lower(),
                    list(Vehicles.get_vehicles().values())
                )
                await Vehicles.send_possible_vehicles(msg, client, possible_vehicles, vehicle_name)

            ''' VEHICLE LOOKUP '''

        elif args[1].lower() in Vehicles.TIER_ALIASES:

            class_name = " ".join(args[2:-2])

            if class_name:
                await message.channel.trigger_typing()

                msg = await message.channel.send(embed=discord.Embed(
                    colour=discord.Colour(Support.GTALENS_ORANGE),
                    title=f"**Searching: *{class_name}***"
                ))

                class_names = list(Vehicles.VEHICLE_CLASS_CORRECTIONS.keys())
                possible_class_names = Support.get_possible(
                    class_name.lower(),
                    class_names,
                    objects=False
                )

                if not possible_class_names:
                    class_name = choice(class_names)

                else:
                    class_name = possible_class_names[0]

                vehicles_class: list[Vehicles.Vehicle] = Vehicles.get_vehicle_class(
                    vehicle_class=class_name,
                    vehicles=Vehicles.get_vehicles()
                )

                tier: str = args[-2][0].upper()
                vehicles_tier, vehicles_tier_str = Vehicles.get_tier(tier, vehicles_class=vehicles_class)
                await Vehicles.send_tier(msg, tier, vehicles_tier, vehicles_tier_str, vehicles_class)

            ''' VEHICLE TIER LOOKUP'''

        elif args[1].lower() in Vehicles.CLASS_ALIASES:

            class_name = " ".join(args[2:]).strip()

            if class_name:
                await message.channel.trigger_typing()

                msg = await message.channel.send(embed=discord.Embed(
                    colour=discord.Colour(Support.GTALENS_ORANGE),
                    title=f"**Searching: *{class_name}***"
                ))

                class_names = list(Vehicles.VEHICLE_CLASS_CORRECTIONS.keys())
                possible_class_names = Support.get_possible(
                    class_name.lower(),
                    class_names,
                    objects=False
                )
                logger.debug(f"Possible Class Names: {possible_class_names}")

                if not possible_class_names:
                    class_name = choice(class_names)

                else:
                    class_name = possible_class_names[0]

                await Vehicles.send_vehicle_class(
                    msg, Vehicles.get_vehicle_class(class_name, Vehicles.get_vehicles()), class_name
                )

            ''' VEHICLE CLASS LOOKUP '''

        elif args[1].lower() in Weather.ALIASES:
            await message.channel.trigger_typing()

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

        elif args[1].lower() == "server":  # send server invite
            content = f"**Have any questions? Join, and ask them!**\n{Support.SERVER_LINK}"
            await message.channel.send(content)

            ''' SERVER LINK '''

        elif args[1].lower() in ["help", "commands"]:  # send help
            help_json = json.load(open("Static Embeds/help.json", "r", encoding='utf8'))
            embed = discord.Embed.from_dict(dict(help_json))
            embed.colour = discord.Color(Support.GTALENS_ORANGE)
            await message.channel.send(embed=embed)

            ''' HELP '''

        elif args[1].lower() in ['stockbrakes', 'brakes']:  # send brakes upgrade explanation
            content = f"**Stock brakes?**\n\n"
            
            content += f"Some cars' stock brakes are sufficient enough compared to the cornering grip; so if you can decide on a threshold, you can then use some math to determine if you actually need to upgrade the brakes.\n\n"
            
            content += f"The bot uses the following method:\n"
            content += f"Get braking in terms of 'grip'\n"
            content += f"{Support.SPACE_CHAR * 2}`braking_grip = (brake_foce * 10) * brake_bias`\n\n"

            content += f"Get the difference to compare to a threshold\n"
            content += f"{Support.SPACE_CHAR * 2}`difference = braking_grip - cornering grip`\n\n"

            content += "The bot uses a threshold of 0.4 to compare to, so if the difference is greater than 0.4, the idea is stock brakes are sufficent; for many cars, this is the case. Brakes are still heavily based on preference, but for me, this is my starting point.\n"
            content += f"{Support.SPACE_CHAR * 2} - Mo (bot creator)\n\n"

            content += ">>> Disclaimer: this logic is based on experience, as well as CHILLI's *Car Upgrades & Dynamics* document [1] and Spear's *Upgrades Document* [2]. You can find the brake_force, brake_bias, and cornering_grip values on Broughy's *GTAV/Online Vehicle Info, Lap Times, and Top Speeds* spreadsheet [3]\n"
            content += "[1] <https://docs.google.com/document/d/1HAzIIJMTc8aPIXXfn-fjYa27bspS27zcnsUOqAbbzAI/edit>\n"
            content += "[2] <https://drive.google.com/file/d/18wmgSQPmHatQzXgmqT-y7yU5D4aGP3xC/view>\n"
            content += "[3] <https://docs.google.com/spreadsheets/d/1nQND3ikiLzS3Ij9kuV-rVkRtoYetb79c52JWyafb4m4/edit#gid=753713977>"

            await message.reply(content)

        # TODO .lens about


@client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    await client.wait_until_ready()

    if payload.channel_id:
        channel_id = payload.channel_id
        channel = client.get_channel(channel_id)

        if not channel:
            channel = await client.fetch_channel(channel_id)

        if payload.message_id:
            message = await channel.fetch_message(payload.message_id)

            if payload.cached_message:

                if message.content != payload.cached_message.content:
                    await on_message(message)

            else:
                await on_message(message)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
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
                        logger.info(f"embed_meta: {embed_meta}")

                        embed_type = embed_meta.split("type=")[1].split("/")[0]

                        if embed_type in Vehicles.EMBED_TYPES:  # is vehicle embed
                            await Vehicles.on_reaction_add(message, emoji, user, client, embed_meta)

                        elif embed_type in Jobs.EMBED_TYPES:  # is job embed
                            await Jobs.on_reaction_add(message, emoji, user, client, embed_meta)

                        elif embed_type in Weather.EMBED_TYPES:  # is weather embed
                            await Weather.on_reaction_add(message, emoji, user, client, embed_meta)


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
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

                        logger.info(f"embed_meta: {embed_meta}")

                        if embed_type in Vehicles.EMBED_TYPES:  # is vehicle embed
                            await Vehicles.on_reaction_remove(message, emoji, user, client, embed_meta)

                        elif embed_type in Weather.EMBED_TYPES:
                            await Weather.on_reaction_remove(message, emoji, user, client, embed_meta)


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}")


@client.event
async def on_error(event, *args, **kwargs):
    logger.warning(f"\n--- UNHANDLED EXCEPTION ---\n\n{traceback.format_exc()}\n--- END UNHANDLED EXCEPTION ---")

    if 'discord.errors.Forbidden' in traceback.format_exc():
        return

    message_content = ""
    if args:

        if event in [
            'on_raw_message_edit',
            'on_message'
        ]:

            if event == 'on_raw_message_edit':
                message: discord.Message = [m for m in client.cached_messages if m.id == args[0].message_id][0]

            else:
                message: discord.Message = args[0]

            embed = discord.Embed(
                colour=discord.Colour(Support.GTALENS_ORANGE),
                title="Oops!",
                description="Looks like there was an error. The developers have been notified, "
                            "and the error will, hopefully, be resolved within 24 hours. "
                            "We are sorry for this inconvenience."
            )

            await message.reply(embed=embed)

            message_content = message.content

        elif event in [
            'on_raw_reaction_remove',
            'on_raw_reaction_add'
        ]:
            messages = [m for m in client.cached_messages if m.id == args[0].message_id]
            if messages:
                message = messages[0]

            else:
                channel = client.get_channel(args[0].channel_id)

                if not channel:
                    channel = await client.fetch_channel(args[0].channel_id)

                message = await channel.fetch_message(args[0].message_id)

            await message.add_reaction(Support.X)
            await asyncio.sleep(5)
            await message.remove_reaction(Support.X, client.user)

    if HOST != "PC":
        errors_channel = client.get_channel(Support.GTALENS_ERRORS_CHANNEL_ID)
        errors_channel = await client.fetch_channel(
            Support.GTALENS_ERRORS_CHANNEL_ID
        ) if not errors_channel else errors_channel
        devs_ping = ','.join(f'<@{d_id}>' for d_id in Support.DEVS.values())
        await errors_channel.send(
            f"{devs_ping}\n> **{message_content}**\n"
            f"```{traceback.format_exc()}```"
        )


async def startup():
    await client.wait_until_ready()

    if HOST != "PC":
        logger.info("Starting Tasks.loop")
        await Tasks.loop.start(client)


def main():

    while True:

        # HIGHLIGHT IF GETTING URLS DOESN'T WORK START HERE
        dir_path = os.path.dirname(os.path.realpath(__file__))
        if HOST == "PC":
            subprocess.call([f"{dir_path}/start_tor.bat"])

            bot_token = os.getenv("PROTO_TOKEN")  # used for testing
            logger.info("Using PROTO_TOKEN")

        else:
            bot_token = os.getenv("GTALENS_TOKEN")
            logger.info("Using GTALENS_TOKEN")

        # elif HOST == "PI4":
        #     subprocess.Popen([f"{dir_path}/start_tor.sh"])

        client.loop.create_task(startup())
        client.run(bot_token)


if __name__ == "__main__":
    main()
