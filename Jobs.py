import asyncio
from datetime import datetime
from copy import deepcopy
import discord
import json
import logging
import pickle
from random import choices
import re

import mysql.connector.errors

import Database
from Database import connect_database, replace_chars
import Support

logger = logging.getLogger("discord")

JOB_SEARCH_ALIASES = ["track", "job", "race"]
PLAYLIST_SEARCH_ALIASES = ["playlists", "playlist", "collection", "collections"]
CREATOR_SEARCH_ALIASES = ["creator"]

SYNC_ALIASES = ["sync"]

EMBED_TYPES = [
    'job',
    'job_search',
    'creator_search_playlist',
    'creator_search'
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
    "LandRaceP2P": "land race P2P",
    "SeaRace": "sea race",
    "SpecialRace": "special race",
    "StuntRaceP2P": "stunt race P2P",
    "BikeRaceP2P": "bike race P2P"
}

PLATFORM_CORRECTIONS = {
    'xboxone': 'XB',
    'pc': 'PC',
    'ps4': 'PS',
    'xboxsx': 'XB',
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

            thumbnail: list[str] = None,  # [part 1, part 2]  some will have xxxx.x_0 some will just have x_0
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
            f"{self.rockstar_id}/{thumbnail[-1]}.jpg"
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


class Collection:

    def __init__(
            self,
            _id: str = None,
            name: str = None,
    ) -> None:
        self._id = _id
        self.name = name
        self.url = f"https://gtalens.com/collection/{self._id}"


class Creator:
    def __init__(
            self,
            _id: str = "",
            name: str = "",

            platform: str = "",

            pinned: list[Job] = None,
            promoted: list[Job] = None,
            trending: list[Job] = None,
            most_relevant: list[Job] = None,
            recently_added: list[Job] = None,
            most_replayed: list[Job] = None,
            recently_updated: list[Job] = None,
            most_played: list[Job] = None,
            most_viewed: list[Job] = None,
            recently_reviewed: list[Job] = None,
            least_played: list[Job] = None,

            collections: list[Collection] = None,
            playlists: list[Playlist] = None,
            playlists_url: str = None
    ):
        self._id = _id
        self.name = name
        self.url = f"https://gtalens.com/profile/{_id}"

        self.platform = platform

        self.pinned = pinned
        self.promoted = promoted
        self.trending = trending
        self.most_relevant = most_relevant
        self.recently_added = recently_added
        self.most_replayed = most_replayed
        self.recently_updated = recently_updated
        self.most_played = most_played
        self.most_viewed = most_viewed
        self.recently_reviewed = recently_reviewed
        self.least_played = least_played

        self.collections = collections
        self.playlists = playlists
        self.playlists_url = playlists_url

    @property
    def id(self):
        return self._id

    def __setstate__(self, state):
        new_state = Creator().__dict__
        new_state.update(state)
        self.__dict__.update(new_state)


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
            await Support.send_inbetween_msg(msg, "Job", f"https://gtalens.com/job/{job_id}")

            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass

            job = await get_job(job_id)

            await send_job(msg, client, job)

    elif embed_type == 'creator_search_playlist':

        if emoji in embed_meta:
            creator_id = embed_meta.split(f"{emoji}=")[1].split('/')[0]
            creator = get_pickled_creators()[creator_id]
            creator = await get_playlists(creator)

            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass

            await send_playlists(msg, creator)

    elif embed_type == "creator_search":

        if emoji in embed_meta:
            creator_id = embed_meta.split(f"{emoji}=")[1].split('/')[0]
            await Support.send_inbetween_msg(msg, "Creator", f"https://gtalens.com/profile/{creator_id}")

            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass

            creator = get_pickled_creators()[creator_id]

            await send_creator(msg, client, await get_creator_platforms(creator))


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

    r_json: json = await Support.get_url(url, headers=Support.SCAPI_HEADERS, proxies=True)

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
    utcnow = datetime.utcnow().timestamp()

    purged = False
    crews = {}
    for platform in [
        "ps4",
        "xboxone",
        "pc",
        "xboxsx"
    ]:

        page_index = 0
        tries = 2
        while tries:
            tries -= 1

            url = f"http://scapi.rockstargames.com/search/mission?" \
                  f"dateRange=any&sort=date&platform={platform}&title=gtav&missiontype=race&" \
                  f"creatorRockstarId={sc_member_id}&pageIndex={page_index}&pageSize=30"
            logger.debug(f"Jobs.add_sc_member_jobs() {url}")

            r_json = await Support.get_url(url, headers=Support.SCAPI_HEADERS, proxies=True)

            if r_json:

                if r_json['status']:  # get was successful

                    db.cursor.execute(f"""  
                        INSERT IGNORE INTO members (
                            _id
                        ) VALUES (
                            '{sc_member_id}'
                        )
                    ;""")

                    db.connection.commit()

                    crews.update(r_json['content']['crews'])
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

                        for job in r_json['content']['items']:

                            if not purged:  # purging old tracks
                                db.cursor.execute(f"DELETE FROM jobs WHERE creator_id = '{sc_member_id}';")
                                db.connection.commit()
                                purged = True

                            while True:
                                try:
                                    db.cursor.execute(f"""
                                        INSERT IGNORE INTO jobs (
                                            _id, _name, platform, updated, creator_id, synced
                                        ) VALUES (
                                            '{job['id']}', 
                                            '{replace_chars(job['name'])}',
                                            '{platform}', 
                                            '{job['createdDate'].split('.')[0]}',
                                            '{sc_member_id}',
                                            '{utcnow}'
                                        );""")
                                    break

                                except mysql.connector.errors.InternalError:
                                    # deadlock found when trying to get lock; try restarting transaction :shrug:
                                    logger.warning("mysql.connector.errors.InternalError, trying again in 1 second")
                                    await asyncio.sleep(1)

                        db.connection.commit()

                        if sc_member_id in r_json['content']['users']:

                            db.cursor.execute(f"""
                                UPDATE members 
                                SET _name='{r_json['content']['users'][sc_member_id]['nickname']}'
                                WHERE _id='{sc_member_id}'
                            ;""")

                        page_index += 1
                        await asyncio.sleep(1)

                    else:
                        db.connection.commit()
                        break

                else:
                    logger.warning(r_json)

                    sleep = 5
                    if 'error' in r_json:
                        if '3.000.2' in r_json['error']['code']:
                            sleep = 90

                        elif '3.000.1' in r_json['error']['code']:
                            sleep = 30

                    if tries:
                        logger.info(f"Jobs.add_sc_member_jobs() was not successful, {url} sleeping for {sleep} seconds... tries left: {tries}")
                        await asyncio.sleep(sleep)

            else:
                break

        # await asyncio.sleep(5)  # per platform

    db.cursor.execute(f"""
        UPDATE members
        SET synced = '{utcnow}'
        WHERE _id = '{sc_member_id}'
    ;""")

    db.connection.commit()
    db.connection.close()

    return crews


async def sync_job(message: discord.Message, job_link: str) -> (discord.Message, Job):

    if 'gtav/' in job_link:
        job_id = job_link.split("gtav/")[-1]

    else:
        job_id = None

    job = None
    msg = None
    if job_id:
        msg = await Support.send_inbetween_msg(message, "Job", f"https://gtalens.com/job/{job_id}")

        job = await get_job(job_id)

        if job:
            embed = discord.Embed(
                colour=discord.Colour(Support.GTALENS_ORANGE),
                title=f"**Syncing {job.creator.name}'s jobs and crews...**"
            )

            await msg.edit(embed=embed)

        else:
            embed = discord.Embed(
                colour=discord.Colour(Support.GTALENS_ORANGE),
                title="Job was not found on GTALens.com",
                description=f"The bot and the site use different databases, "
                            f"but the bot depends on site to have the job to get extra details. "
                            f"Request the job be added to the site by going to https://gtalens.com/job/{job_id} "
                            f"Once it's available on the site, "
                            f"then use `.lens sync` command again to sync it to the bot's database."
            )

            await msg.edit(embed=embed)
            logger.info(f'Sync Job: {job_id} not found on GTALens.com')

            return message, None

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
        logger.info(f'Sync Job: Missing Job ID')

    if msg:
        await msg.edit(embed=embed)
    else:
        msg = await message.channel.send(embed=embed)
    return msg, job


def get_jobs() -> list[Job]:
    db = Database.connect_database()
    db.cursor.execute(f"SELECT * FROM jobs")
    db.connection.close()
    return [Job(
        rockstar_id=j[0],
        name=j[1],
        platform=j[2],
        updated=datetime.strptime(j[3], "%Y-%m-%dT%H:%M:%S"),
        creator=Creator(_id=j[4]),
    ) for j in db.cursor.fetchall()]


def get_pickled_jobs(_id="") -> list[Job]:
    jobs: list[Job] = pickle.load(open("database_cache/jobs.pkl", "rb"))
    logger.info(f"Got {len(jobs)} jobs")
    return [j for j in jobs if not _id or j.rockstar_id == _id]


def pickle_jobs():
    logger.info("Updating jobs.pkl")
    jobs = get_jobs()
    pickle.dump(jobs, open("database_cache/jobs.pkl", "wb"))
    logger.info("Updated jobs.pkl")


''' CREATOR DATABASE '''


async def get_creator_platforms(creator):

    creator_platforms = {}
    for platform in PLATFORM_CORRECTIONS.keys():
        creator_platforms[platform] = deepcopy(creator)
        creator_platforms[platform].platform = platform
        creator_platforms[platform] = await get_gtalens_creator(creator_platforms[platform])

    return creator_platforms


async def get_gtalens_creator(creator: Creator) -> Creator:

    # get jobs
    url = f"https://gtalens.com/api/v1/jobs/explore?platforms%5B0%5D={creator.platform}&userId={creator.id}"

    r_json = await Support.get_url(url)
    logger.debug(f"Jobs.get_gtalens_creator() {url}")

    if 'payload' in r_json:
        payload = r_json['payload']

        if 'results' in payload:
            results = payload['results']

            for category in results:
                # promoted, pinned, trending, most-relevant, recently-added, most-replayed, recently- added

                cat = category['cat'].replace('-', '_')
                exec(f"creator.{cat} = []")

                for job in category['result']['jobs']:
                    job = Job(
                        gtalens_id=job['jobId'],
                        rockstar_id=job['jobCurrId'],
                        name=job['name']
                    )
                    exec(f"creator.{cat}.append(job)")

    # get collections
    url = f"https://gtalens.com/api/v1/collections?type=0&page=1&platforms[]=pc&platforms[]=ps4&platforms[]=xboxone&sorting=date_updated&userId={creator.id}"

    r_json = await Support.get_url(url)
    logger.debug(f"Jobs.get_gtalens_creator() {url}")

    if 'payload' in r_json:
        payload = r_json['payload']

        if 'collections' in payload:
            collections = payload['collections']

            if collections:
                creator.collections = []

            for collection in collections:

                collection = Collection(
                    _id=collection['_id'],
                    name=collection['name'],
                )

                creator.collections.append(collection)

    return creator


def get_creators() -> dict[str, Creator]:
    db = Database.connect_database()
    db.cursor.execute(f"SELECT * FROM members")
    creators = {}
    for creator in db.cursor.fetchall():
        creators[creator[0]] = Creator(
            _id=creator[0],
            name=creator[1] if creator[1] else ""
        )
    return creators


def get_pickled_creators() -> dict[str, Creator]:
    creators: dict[str, Creator] = pickle.load(open("database_cache/creators.pkl", "rb"))
    # check if creator attributes match Creator class
    logger.info(f"Got {len(creators)} creators")
    return creators


def pickle_creators():
    logger.info("Updating creators.pkl")
    creators = get_creators()
    pickle.dump(creators, open("database_cache/creators.pkl", "wb"))
    logger.info("Updated creators.pkl")


''' JOB DISCORD '''


async def get_job(job_id: str) -> Job:
    # BGNZ Here Viggo Again!
    # https://gtalens.com/job/-zBNUcfmsUCiYznpiH_ldQ
    # https://gtalens.com/api/v1/jobs/info/-zBNUcfmsUCiYznpiH_ldQ

    full_info_url = "https://gtalens.com/api/v1/jobs/info/"  # + job_id
    basic_info_url = "https://gtalens.com/api/v1/jobs/basicinfo/"  # + job_id

    url = f"{full_info_url}{job_id}"
    r_json = await Support.get_url(url)
    logger.debug(f"Jobs.get_job() {url}")

    if 'payload' in r_json:
        payload = r_json["payload"]
        job_dict = payload["job"]

        creator = Creator(
            _id=payload["suppl"]["usersInfo"][0]["userId"],
            name=payload["suppl"]["usersInfo"][0]["username"],
            platform=job_dict['plt']
        )

        creator: Creator = await get_gtalens_creator(creator)

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
            platform=creator.platform,
            creator=creator
        )

        if 'vrtP' in payload['job']:

            if 'vrt' in payload['job']:
                job.variants = payload['job']['vrt']  # get the gtalens id
                if job.gtalens_id in job.variants:
                    del job.variants[job.variants.index(job.gtalens_id)]

                for i, p in enumerate(payload['job']['vrtP']):  # add the platform
                    job.variants.append([job.variants[i], p])

    else:
        job: list[Job] = get_pickled_jobs(_id=job_id)
        if job:
            job: Job = job[0]
            job.gtalens_id = '?'

        else:
            return None

    tries = 2
    while tries:

        url = f"https://scapi.rockstargames.com/ugc/mission/details?title=gtav&contentId={job.rockstar_id}"
        logger.debug(f"Jobs.get_job() {url}")

        try:
            r_json = await Support.get_url(url, headers=Support.SCAPI_HEADERS, proxies=True)
            job.job_type = JOB_TYPE_CORRECTIONS[r_json['content']['type']]
            
        except KeyError:
            tries -= 1
            continue

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

    logger.info(f"Got Job: {job.name} by {job.creator.name} on {job.platform}")
    return job


