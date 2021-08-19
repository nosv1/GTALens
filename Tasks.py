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

    seconds = loop.current_loop * 30

    if seconds % (5 * 60) == 0:
        if HOST != "PC":
            await update_status(client)
        else:
            await client.change_presence(status=discord.Status.offline)

    if loop.current_loop > 0:  # skip first iteration
        if seconds % (2 * 60) == 0:
            await update_jobs()

        # TODO once you figure out a way to intelligently update tracks, add crew members
        if seconds % (60 * 60 + 30) == 0:
            await update_crews()

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
    db: Database.DB = Database.connect_database()

    # deleting known not creators, at least atm
    delete_not_creators = f""" 
        DELETE FROM members
        WHERE _id NOT IN (
            SELECT DISTINCT(creator_id) FROM jobs
        ) AND synced IS NOT NULL
    """

    db.cursor.execute(f"""{delete_not_creators};""")
    logger.info(f"Deleted Members: {db.cursor.rowcount}")
    db.connection.commit()

    creators_limit = 3
    tbd_creators_limit = 2

    # updating known creators
    creators = f"""
        SELECT _id FROM members
        INNER JOIN (
            SELECT DISTINCT(creator_id) FROM jobs
        ) as j1
        ON _id = j1.creator_id
    """

    db.cursor.execute(f"""
        {creators}
        ORDER BY synced ASC
        LIMIT {creators_limit}
    ;""")
    member_ids = db.cursor.fetchall()

    # updating unknowns
    tbd_creators = f"""
        SELECT _id FROM members
        WHERE _id NOT IN (
            SELECT DISTINCT(creator_id) FROM jobs
        ) AND synced IS NULL
    """

    db.cursor.execute(f"""
        {tbd_creators}
        ORDER BY synced ASC 
        LIMIT {tbd_creators_limit}
    ;""")
    member_ids += db.cursor.fetchall()

    for i, member_id in enumerate(member_ids):
        logger.debug(f"Members Update: {int(100 * (i/5))}%")
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
