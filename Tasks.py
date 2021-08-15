import logging
from random import choice

import discord
from discord.ext import tasks

import Database
import Jobs

logger = logging.getLogger('discord')


# randomly choose an 'activity' every 5 minutes
@tasks.loop(seconds=30)
async def loop(client):

    seconds = loop.current_loop * 30

    if seconds % (5 * 60) == 0:
        await update_status(client)

    if loop.current_loop > 0:  # skip first iteration
        if seconds % (1.75 * 60) == 0:
            await update_jobs()

        # if seconds % 1.5 * 60 == 0:
        #     await update_crews()


async def update_status(client, restart=False, close=False):

    activities: list[discord.Activity] = [
        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens commands"),

        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens donate - support the developers"
        ),

        discord.Activity(
            type=discord.ActivityType.watching,
            name=".lens invite - add to your server"
        )
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
    limit = 5
    db.cursor.execute(f"SELECT _id FROM members WHERE synced IS NULL ORDER BY RAND() LIMIT {limit};")
    member_ids = db.cursor.fetchall()

    for i, member_id in enumerate(member_ids):
        logger.debug(f"Members Update: {int(100 * (i/limit))}%")
        await Jobs.add_sc_member_jobs(member_id[0])
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