def get_random_jobs() -> list[Job]:

    jobs: list[Job] = get_pickled_jobs()
    jobs = choices(jobs, k=6)
    return jobs


async def send_possible_jobs(
        msg: discord.Message, client: discord.Client, possible_jobs: list[Job], job_name: str
) -> discord.Message:

    if len(possible_jobs) == 1:  # straight to sending the job embed
        msg = await Support.send_inbetween_msg(msg, "Job", f"https://gtalens.com/job/{possible_jobs[0].gtalens_id}")
        msg = await send_job(msg, client, await get_job(possible_jobs[0].rockstar_id))

    else:  # create embed for possible jobs list
        letters = list(Support.LETTERS_EMOJIS.keys())
        possible_jobs_str = ""
        embed_meta = "embed_meta/type=job_search/"

        creators = get_pickled_creators()

        for i, job in enumerate(possible_jobs):
            creator = creators[job.creator.id]

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
            title=f"**Search: *{job_name if job_name != '.random' else 'Random Jobs...'}***",
            description=f"[Search GTALens](https://gtalens.com/?page=1&search={job_name.replace(' ', '%20')}) **|** "
                        f"[Donate]({Support.DONATE_LINK})"
                        f"\n\nIf the searched track isn't in the results, "
                        f"it's possible the creator's races aren't being synced. "
                        f"To add the creator to the bot's database, use `.lens sync SC_TRACK_LINK` "
                        f"where `SC_TRACK_LINK` is the Social Club link to one of the creator's races."
                        f"\n\n**Results:**"
                        f"{possible_jobs_str}"
                        f"[{Support.ZERO_WIDTH}]({embed_meta})"
        )

        embed.set_footer(text=".lens creator CREATOR")
        # TODO .lens playlist CREATOR
        # embed.set_footer(text=".lens playlist CREATOR")

        await msg.edit(embed=embed)
        for i, j in enumerate(possible_jobs):
            await msg.add_reaction(Support.LETTERS_EMOJIS[letters[i]])

    return msg


