import asyncio
from datetime import datetime
from Custom_Libraries.difflib import get_close_matches
import discord
import json
import logging

import Database
from Database import connect_database, replace_chars
import Support

logger = logging.getLogger("discord")

JOB_SEARCH_ALIASES = ["track", "job", "race"]
PLAYLIST_SEARCH_ALIASES = ["playlists", "playlist", "collection", "collections"]

SYNC_ALIASES = ["sync"]

EMBED_TYPES = [
    'job',
    'job_search'
]

WEATHER = [  # indices relate to what prod.cloud.rockstargames.com/ugs/mission provides
    "current",
    "☀️ bright",
    "🌧️ raining",
    "❄️ blizzard",
    "🌫 smog",
    "🎃 halloween",
    "🔥 hell",
    "☀ clear",
    "☁️ clouds",
    "☁️ overcast",
    "⛈️ thunder",
    "🌫️ foggy",
]

TIME_OF_DAY = [
    'current',  # this is a guess
    'morning',
    'noon',
    'night',
]

# FIXME there are more types than this... like P2P, but cba
JOB_TYPE_CORRECTIONS = {
    "StuntRace": "stunt race",
    "OpenWheelRace": "open wheel race",
    "PursuitRace": "pursuit race",
    "StreetRace": "street race",
    "ArenaWar": "arena war",
    "TransformRace": "transform race",
    "SpecialVehicleRace": "special vehicle race",
    "TargetAssaultRace": "target assault race",
    "AirRace": "air race",
    "BikeRace": "bike race",
    "LandRace": "land race",
    "LandRaceP2P" : "land race P2P",
    "SeaRace": "sea race"
}

PLATFORM_CORRECTIONS = {
    'xboxone': 'XB',
    'pc': 'PC',
    'ps4': 'PS'
}


class Job:
    def __init__(
            self,
            gtalens_id: str = "",
            rockstar_id: str = "",
            name: str = "",
            description: str = "",
            added: datetime = datetime.fromtimestamp(0),
            updated: datetime = datetime.fromtimestamp(0),
            synced: datetime = datetime.fromtimestamp(0),

            thumbnail: list[str] = None,  # [part1, part2]
            likes: int = 0,
            dislikes: int = 0,
            quits: int = 0,
            total_plays: int = 0,
            unique_plays: int = 0,
            rating: float = 0.0,

            creator=None,  # Creator

            platform: str = "",
            variants=None,  # list of gtalens ids

            job_type: str = "",
            pedestrians: str = "",
            time_of_day: str = "",
            weather: str = "",
    ):
        self.gtalens_id = gtalens_id
        self.rockstar_id = rockstar_id
        self.name = name
        self.description = description
        self.thumbnail = (
            f"https://prod.cloud.rockstargames.com/ugc/gta5mission/"
            f"{thumbnail[0]}/{self.rockstar_id}/{thumbnail[1]}.jpg"
        ) if thumbnail else Support.GTALENS_LOGO
        self.added = added
        self.updated = updated
        self.synced = synced

        self.likes = likes
        self.dislikes = dislikes
        self.quits = quits
        self.total_plays = total_plays
        self.unique_plays = unique_plays
        self.rating = rating

        self.creator = creator

        self.variants = variants
        self.platform = platform

        self.job_type = job_type
        self.pedestrians = pedestrians
        self.time_of_day = time_of_day
        self.weather = weather


class Playlist:

    def __init__(
            self,
            _id: str = None,
            name: str = None,

            platform: str = None,
            job_types: str = None,

            job_ids: list[str] = None,
            jobs: list[Job] = None,

            updated: datetime = None,
            created: datetime = None
    ):
        self._id = _id
        self.name = name
        self.url = f"https://gtalens.com/collection/{self._id}"

        self.platform = platform
        self.job_types = job_types

        self.job_ids = job_ids
        self.jobs = jobs

        self.updated = updated
        self.created = created


