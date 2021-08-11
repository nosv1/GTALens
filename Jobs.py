
import asyncio
from datetime import datetime
from difflib import get_close_matches
import discord
import logging

import Creators
import Database
from Database import connect_database, replace_chars
import Support

logger = logging.getLogger("discord")

ALIASES = ["track", "job", "race"]


class Job:
    def __init__(
        self,  # TODO add more attributes
        gtalens_id: str = "",
        rockstar_id: str = "",
        name: str = "",
        description: str = "",
        last_updated: datetime = datetime.fromtimestamp(0),
        thumbnail: list = [],  # [part1, part2]
        likes: int = 0,
        dislikes: int = 0,
        quits: int = 0,
        total_plays: int = 0,
        unique_plays: int = 0,
        rating: float = 0.0,
        creator: Creators.Creator = Creators.Creator,
        platform: str = "",
    ):
        self.gtalens_id = gtalens_id
        self.rockstar_id = rockstar_id
        self.name = name
        self.description = description
        self.thumbnail = (
            f"https://prod.cloud.rockstargames.com/ugc/gta5mission/"
            f"{thumbnail[0]}/{self.rockstar_id}/{thumbnail[1]}.jpg"
        ) if thumbnail else Support.GTALENS_LOGO
        self.last_updated = last_updated

        self.likes = likes
        self.dislikes = dislikes
        self.quits = quits
        self.total_plays = total_plays
        self.unique_plays = unique_plays
        self.rating = rating

        self.creator = creator

        self.platform = platform