async def send_job(
        message: discord.Message, client: discord.Client, job: Job
) -> discord.Message:
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

        trending_str = ""
        trending: list[Job] = job.creator.trending
        if trending:  # guess sometimes, it doesn't get the details from gtalens?
            for j in trending[:5]:
                trending_str += f"[{j.name}](https://gtalens.com/job/{j.gtalens_id})\n"

            embed.add_field(
                name=f"**__{job.creator.name}'s Trending__**",
                value=trending_str
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
    if message.author.id not in Support.CLIENT_IDS.values():
        msg = await msg.channel.send(embed=embed)

    else:
        await msg.edit(embed=embed)

    logger.info(f"Sent Job: {job.name} by {job.creator.name} on {job.platform}")

    logger.info(f"Updating {job.creator.id}'s jobs and crews...")
    start = datetime.utcnow()

    crews = await asyncio.shield(add_sc_member_jobs(job.creator.id))
    for crew_id in crews:
        await add_crew(crew_id)

    end = datetime.utcnow()
    logger.info(f'Updated {job.creator.id}\'s jobs and crews')
    logger.info(f"Elapsed Time: {(end - start).total_seconds()} seconds")

    return msg


''' PLAYLIST DISCORD '''


async def get_playlists(creator: Creator) -> Creator:
    url = f"https://gtalens.com/api/v1/collections?type=1&page=1&platforms%5B0%5D=pc&platforms%5B1%5D=ps4&platforms%5B2%5D=xboxone&sort=updated&includeCount=true&userId={creator.id}"
    logger.debug(f"Jobs.get_playlists() {url}")

    r_json = await Support.get_url(url)

    creator.playlists_url = f"https://gtalens.com/collections/user/{creator.id}?type=1&sort=_updated"

    if 'payload' in r_json:

        creator.playlists = []
        for collection in r_json['payload']['collections']:

            creator.playlists.append(
                Playlist(
                    _id=collection['_id'],
                    name=collection['name'],
                    platform=collection['jP'][0],
                    job_types=collection['jT'],
                    job_ids=[],
                    created=datetime.strptime(collection["crD"], "%Y-%m-%dT%H:%M:%S.%fZ"),
                    updated=datetime.strptime(collection["upD"], "%Y-%m-%dT%H:%M:%S.%fZ"),
                )
            )

            for job in collection['jobs']:
                creator.playlists[-1].job_ids.append(job['id'])

        return creator


async def send_playlists(message: discord.Message, creator: Creator) -> discord.Message:

    # embed_meta = f"[{Support.ZERO_WIDTH}](embed_meta/type={embed_type}/)"

    playlists_str = ""
    for playlist in creator.playlists[:5]:
        days_delta: int = (datetime.utcnow() - playlist.updated).days
        days_delta_str = f"Updated {'Today' if not days_delta else f'{days_delta} days ago'}"
        playlists_str += f"[{playlist.name}]({playlist.url}) {days_delta_str}\n"

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f"**{creator.name}'s Most Recently Updated Playlists**",
        description=f"[GTALens]({creator.playlists_url}) **|** [Donate]({Support.DONATE_LINK})"
                    f"\n\n{playlists_str}"
    )

    msg = message
    if message.author.id not in Support.CLIENT_IDS.values():
        msg = await msg.channel.send(embed=embed)
    else:
        await msg.edit(embed=embed)

    return msg