class Creator:
    def __init__(
            self,
            _id: str = "",
            name: str = "",

            playlists: list[Playlist] = None,
            playlists_url: str = None
    ):
        self._id = _id
        self.name = name
        self.url = f"https://gtalens.com/profile/{_id}"

        self.playlists = playlists
        self.playlists_url = playlists_url

    @property
    def id(self):
        return self._id


async def on_reaction_add(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:
    embed_type = embed_meta.split('type=')[1].split('/')[0]

    if embed_type == 'job_search':

        if emoji in embed_meta:
            job_id = embed_meta.split(f"{emoji}=")[1].split('/')[0]
            job = await get_job(job_id)

            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass

            await send_job(msg, client, job)

    elif embed_type == 'creator_playlist_search':

        if emoji in embed_meta:
            creator_id = embed_meta.split(f"{emoji}=")[1].split('/')[0]
            creator = get_creators(_id=creator_id)
            creator = await get_playlists(creator)

            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass

            await send_playlists(msg, creator)


async def on_reaction_remove(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:
    pass


''' JOB DATABASE '''


async def add_crew(crew_id: str) -> None:
    # http://scapi.rockstargames.com/crew/ranksWithMembership?crewId=31534161 &onlineService=sc&searchTerm=&memberCountToRetrieve=1000
    url = f"http://scapi.rockstargames.com/crew/ranksWithMembership?crewId={crew_id}" \
          "&onlineService=sc&searchTerm=&memberCountToRetrieve=1000"
    logger.debug(f"Jobs.add_crew() {url}")

    r_json: json = await Support.get_url(url, headers=Support.SCAPI_HEADERS)

    db: Database.DB = connect_database()

    db.cursor.execute(f"""
        INSERT INTO crews (
            _id, synced
        ) VALUES (
            '{crew_id}', '{datetime.utcnow().timestamp()}'
        ) ON DUPLICATE KEY UPDATE
            synced='{datetime.utcnow().timestamp()}'
        ;""")

    db.connection.commit()
    db.connection.close()

    await add_sc_members(r_json)


async def add_sc_members(crew_json: json) -> None:
    db: Database.DB = connect_database()

    if 'crewRanks' in crew_json:

        for rank in crew_json['crewRanks']:

            for member in rank['rankMembers']:
                db.cursor.execute(f"""
                    INSERT INTO members (
                        _id, _name
                    ) VALUES (
                        '{member['rockstarId']}', '{member['nickname']}'
                    ) ON DUPLICATE KEY UPDATE
                        _name='{member['nickname']}' 
                    ;""")

                primary_crew = member['primaryClan']
                db.cursor.execute(f"""
                    INSERT INTO crews (
                        _id, _name
                    ) VALUES (
                        '{primary_crew['id']}', '{replace_chars(primary_crew['name'])}' 
                    ) ON DUPLICATE KEY UPDATE
                        _name='{replace_chars(primary_crew['name'])}'
                    ;""")

    db.connection.commit()
    db.connection.close()


async def add_sc_member_jobs(sc_member_id: str) -> dict:
    db = connect_database()

    purged = False
    crews = {}
    for platform in [
        "ps4",
        "xboxone",
        "pc",
    ]:

        page_index = 0
        while True:

            url = f"http://scapi.rockstargames.com/search/mission?" \
                  f"dateRange=any&sort=date&platform={platform}&title=gtav&missiontype=race&" \
                  f"creatorRockstarId={sc_member_id}&pageIndex={page_index}&pageSize=30"
            logger.debug(f"Jobs.add_sc_member_jobs() {url}")

            r_json = await Support.get_url(url, headers=Support.SCAPI_HEADERS)

            if r_json:

                if r_json['status']:  # get was successful

                    utcnow = datetime.utcnow().timestamp()
                    db.cursor.execute(f"""
                        INSERT INTO members (
                            _id, synced
                        ) VALUES (
                            '{sc_member_id}', '{utcnow}'
                        ) ON DUPLICATE KEY UPDATE
                            synced='{utcnow}'
                    ;""")

                    db.connection.commit()

                    crews: dict = r_json['content']['crews']
                    for crew_id in crews:
                        crew = crews[crew_id]
                        db.cursor.execute(f"""
                            INSERT INTO crews (
                                _id, _name
                            ) VALUES (
                                '{crew['id']}', '{replace_chars(crew['name'])}' 
                            ) ON DUPLICATE KEY UPDATE
                                _name='{replace_chars(crew['name'])}'
                            ;""")

                    if r_json['content']['items']:  # jobs to add

                        if sc_member_id in r_json['content']['users']:

                            db.cursor.execute(f"""
                                UPDATE members
                                SET _name='{r_json['content']['users'][sc_member_id]['nickname']}'
                                WHERE _id='{sc_member_id}'
                            ;""")

                        for job in r_json['content']['items']:

                            if not purged:  # purging old tracks
                                db.cursor.execute(f"DELETE FROM jobs WHERE creator_id = '{sc_member_id}';")
                                db.connection.commit()
                                purged = True

                            db.cursor.execute(f"""
                                INSERT IGNORE INTO jobs (
                                    _id, _name, platform, updated, creator_id, synced
                                ) VALUES (
                                    '{job['id']}', 
                                    '{replace_chars(job['name'])}',
                                    '{platform}', 
                                    '{job['createdDate'].split('.')[0]}',
                                    '{sc_member_id}',
                                    '{datetime.utcnow().timestamp()}'
                                );""")

                        db.connection.commit()
                        page_index += 1

                    else:
                        db.connection.commit()
                        break

                else:
                    logger.warning(r_json)

                    sleep = 10
                    if 'error' in r_json:
                        if '3.000.2' in r_json['error']['code']:
                            sleep = 90

                        elif '3.000.1' in r_json['error']['code']:
                            sleep = 30

                    logger.info(f"Jobs.add_sc_member_jobs() was not successful, {url} sleeping for {sleep} seconds...")
                    await asyncio.sleep(sleep)

            else:
                break

        await asyncio.sleep(5)  # per platform

    db.connection.close()

    return crews


async def sync_job(message: discord.Message, job_link: str) -> (discord.Message, Job):
    job_id = job_link.split("gtav/")[-1]

    job = None
    msg = None
    if job_id:
        job = await get_job(job_id)

        embed = discord.Embed(
            colour=discord.Colour(Support.GTALENS_ORANGE),
            title=f"**Syncing {job.creator.name}'s jobs and crews...**"
        )
        msg = await message.channel.send(embed=embed)

        crews = await asyncio.shield(add_sc_member_jobs(job.creator.id))
        for crew_id in crews:
            await add_crew(crew_id)

        logger.info(f'Updated {job.creator.id}\'s jobs and crews')

        embed = discord.Embed(
            colour=discord.Colour(Support.GTALENS_ORANGE),
            title=f"**Synced {job.creator.name}'s Races**",
            description=f"Thank you for syncing {job.creator.name}'s jobs. "
                        f"Their ID is now in the database and will be synced periodically to stay up-to-date."
        )

    else:

        embed = discord.Embed(
            colour=discord.Colour(Support.GTALENS_ORANGE),
            title=f"**Missing Job ID**",
            description=f"It looks like the link you provided doesn't include the job id. "
                        f"The link should look something like this "
                        f"`https://socialclub.rockstargames.com/job/gtav/0mS1iV2tV06Wi-AJeQISbw`, "
                        f"\n\nSo, the command should look something like this "
                        f"\n`.lens sync https://socialclub.rockstargames.com/job/gtav/0mS1iV2tV06Wi-AJeQISbw`"
        )
        embed.set_footer(text="Having issues? Ask for help in the '.lens server'")

    if msg:
        await msg.edit(embed=embed)
    else:
        msg = await message.channel.send(embed=embed)
    return msg, job


def get_jobs(_id='%%'):
    db = Database.connect_database()
    db.cursor.execute(f"SELECT * FROM jobs WHERE _id LIKE '%{_id}%'")
    db.connection.close()
    return [Job(
        rockstar_id=j[0],
        name=j[1],
        platform=j[2],
        updated=datetime.strptime(j[3], "%Y-%m-%dT%H:%M:%S"),
        creator=Creator(_id=j[4]),
    ) for j in db.cursor.fetchall()]


''' CREATOR DATABASE '''


def get_creators(_id: str = ""):
    db = Database.connect_database()
    db.cursor.execute(f"SELECT * FROM members WHERE _id LIKE '%{_id}%'")

    if _id:
        _ = db.cursor.fetchall()[0]
        return Creator(
            _id=_[0],
            name=_[1]
        )

    else:
        creators = db.cursor.fetchall()
        for i, creator in enumerate(creators):
            creators[i] = Creator(
                _id=creator[0],
                name=creator[1]
            )
        return creators


''' JOB DISCORD '''


async def get_job(job_id: str) -> Job:
    # BGNZ Here Viggo Again!
    # https://gtalens.com/job/-zBNUcfmsUCiYznpiH_ldQ
    # https://gtalens.com/api/v1/jobs/info/-zBNUcfmsUCiYznpiH_ldQ

    full_info_url = "https://gtalens.com/api/v1/jobs/info/"  # + job_id
    basic_info_url = "https://gtalens.com/api/v1/jobs/basicinfo/"  # + job_id

    url = f"{full_info_url}{job_id}"
    r_json = await Support.get_url(url)

    if 'payload' in r_json:
        payload = r_json["payload"]
        job_dict = payload["job"]

        job: Job = Job(
            gtalens_id=job_dict["jobId"],
            rockstar_id=job_dict["jobCurrId"],
            name=job_dict["name"],
            description=job_dict["desc"],
            added=datetime.strptime(job_dict["adD"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            updated=datetime.strptime(job_dict["upD"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            synced=datetime.strptime(job_dict["fD"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            thumbnail=job_dict["img"].split("."),
            likes=job_dict["stats"]["lk"],
            dislikes=job_dict["stats"]["dlk"],
            total_plays=job_dict["stats"]["plT"],
            unique_plays=job_dict["stats"]["plU"],
            quits=job_dict["stats"]["qt"],
            rating=job_dict["stats"]["r"],
            platform=job_dict['plt'],
            creator=Creator(
                _id=payload["suppl"]["usersInfo"][0]["userId"],
                name=payload["suppl"]["usersInfo"][0]["username"]
            )
        )

        if 'vrtP' in payload['job']:
            print(payload['job']['vrtP'])
            print(payload['job']['vrt'])

            job.variants = payload['job']['vrt']  # get the gtalens id
            if job.gtalens_id in job.variants:
                del job.variants[job.variants.index(job.gtalens_id)]

            for i, p in enumerate(payload['job']['vrtP']):  # add the platform
                job.variants.append([job.variants[i], p])

    else:
        job: Job = get_jobs(_id=job_id)[0]
        job.gtalens_id = '?'

    while True:

        url = f"https://scapi.rockstargames.com/ugc/mission/details?title=gtav&contentId={job.rockstar_id}"
        logger.debug(f"Jobs.get_job() {url}")

        r_json = await Support.get_url(url, headers=Support.SCAPI_HEADERS)

        job.job_type = JOB_TYPE_CORRECTIONS[r_json['content']['type']]

        found_mission = False

        id_version: int = 0
        for id_version in range(10):  # id_version is the number of saves before publish

            for lang in [
                "en", "fr", "de", "pt", "es", "es-mx", "it", "ru", "ja", "pl", "zh", "zh-cn", "ko"
            ]:

                while True:

                    url = f"https://prod.cloud.rockstargames.com/ugc/gta5mission" \
                          f"/{job.rockstar_id}/0_{id_version}_{lang}.json"
                    logger.debug(f"Jobs.get_job() {url}")

                    r_json = await Support.get_url(url)

                    if r_json:
                        if 'mission' in r_json:
                            job.pedestrians = 'off' if r_json['mission']['rule']['apeds'] else 'on'
                            job.weather = WEATHER[r_json['mission']['rule']['weth']]
                            job.time_of_day = TIME_OF_DAY[r_json['mission']['rule']['tod']]

                            found_mission = True
                            break

                        elif 'JSONDecodeError' in r_json['error']['code']:
                            break

                    else:
                        break

                if found_mission:
                    break

            if found_mission:
                break

        if found_mission or id_version == 9:
            break

    logger.info(f"Got Job: {job.name} by {job.creator.name}")
    return job


def get_possible_jobs(job_name: str) -> list[Job]:
    job_name_lower = job_name.lower()
    jobs = get_jobs()
    possible_jobs = get_close_matches(
        job_name_lower, [j.name.lower() for j in jobs], n=6, cutoff=.3
    )  # list of job names - max 6 so the reactions don't go wider than the embed or new line
    possible_jobs = [jobs[i] for i in possible_jobs]

    if len(possible_jobs) > 1:

        if (
                possible_jobs[0].name.lower() == job_name_lower and
                possible_jobs[1].name.lower() != job_name_lower and
                job_name_lower not in possible_jobs[1].name.lower()
        ):  # only one exact match
            return [possible_jobs[0]]

    return possible_jobs


async def send_possible_jobs(
        message: discord.Message, client: discord.Client, possible_jobs: list[Job], job_name: str
) -> discord.Message:

    if len(possible_jobs) == 1:  # straight to sending the job embed
        msg = await send_job(message, client, await get_job(possible_jobs[0].rockstar_id))

    else:  # create embed for possible jobs list
        letters = list(Support.LETTERS_EMOJIS.keys())
        possible_jobs_str = ""
        embed_meta = "embed_meta/type=job_search/"

        for i, job in enumerate(possible_jobs):
            creator = get_creators(_id=job.creator.id)

            platform_emoji = str(discord.utils.find(
                lambda e: e.name == PLATFORM_CORRECTIONS[job.platform].lower(), client.get_guild(
                    Support.GTALENS_GUILD_ID).emojis))

            possible_jobs_str += f"\n{Support.LETTERS_EMOJIS[letters[i]]} " \
                                 f"{platform_emoji} " \
                                 f"[{job.name}](https://gtalens.com/job/{job.rockstar_id}) - " \
                                 f"[{creator.name}](https://gtalens.com/profile/{job.creator.id})"

            embed_meta += f"{Support.LETTERS_EMOJIS[letters[i]]}={job.rockstar_id}/"

        if not possible_jobs_str:
            possible_jobs_str = "\n\nThere were no close matches for your search. " \
                                "This may have happened because the job literally doesn't exist," \
                                " or it's not in the bot's database. " \
                                "The bot and the site use different databases," \
                                " so you may have better luck on the website."

        embed = discord.Embed(
            color=discord.Color(Support.GTALENS_ORANGE),
            title=f"**Search: *{job_name}***",
            description=f"[Search GTALens](https://gtalens.com/?page=1&search={job_name.replace(' ', '%20')}) **|** "
                        f"[Donate]({Support.DONATE_LINK})"
                        f"\n\nIf the searched track isn't in the results, "
                        f"it's possible the creator's races aren't being synced. "
                        f"To add the creator to the bot's database, use `.lens sync SC_TRACK_LINK` "
                        f"where SC_TRACK_LINK is the Social Club link to one of the creator's races."
                        f"\n\n**Results:**"
                        f"{possible_jobs_str}"
                        f"[{Support.ZERO_WIDTH}]({embed_meta})"
        )

        # TODO .lens creator creator_name
        # embed.set_footer(text=".lens creator creator_name")
        embed.set_footer(text=".lens playlist CREATOR")

        msg = await message.channel.send(embed=embed)
        for i, j in enumerate(possible_jobs):
            await msg.add_reaction(Support.LETTERS_EMOJIS[letters[i]])

    return msg


async def send_job(message: discord.Message, client: discord.Client, job: Job):
    variants_str = ""
    if job.variants:
        variants_str = f"**Variants ({len(job.variants)}):** "
        variants_str += ', '.join(
            [f"[{PLATFORM_CORRECTIONS[v[1]]}](https://gtalens.com/job/{v[0]})" for v in job.variants if type(v) == list]
        )
        variants_str += "\n"

    job_not_found = job.gtalens_id == '?'

    if not job_not_found:  # job found

        platform_emoji = str(discord.utils.find(
            lambda e: e.name == PLATFORM_CORRECTIONS[job.platform].lower(), client.get_guild(
                Support.GTALENS_GUILD_ID).emojis))

        embed = discord.Embed(
            color=discord.Colour(Support.GTALENS_ORANGE),
            title=f"**{platform_emoji} {job.name}**",
            description=f"\n[GTALens](https://gtalens.com/job/{job.gtalens_id}) **|** "
                        f"[R*SC](https://socialclub.rockstargames.com/job/gtav/{job.rockstar_id}) **|** "
                        f"[Donate](https://ko-fi.com/gtalens)\n\n"
                        f"{variants_str}"
                        f"**Creator:** [{job.creator.name}](https://gtalens.com/profile/{job.creator.id})"
                        f"\n*{job.description.strip()}*"
                        f"\n{Support.SPACE_CHAR}"
    
                        f"[{Support.ZERO_WIDTH}](embed_meta/type=job/gtalens_id={job.gtalens_id}/)",
        )

        embed.add_field(
            name=f"**__Ratings ({round(job.rating, 1)}%)__**",
            value=f"**Likes:** {job.likes}"
                  f"\n**Dislikes:** {job.dislikes} *+{job.quits}*"
                  f"\n**Plays:** {job.total_plays}"
                  f"\n**Unique:** {job.unique_plays}"
                  f"\n{Support.SPACE_CHAR}"
        )

        embed.add_field(
            name="**__Settings__**",
            value=f"**Type:** {job.job_type.title()}"  # job type, land/stunt...
            # f"\n**Mode:** {}"
                  f"\n**Pedestrians:** {job.pedestrians.title()}"
                  f"\n**Time:** {job.time_of_day.title()}"
                  f"\n**Weather:** {job.weather.title()}"
                  f"\n{'`.lens weather`' if job.weather == 'current' else ''}"  # must be last line cause \n
                  f"{Support.SPACE_CHAR}"
        )

        # TODO trending field?
        embed.add_field(
            name="**__Trending__**",
            value="*Coming soon!*"
        )

        embed.set_thumbnail(url=job.thumbnail)
        embed.set_footer(
            text=f"Updated: {Support.smart_day_time_format('{S} %b %Y', job.updated)} | "
                 f"Added: {Support.smart_day_time_format('{S} %b %Y', job.added)} | "
                 f"Synced: {Support.smart_day_time_format('{S} %b %Y', job.synced)}"
        )

    else:  # job was not found on gtalens
        not_found_str = "The job requested was not found on the GTALens site. The GTALens bot, and the site use " \
                        "different databases. It is possible for the bot to have jobs synced that the site does not " \
                        "and vice versa. You can request this job be imported on the site by going to the link above. "
        embed = discord.Embed(
            color=discord.Colour(Support.GTALENS_ORANGE),
            title=f"**{job.name}**",
            description=f"\n[GTALens Import](https://gtalens.com/job/{job.rockstar_id}) **|** "
                        f"[R*SC](https://socialclub.rockstargames.com/job/gtav/{job.rockstar_id}) **|** "
                        f"[Donate](https://ko-fi.com/gtalens)\n\n"
                        f"{not_found_str}"
        )

    msg = message
    if message.author.id != Support.GTALENS_CLIENT_ID:
        msg = await msg.channel.send(embed=embed)

    else:
        await msg.edit(embed=embed)

    crews = await asyncio.shield(add_sc_member_jobs(job.creator.id))
    for crew_id in crews:
        await add_crew(crew_id)

    logger.info(f'Updated {job.creator.id}\'s jobs and crews')

    return msg


''' PLAYLIST DISCORD '''


async def get_playlists(creator: Creator) -> Creator:
    creator.playlists_url = f"https://gtalens.com/api/v1/collections?type=1&page=1&platforms%5B0%5D=pc&platforms%5B1%5D=ps4&platforms%5B2%5D=xboxone&sort=updated&includeCount=true&userId={creator.id}"
    r_json = await Support.get_url(creator.playlists_url)

    if 'payload' in r_json:

        creator.playlists = []
        for collection in r_json['collections']:

            creator.playlists.append(
                Playlist(
                    _id=collection['_id'],
                    name=collection['name'],
                    platform=collection['jP'][0],
                    job_types=collection['jT'],
                    job_ids=[],
                    created=datetime.strptime(r_json["crD"], "%Y-%m-%dT%H:%M:%S.%fZ"),
                    updated=datetime.strptime(r_json["upD"], "%Y-%m-%dT%H:%M:%S.%fZ"),
                )
            )

            for job in collection:
                creator.playlists[-1].job_ids.append(job['id'])

        return creator


async def send_playlists(message: discord.Message, creator: Creator) -> discord.Message:

    playlists_str = ""
    for playlist in creator.playlists:
        playlists_str += f"[{playlist.name}]({playlist.url}) {str(datetime.utcnow() - playlist.updated)}\n"

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f"**{creator.name}'s Most Recently Updated Playlists**",
        description=f"[GTALens]({creator.playlists_url}) **|** [Donate]({Support.DONATE_LINK})"
                    f"\n\n{playlists_str}"
    )

    msg = message
    if message.author.id != Support.GTALENS_CLIENT_ID:
        msg = await msg.channel.send(embed=embed)
    else:
        await msg.edit(embed=embed)

    return msg

''' CREATORS DISCORD'''


def get_possible_creators(creator_name: str) -> list[Creator]:
    creator_name_lower = creator_name.lower()
    creators = get_creators()

    creator_names = [c.name for c in creators if c.name]
    possible_creators = get_close_matches(
        creator_name_lower, [c.lower() for c in creator_names], n=5, cutoff=.3
    )
    possible_creators = [creators[creator_names[i]] for i in possible_creators]

    if len(possible_creators) > 1:

        if (
            possible_creators[0].name.lower() == creator_name_lower and
            possible_creators[1].name.lower() != creator_name_lower and
            creator_name_lower not in possible_creators[1].name.lower()
        ):
            return [possible_creators[0]]

    return possible_creators


async def send_possible_creators(
        message: discord.Message, possible_creators: list[Creator], creator_name: str, embed_type: str
) -> discord.Message:

    if len(possible_creators) == 1:
        msg = await send_playlists(message, possible_creators[0])

    else:
        letters = list(Support.LETTERS_EMOJIS.keys())
        possible_creators_str = ""
        embed_meta = f"[{Support.ZERO_WIDTH}](embed_meta/type={embed_type}/)"

        for i, creator in enumerate(possible_creators):
            possible_creators_str += f"\n{Support.LETTERS_EMOJIS[letters[i]]}" \
                                     f"[{creator.name}]({creator.url})"

            embed_meta += f"{Support.LETTERS_EMOJIS[letters[i]]}={creator.name}/"

        if not possible_creators_str:
            possible_creators_str = "\n\nThere were no close matches for your search. " \
                                    "It may be possible the creator is not in the bot's database. " \
                                    "To add a creator use `.lens sync SC_TRACK_LINK`"

        embed = discord.Embed(
            color=discord.Color(Support.GTALENS_ORANGE),
            title=f"**Search: *{creator_name}***",
            description=f"[Search GTALens](https://gtalens.com/creators?page=1&search={creator_name.replace(' ', '%20')}) **|** "
                        f"[Donate]({Support.DONATE_LINK})"
                        f"\n\n**Results:**"
                        f"{possible_creators_str}"
                        f"[{Support.ZERO_WIDTH}]({embed_meta})"
        )

        msg = await message.channel.send(embed=embed)
        for i, j in enumerate(possible_creators):
            await msg.add_reaction(Support.LETTERS_EMOJIS[letters[i]])

        return msg