import asyncio
import discord
from discord.ext import tasks
from dotenv import load_dotenv
import logging
import os
from random import choice

import Database
import Jobs
import Vehicles

load_dotenv()

logger = logging.getLogger('discord')

HOST = os.getenv("HOST")


# randomly choose an 'activity' every 5 minutes
@tasks.loop(seconds=15)
async def loop(client):

    if HOST == "PC":
        return

    seconds = loop.current_loop * 30

    if seconds % (5 * 60) == 0:
        await update_status(client)

    if loop.current_loop > 0:  # skip first iteration
        if seconds % (2 * 60) == 0:
            await update_jobs()

        # TODO once you figure out a way to intelligently update tracks, add crew members
        # if seconds % 1.5 * 60 == 0:
        #     await update_crews()

        if seconds % (12 * 60 * 60) == 0:
            await update_vehicles()


async def update_status(client, restart=False, close=False):

    activities: list[discord.Activity] = [
        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens help"),

        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens donate - support the developers"
        ),

        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens invite - invite to your server"
        ),

        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens server - join GTALens's server"
        ),
    ]

    activity = None
    if not (restart or close):
        activity = choice(activities)

    elif restart:
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Restarting"
        )

    elif close:
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Shutting Down for Maintenance"
        )

    await client.change_presence(
        activity=activity,
        status=discord.Status.online
    )


async def update_jobs():
    db = Database.connect_database()

    has_jobs_limit = 4
    limit = 5

    # updating creators who have jobs more often than creators that don't

    db.cursor.execute(f"""
        SELECT _id 
        FROM members 
        WHERE _name IS NOT NULL
        ORDER BY synced ASC 
        LIMIT {has_jobs_limit};
    ;""")
    member_ids = db.cursor.fetchall()

    db.cursor.execute(f"""
        SELECT _id 
        FROM members 
        WHERE _name IS NULL
        ORDER BY synced ASC 
        LIMIT {limit - has_jobs_limit};
    ;""")
    member_ids += db.cursor.fetchall()

    for i, member_id in enumerate(member_ids):
        logger.debug(f"Members Update: {int(100 * (i/limit))}%")
        await asyncio.shield(Jobs.add_sc_member_jobs(member_id[0]))
        await asyncio.sleep(5)  # per user
    logger.info(f"Members Updated: {member_ids}")

    db.connection.close()


async def update_crews():
    db = Database.connect_database()
    limit = 10
    db.cursor.execute(f"SELECT _id FROM members ORDER BY RAND() LIMIT {limit}")
    crew_ids = db.cursor.fetchall()

    for i, crew_id in enumerate(crew_ids):
        logger.debug(f"Crews Update: {int(100 * (i/limit))}%")
        await Jobs.add_crew(crew_id[0])
    logger.info(f"Crews Updated: {crew_ids}")

    db.connection.close()


async def update_vehicles():
    await Vehicles.update_vehicles()
    logger.info(f"Vehicles Updated")
