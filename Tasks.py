import asyncio
import discord
from discord.ext import tasks
from dotenv import load_dotenv
import logging
import os
from random import choice, shuffle

import Database
import Jobs
import Vehicles

load_dotenv()

logger = logging.getLogger('discord')

HOST = os.getenv("HOST")


@tasks.loop(seconds=15)
async def loop(client):

    seconds = loop.current_loop * 30

    if seconds % (5 * 60) == 0:
        if HOST != "PC":
            await update_status(client)
        else:
            await client.change_presence(status=discord.Status.offline)

        ''' UPDATE STATUS '''

    if seconds % (60 * 60) == 0:
        Jobs.pickle_jobs()
        Jobs.pickle_creators()

        ''' UPDATE JOBS PICKLE '''

    if loop.current_loop > 0:  # skip first iteration
        if seconds % (2 * 60) == 0:
            await update_jobs()

            ''' UPDATE JOBS '''

        # if seconds % (60 * 60 + 30) == 0:
        #     await update_crews()

            ''' UPDATE CREWS '''

        if seconds % (12 * 60 * 60) == 0:
            await update_vehicles()

            '''' UPDATE VEHICLES '''


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
        DELETE m FROM members m
        LEFT JOIN (
            SELECT creator_id FROM jobs
            GROUP BY creator_id
        ) as j
        ON j.creator_id = m._id
        WHERE 
            synced IS NOT NULL AND
            creator_id IS NULL
    """

    db.cursor.execute(f"""{delete_not_creators};""")
    logger.debug(f"Deleted Members: {db.cursor.rowcount}")
    db.connection.commit()

    creators_limit = 6
    tbd_creators_limit = 4

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
    db.connection.close()

    # shuffling to lessen timeout errors
    # (putting creators together means more pages to fetch per user)
    shuffle(member_ids)

    logger.info(f"Updating Members: {', '.join([m[0] for m in member_ids])}")
    for i, member_id in enumerate(member_ids):
        await asyncio.shield(Jobs.add_sc_member_jobs(member_id[0]))
        # await asyncio.sleep(5)  # per user
    logger.info(f"Members Updated: {', '.join([m[0] for m in member_ids])}")


async def update_crews():
    db = Database.connect_database()
    limit = 5
    db.cursor.execute(f"SELECT _id FROM crews ORDER BY synced ASC LIMIT {limit}")
    crew_ids = db.cursor.fetchall()
    db.connection.close()

    logger.info(f"Updating Crews: {', '.join([c[0] for c in crew_ids])}")
    for i, crew_id in enumerate(crew_ids):
        await Jobs.add_crew(crew_id[0])
    logger.info(f"Crews Updated: {', '.join([c[0] for c in crew_ids])}")


async def update_vehicles():
    logger.info("Updating Vehicles")
    await Vehicles.update_vehicles()
    logger.debug(f"Vehicles Updated")
