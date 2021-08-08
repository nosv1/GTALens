from datetime import datetime
import discord
import json
import requests

import Support

ALIASES = ["track", "job", "race"]


class Job:
    def __init__(
        self,  # TODO add more attributes
        gtalens_id: str,
        rockstar_id: str,
        name: str,
        description: str,
        last_updated: datetime,
        thumbnail: list,  # [part1, part2]
        likes: int,
        dislikes: int,
        quits: int,
        total_plays: int,
        unique_plays: int,
        rating: float,
        user_name: str,
        user_id: str,
    ):
        self.gtalens_id = gtalens_id
        self.rockstar_id = rockstar_id
        self.name = name
        self.description = description
        self.thumbnail = (
            f"https://prod.cloud.rockstargames.com/ugc/gta5mission/"
            f"{thumbnail[0]}/{self.rockstar_id}/{thumbnail[1]}.jpg"
        )
        self.last_updated = last_updated

        self.likes = likes
        self.dislikes = dislikes
        self.quits = quits
        self.total_plays = total_plays
        self.unique_plays = unique_plays
        self.rating = rating

        self.user_name = user_name
        self.user_id = user_id

    async def send_job_embed(self, message: discord.Message):
        # FIXME this assumes brand new message, and not editable embed

        embed = discord.Embed(
            color=discord.Colour(Support.GTALENS_ORANGE),
            title=f"**__{self.name}__**",
            description=f"\n[GTALens](https://gtalens.com/job/{self.gtalens_id}) **|** "
            f"[R*SC](https://socialclub.rockstargames.com/job/gtav/{self.rockstar_id}) **|** "
            f"[Donate](https://ko-fi.com/gtalens)"
            f"\n\n[{self.user_name}](https://gtalens.com/profile/{self.user_id}): "
            f"{self.description}"
            f"\n\n:thumbsup: **{self.likes}** {round(self.rating, 1)}% "
            f":thumbsdown: **{self.dislikes}** +{self.quits}"
            f"\n:video_game: **{self.total_plays}** "
            f":bust_in_silhouette: **{self.unique_plays}**"
            # hiding information at the end of the description, separate vars by comma
            f"[{Support.ZERO_WIDTH}](gtalens_id={self.gtalens_id},)",
        )

        embed.set_thumbnail(url=self.thumbnail)
        embed.set_footer(text=f"Last Updated: {self.last_updated.strftime('%d %b %Y')}")

        print(json.dumps(embed.to_dict(), indent=4))

        return await message.channel.send(embed=embed)


# create a job from gtalens api endpoint


def get_job(job_id: str) -> Job:
    # BGNZ Here Viggo Again!
    # https://gtalens.com/job/-zBNUcfmsUCiYznpiH_ldQ
    # https://gtalens.com/api/v1/jobs/info/-zBNUcfmsUCiYznpiH_ldQ

    full_info_url = "https://gtalens.com/api/v1/jobs/info/"  # + job_id
    basic_info_url = "https://gtalens.com/api/v1/jobs/basicinfo/"  # + job_id

    response = requests.get(f"{full_info_url}{job_id}")
    response = json.loads(response.text)
    payload = response["payload"]
    job_dict = payload["job"]

    return Job(
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
        user_name=payload["suppl"]["usersInfo"][0]["username"],
        user_id=payload["suppl"]["usersInfo"][0]["userId"],
    )


async def edit_job_embed(message, add_remove="add", info="race") -> None:
    # TODO not needed until info becomes available in the endpoint
    """
    :param message:
    :param add_remove: 'add/remove' whether we're adding or removing a field
    :param info: 'race/general/map' which field we're adding or removing
    :return:
    """
    embed = message.embeds[0]
    job = get_job(embed.description.split("gtalens_id=")[1].split(",")[0])