async def on_reaction_add(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:

    if emoji in embed_meta:
        job_id = embed_meta.split(f"{emoji}=")[1].split('/')[0]
        job = await get_job(job_id)
        await msg.clear_reactions()
        await send_job(msg, job)


async def on_reaction_remove(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:
    pass


def get_jobs():
    db = Database.connect_database()
    db.cursor.execute("SELECT * FROM jobs")
    db.connection.close()
    return [Job(
        rockstar_id=j[0],
        name=j[1],
        platform=j[2],
        last_updated=datetime.strptime(j[3], "%Y-%m-%dT%H:%M:%S"),
        creator=Creators.Creator(_id=j[4]),
    ) for j in db.cursor.fetchall()]


async def get_job(job_id: str) -> Job:
    # BGNZ Here Viggo Again!
    # https://gtalens.com/job/-zBNUcfmsUCiYznpiH_ldQ
    # https://gtalens.com/api/v1/jobs/info/-zBNUcfmsUCiYznpiH_ldQ

    full_info_url = "https://gtalens.com/api/v1/jobs/info/"  # + job_id
    basic_info_url = "https://gtalens.com/api/v1/jobs/basicinfo/"  # + job_id

    url = f"{full_info_url}{job_id}"
    print(url)
    r_json = await Support.get_url(url)
    payload = r_json["payload"]
    job_dict = payload["job"]

    job = Job(
        gtalens_id=job_dict["jobId"],
        rockstar_id=job_dict["jobCurrId"],
        name=job_dict["name"],
        description=job_dict["desc"],
        last_updated=datetime.strptime(job_dict["upD"], "%Y-%m-%dT%H:%M:%S.%fZ"),
        thumbnail=job_dict["img"].split("."),
        likes=job_dict["stats"]["lk"],
        dislikes=job_dict["stats"]["dlk"],
        total_plays=job_dict["stats"]["plT"],
        unique_plays=job_dict["stats"]["plU"],
        quits=job_dict["stats"]["qt"],
        rating=job_dict["stats"]["r"],
        creator=Creators.Creator(
            _id=payload["suppl"]["usersInfo"][0]["userId"],
            name=payload["suppl"]["usersInfo"][0]["username"]
        )
    )

    while True:

        url = f"https://scapi.rockstargames.com/ugc/mission/details?title=gtav&contentId={job_id}"
        logger.info(f"Jobs.get_job() {url}")

        r_json = await Support.get_url(url, headers=Support.SCAPI_HEADERS)

        for id_version in range(100):  # id_version is the number of saves before publish

            for lang in [
                "en", "es", "ru", "de", "fr", "tr", "it", "zh", "hi", "ar", "ja"
            ]:

                while True:

                    url = f"https://prod.cloud.rockstargames.com/ugc/gta5mission" \
                          f"/{job_id}/0_{id_version}_{lang}.json"
                    logger.info(f"Jobs.get_job() {url}")

                    r_json = await Support.get_url(url)

                    if r_json:
                        break

                if r_json:
                    break

            if r_json:
                break

        if r_json:
            break

    return job


async def add_sc_member_jobs(sc_member_id: str) -> None:

    db = connect_database()

    sql = f"DELETE FROM jobs WHERE creator_id = '{sc_member_id}'"
    db.cursor.execute(sql)
    db.connection.commit()

    headers = Support.SCAPI_HEADERS

    for platform in [
        "ps4",
        "xboxone",
        "pc",
    ]:
        print()
        print(platform)

        page_index = 0

        while True:

            url = f"http://scapi.rockstargames.com/search/mission?" \
                  f"dateRange=any&sort=date&platform={platform}&title=gtav&missiontype=race&" \
                  f"creatorRockstarId={sc_member_id}&pageIndex={page_index}&pageSize=30"
            print(url)

            r_json = await Support.get_url(url, headers=Support.SCAPI_HEADERS)

            if r_json['status']:  # get was successful

                if r_json['content']['items']:  # jobs to add
                    print(len(r_json['content']['items']))

                    for job in r_json['content']['items']:

                        sql = f"""
                            INSERT IGNORE INTO jobs (
                                _id, name, platform, last_updated, creator_id
                            ) VALUES (
                                '{job['id']}', 
                                '{replace_chars(job['name'])}',
                                '{platform}', 
                                '{job['createdDate'].split('.')[0]}',
                                '{sc_member_id}'
                            );"""
                        db.cursor.execute(sql)

                    db.connection.commit()

                    page_index += 1

                else:
                    break

            else:
                print(r_json)
                await asyncio.sleep(15)

    db.connection.close()


def get_possible_jobs(job_name: str) -> list[Job]:
    job_name_lower = job_name.lower()
    jobs = get_jobs()
    possible_jobs = get_close_matches(
        job_name_lower, [j.name.lower() for j in jobs], n=5, cutoff=.3
    )  # list of job names - max 5
    possible_jobs = [jobs[i] for i in possible_jobs]

    if len(possible_jobs) > 1:

        if (
                possible_jobs[0].name.lower() == job_name_lower and
                possible_jobs[1].name.lower() != job_name_lower
        ):  # only one exact match
            return [possible_jobs[0]]

    return possible_jobs


async def send_possible_jobs(
        message: discord.Message, possible_jobs: list[Job], job_name: str
) -> discord.Message:

    await message.channel.trigger_typing()

    if len(possible_jobs) == 1:  # straight to sending the job embed
        msg = await send_job(message, await get_job(possible_jobs[0].rockstar_id))

    else:  # create embed for possible jobs list
        letters = list(Support.LETTERS_EMOJIS.keys())
        possible_jobs_str = ""
        embed_meta = "embed_meta/type=job/"

        for i, job in enumerate(possible_jobs):
            creator = Creators.get_creator(job.creator.id)

            possible_jobs_str += f"\n{Support.LETTERS_EMOJIS[letters[i]]} " \
                                 f"[{job.name}](https://gtalens.com/job/{job.rockstar_id}) - " \
                                 f"[{creator.name}](https://gtalens.com/profile/{job.creator.id})"

            embed_meta += f"{Support.LETTERS_EMOJIS[letters[i]]}={job.rockstar_id}/"

        embed = discord.Embed(
            color=discord.Color(Support.GTALENS_ORANGE),
            title=f"Search: '{job_name}'",
            description=f"[GTALens](https://gtalens.com/?page=1&search={job_name.replace(' ', '%20')}) **|** "
                        f"[Donate]({Support.DONATE_LINK})"
                        f"\n{possible_jobs_str}"
                        f"[{Support.ZERO_WIDTH}]({embed_meta})"
        )

        # TODO .lens creator creator_name
        # embed.set_footer(text=".lens creator creator_name")

        msg = await message.channel.send(embed=embed)
        for i, j in enumerate(possible_jobs):
            await msg.add_reaction(Support.LETTERS_EMOJIS[letters[i]])

    return msg


async def send_job(message: discord.Message, job: Job):

    embed = discord.Embed(
        color=discord.Colour(Support.GTALENS_ORANGE),
        title=f"**{job.name}**",
        description=f"\n[GTALens](https://gtalens.com/job/{job.gtalens_id}) **|** "
                    f"[R*SC](https://socialclub.rockstargames.com/job/gtav/{job.rockstar_id}) **|** "
                    f"[Donate](https://ko-fi.com/gtalens)"
                    f"\n\n**Creator**: [{job.creator.name}](https://gtalens.com/profile/{job.creator.id})"
                    f"\n*{job.description}*"
                    f"\n{Support.SPACE_CHAR}"
                    
                    f"[{Support.ZERO_WIDTH}](embed_meta/gtalens_id={job.gtalens_id}/)",
    )

    embed.add_field(
        name=f"**__Ratings ({round(job.rating, 1)}%)__**",
        value=f"**Likes:** {job.likes}"
              f"\n**Dislikes:** {job.dislikes} *+{job.quits}*"
              f"\n**Plays:** {job.total_plays}"
              f"\n**Unique:** {job.unique_plays}"
              f"\n{Support.SPACE_CHAR}",
        inline=False
    )

    # TODO settings field

    # embed.add_field(
    #     name="**__Settings__**",
    #     value=f"{job.type}"  # race type, land/stunt...
    #           f"{job.time_of_day} - {job.weather}"
    #           f"\n{Support.SPACE_CHAR}",
    #     inline=False
    # )

    # TODO trending field?

    embed.set_thumbnail(url=job.thumbnail)
    embed.set_footer(text=f"Updated: {job.last_updated.strftime('%d %b %Y')}")

    if message.author.id != Support.GTALENS_CLIENT_ID:
        return await message.channel.send(embed=embed)

    else:
        return await message.edit(embed=embed)