''' CREATORS DISCORD'''


async def send_possible_creators(
        msg: discord.Message,
        client: discord.Client,
        possible_creators: list[Creator],
        creator_name: str,
        embed_type: str
) -> discord.Message:

    if len(possible_creators) == 1:
        msg = await Support.send_inbetween_msg(msg, "Creator", f"https://gtalens.com/profile/{possible_creators[0].id}")

        if embed_type == "creator_search_playlist":
            msg = await send_playlists(msg, possible_creators[0])

        else:
            msg = await send_creator(msg, client, await get_creator_platforms(possible_creators[0]))

        return msg

    else:
        letters = list(Support.LETTERS_EMOJIS.keys())
        possible_creators_str = ""
        embed_meta = f"[{Support.ZERO_WIDTH}](embed_meta/type={embed_type}/"

        for i, creator in enumerate(possible_creators):
            possible_creators_str += f"\n{Support.LETTERS_EMOJIS[letters[i]]} " \
                                     f"[{creator.name}]({creator.url})"

            embed_meta += f"{Support.LETTERS_EMOJIS[letters[i]]}={creator.id}/"

        if not possible_creators_str:
            possible_creators_str = "\n\nThere were no close matches for your search. " \
                                    "It may be possible the creator is not in the bot's database. " \
                                    "To add a creator use `.lens sync SC_TRACK_LINK`"

        embed = discord.Embed(
            color=discord.Color(Support.GTALENS_ORANGE),
            title=f"**Search: *{creator_name}***",
            description=f"[Search GTALens](https://gtalens.com/creators?page=1&q={creator_name.replace(' ', '%20')}) **|** "
                        f"[Donate]({Support.DONATE_LINK})"
                        f"\n\nIf the searched creator isn't in the results, "
                        f"it's possible the creator hasn't been synced in the bot's database yet. "
                        f"To force a sync, use `.lens sync SC_TRACK_LINK` "
                        f"where `SC_TRACK_LINK` is the Social Club link to one of the creator's races."
                        f"\n\n**Results:**"
                        f"{possible_creators_str}"
                        f"[{Support.ZERO_WIDTH}]({embed_meta})"
        )

        await msg.edit(embed=embed)

        for i, j in enumerate(possible_creators):
            await msg.add_reaction(Support.LETTERS_EMOJIS[letters[i]])

        return msg


