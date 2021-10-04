import discord
from dotenv import load_dotenv
import mysql.connector
import os

import Support

load_dotenv()


class DB:
    def __init__(self, connection, cursor):
        self.connection = connection
        self.cursor = cursor


def connect_database(db_name=os.getenv("DB_NAME")) -> DB:

    db_connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),

        database=db_name,
        charset="utf8mb4",
        use_unicode=True,
        buffered=True
    )

    db_cursor = db_connection.cursor()

    return DB(db_connection, db_cursor)


def replace_chars(bad_string: str) -> str:
    return bad_string.replace("'", "''").replace("\\", "\\\\")


async def send_rundown(message: discord.Message):
    # await message.channel.trigger_typing()

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title="**Database**"
    )

    db: DB = connect_database()

    db.cursor.execute("SELECT _id FROM crews;")
    crews_total = len(db.cursor.fetchall())

    db.cursor.execute("SELECT _id FROM crews WHERE synced IS NOT NULL;")
    crews_synced = len(db.cursor.fetchall())

    embed.add_field(
        name=f"__**Crews ({crews_total})**__",
        value=f"**Synced:** {crews_synced}"
    )

    db.cursor.execute("SELECT _id FROM members;")
    members_total = len(db.cursor.fetchall())

    db.cursor.execute("SELECT _id FROM members WHERE synced IS NOT NULL;")
    members_synced = len(db.cursor.fetchall())

    embed.add_field(
        name=f"__**Members ({members_total})**__",
        value=f"**Synced:** {members_synced}"
    )

    db.cursor.execute("SELECT _id FROM jobs;")
    jobs_total = len(db.cursor.fetchall())

    db.cursor.execute("SELECT _id FROM jobs WHERE synced IS NOT NULL;")
    jobs_synced = len(db.cursor.fetchall())

    embed.add_field(
        name=f"__**Jobs ({jobs_total})**__",
        value=f"**Synced:** {jobs_synced}"
    )

    db.connection.close()

    msg = await message.channel.send(embed=embed)

    return msg