async def send_creator(
        message: discord.Message, client: discord.Client, creator_platforms: dict[str, Creator]
) -> discord.Message:

    embed = discord.Embed(
        color=discord.Color(Support.GTALENS_ORANGE),
        title=f"**{creator_platforms['pc'].name}**",
        description=f"[GTALens]({creator_platforms['pc'].url}) **|** [Donate]({Support.DONATE_LINK})"
                    f"\n{Support.SPACE_CHAR}"
    )

    embed.set_thumbnail(url=f"https://a.rsg.sc//n/{creator_platforms['pc'].name.lower()}/n")

    collections = []
    if creator_platforms['pc'].collections:
        for collection in creator_platforms['pc'].collections:
            collections.append(f"[{collection.name}]({collection.url})")

        embed.add_field(
            name=f"{Support.BOOKS} **__Collections__**",
            value=f"{' **|** '.join(collections)}\n{Support.SPACE_CHAR}",
            inline=False
        )

    def get_jobs_str(jobs: list[Job]):
        jobs_str = ""
        for j in jobs[:5]:
            jobs_str += f"[{j.name}](https://gtalens.com/job/{j.gtalens_id})\n"

        return jobs_str

    pinned_platforms = []
    for platform in creator_platforms:
        creator = creator_platforms[platform]

        if creator.trending:
            platform_emoji = str(discord.utils.find(
                lambda e: e.name == PLATFORM_CORRECTIONS[platform].lower(), client.get_guild(
                    Support.GTALENS_GUILD_ID).emojis)
            )

            embed.add_field(
                name=f"{platform_emoji} **__Trending__**",
                value=f"{get_jobs_str(creator.trending)}{Support.SPACE_CHAR}",
                inline=True
            )

            embed.add_field(
                name=f"{platform_emoji} **__Recently Added__**",
                value=f"{get_jobs_str(creator.recently_added)}{Support.SPACE_CHAR}",
                inline=True
            )

            embed.add_field(
                name=f"{platform_emoji} **__Most Played__**",
                value=f"{get_jobs_str(creator.most_played)}{Support.SPACE_CHAR}",
                inline=True
            )

        if creator.pinned:
            pinned_platforms.append(platform)

    for platform in pinned_platforms:

        platform_emoji = str(discord.utils.find(
            lambda e: e.name == PLATFORM_CORRECTIONS[platform].lower(), client.get_guild(
                Support.GTALENS_GUILD_ID).emojis)
        )

        creator = creator_platforms[platform]

        embed.add_field(
            name=f"{platform_emoji} **__Pinned__**",
            value=f"{get_jobs_str(creator.pinned)}{Support.SPACE_CHAR}",
            inline=True
        )

    msg = message
    if msg.author.id not in Support.CLIENT_IDS.values():
        await message.channel.send(embed=embed)
    else:
        await msg.edit(embed=embed)

    logger.info(f"Sent creator: {', '.join([f'{p} - {creator_platforms[p]}' for p in creator_platforms])}")

    return msg


