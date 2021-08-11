
from datetime import datetime
from difflib import get_close_matches
import discord
import google.auth.exceptions
import json
import logging
import random
import requests
import sys

import Support


logger = logging.getLogger("discord")

ALIASES = ["car", "truck", "vehicle"]

BROUGHY_SPREADSHEET = "https://docs.google.com/spreadsheets/d/1nQND3ikiLzS3Ij9kuV-rVkRtoYetb79c52JWyafb4m4"
KEY_VEHICLE_INFO_SHEET_ID = 1689972026
BASIC_HANDLING_DATA_SHEET_ID = 110431106
OVERALL_LAP_TIME_SHEET_ID = 60309153


class Vehicle:
    def __init__(
            self,
            name: str = None,
            vehicle_class: str = None,

            # Key Attributes
            drivetrain: str = None,
            seats: str = None,
            manufacturer: str = None,
            race_tier: str = None,

            # Performance Improvements
            spoiler: str = None,
            off_roads: str = None,
            suspension: str = None,
            boost: str = None,
            drift_tyres: str = None,

            # Buying, Storing, & Upgrading
            source: str = None,
            cost: str = None,
            storage: str = None,
            upgrade: str = None,

            # Added to GTA Online
            date_added: float = None,  # timestamp
            dlc: str = None,
            other_notes: str = None,

            # Speed
            engine_stock: float = None,
            level_4_upgrade: int = None,
            engine_max: float = None,
            drag: float = None,
            max_speed: float = None,

            # Acceleration
            power_to_front: int = None,  # as %, so 100% is 100
            gears: int = None,
            upshift_rate: float = None,
            downshift_rate: float = None,

            # Braking
            brake_force: float = None,
            brake_bias: float = None,

            # Traction
            cornering_grip: float = None,
            straight_line_grip: float = None,
            off_road_grip_loss: float = None,

            # Collisions
            weight_kg: int = None,

            # AH Flag Issues
            flags_bouncy: str = None,
            flags_engine: str = None,

            # Evaluation
            pos_overall: dict[str, int] = None,  # {default, variants...: ...}
            pos_class: dict[str, int] = None,  # {default, variants...: ...}
            lap_times: dict[str, float] = None,  # {default, variants...: miliseconds}
            top_speeds_mph: dict[str, float] = None,  # {default, variants...: ...}
            # GTALens Information

            # GTALens
            gtalens_id: str = None,
            wiki_id: str = None,  # gta.fandom.com id
            images: dict[str, list[dict]] = None,
            description: str = None,
            video_id: str = None,  # youtube video id
    ):
        self.name = name

        self.vehicle_class = vehicle_class

        # Key Attributes
        self.drivetrain = drivetrain
        self.seats = seats
        self.manufacturer = manufacturer
        self.race_tier = race_tier

        # Performance Improvements
        self.spoiler = spoiler
        self.off_roads = off_roads
        self.suspension = suspension
        self.boost = boost
        self.drift_tyres = drift_tyres

        # Buying, Storing, & Upgrading
        self.source = source
        self.cost = cost
        self.storage = storage
        self.upgrade = upgrade

        # Added to GTA Online
        self.date_added = date_added
        self.dlc = dlc

        self.other_notes = other_notes

        # Speed
        self.engine_stock = engine_stock
        self.level_4_upgrade = level_4_upgrade
        self.engine_max = engine_max  # = stock + (stock * lvl4 * .0002)
        self.drag = drag
        self.max_speed = max_speed

        # Acceleration
        self.power_to_front = power_to_front
        self.gears = gears
        self.upshift_rate = upshift_rate
        self.downshift_rate = downshift_rate

        # Braking
        self.brake_force = brake_force
        self.brake_bias = brake_bias

        # Traction
        self.cornering_grip = cornering_grip
        self.straight_line_grip = straight_line_grip
        self.off_road_grip_loss = off_road_grip_loss

        # Collisions
        self.weight_kg = weight_kg

        # AH Flag Issues
        self.flags_bouncy = flags_bouncy
        self.flags_engine = flags_engine

        # Evaluation
        self.pos_overall = pos_overall
        self.pos_class = pos_class
        self.lap_times = lap_times
        self.top_speeds_mph = top_speeds_mph

        # GTALens Information
        self.gtalens_id = gtalens_id
        self.wiki_id = wiki_id
        self.images = images
        self.description = description
        self.video_id = video_id


async def on_reaction_add(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:

    if emoji == Support.WRENCH:
        vehicle_name = embed_meta.split("name=")[1].split("/")[0].replace('%20', ' ')
        vehicle = get_vehicle(vehicle_name)
        msg = await toggle_handling(vehicle, msg, msg.embeds[0], embed_meta)


async def on_reaction_remove(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:

    if emoji == Support.WRENCH:
        vehicle_name = embed_meta.split("name=")[1].split("/")[0].replace('%20', ' ')
        vehicle = get_vehicle(vehicle_name)
        msg = await toggle_handling(vehicle, msg, msg.embeds[0], embed_meta)


async def toggle_handling(
        vehicle: Vehicle, msg: discord.Message, embed: discord.Embed, embed_meta: str
) -> discord.Message:

    if embed_meta.split("handling=")[1].split("/")[0] == "[]":  # display handling
        embed = embed.to_dict()
        old_fields_len = len(embed['fields'])
        embed = discord.Embed.from_dict(embed)

        handling_fields: list[str] = []  # storing the indexes where the handling fields are used

        embed.add_field(name="test", value="yup, worked")
        handling_fields.append(str(old_fields_len + len(handling_fields)))

        embed_meta = embed_meta.replace("handling=[]", f"handling=[{','.join(handling_fields)}]")

    else:  # hide handling

        # get the indexes for the handling fields, currently as strings
        handling_field_indexes = embed_meta.split("handling=[")[1].split("]")[0].split(',')

        embed = embed.to_dict()
        for field_index in handling_field_indexes:
            del embed['fields'][int(field_index)]

        embed = discord.Embed.from_dict(embed)

        embed_meta = embed_meta.replace(
            f"handling={str([int(i) for i in handling_field_indexes]).replace(' ', '')}", f"handling=[]"
        )

    embed.description = embed.description.replace(
        embed.description.split("embed_meta/")[1],
        f"{embed_meta}"
    )  # replace old embed_meta with updated

    msg = await msg.edit(embed=embed)
    return msg


def get_vehicles() -> list[Vehicle]:
    vehicles = json.load(open("vehicles.json", "r"))
    for vehicle_name in vehicles:
        vehicles[vehicle_name] = Vehicle(**vehicles[vehicle_name])

    return vehicles


def get_vehicle(name: str) -> Vehicle:

    for i, pv in enumerate(poss_vehicles):  # fix vehicle names to be proper
        for v in vehicle_names:
            if pv == v.lower():
                poss_vehicles[i] = vehicles[v]

    # TODO ... the rest, currently have a list of vehicles that are close matches, returning first element for testing
    return poss_vehicles[0]


def get_vehicle_class(vehicle_class: str, vehicles: list[Vehicle]) -> list[Vehicle]:
    vehicle_class = [vehicles[v] for v in vehicles if vehicles[v].vehicle_class == vehicle_class]
    vehicle_class.sort(key=lambda v: (v.lap_times['default'] if v.lap_times else sys.maxsize))
    return vehicle_class


def update_vehicles():
    """
    :return: None, Saves to vehicles.json
    """

    g_client = Support.get_g_client()
    broughy_spreadsheet = g_client.open_by_url(BROUGHY_SPREADSHEET)

    while True:
        try:
            print("s_kvi")
            sheet_key_vehicle_info = broughy_spreadsheet.get_worksheet_by_id(
                KEY_VEHICLE_INFO_SHEET_ID
            )
            print("s_bhd")
            sheet_basic_handling_data = broughy_spreadsheet.get_worksheet_by_id(
                BASIC_HANDLING_DATA_SHEET_ID
            )
            print("s_olt")
            sheet_overall_lap_time = broughy_spreadsheet.get_worksheet_by_id(
                OVERALL_LAP_TIME_SHEET_ID
            )

            print("v_kvi")
            values_key_vehicle_info = sheet_key_vehicle_info.get_values(
                f"A4:V{sheet_key_vehicle_info.row_count}"
            )
            print("v_bhd")
            values_basic_handling_data = sheet_basic_handling_data.get_values(
                f"A4:T{sheet_basic_handling_data.row_count}"
            )
            print("v_olt")
            values_overall_lap_time = sheet_overall_lap_time.get_values(
                f"A4:F{sheet_overall_lap_time.row_count}"
            )
            break

        except requests.exceptions.ConnectionError:
            logger.info(
                "Connection Error attempting to update_vehicles. Trying again."
            )

        except google.auth.exceptions.TransportError:
            logger.info("Transport Error attempting to update_vehicles. Trying again.")

    vehicles: dict[str, Vehicle] = {}  # {name: Vehicle}

    for row in values_key_vehicle_info:
        name = row[1]

        vehicles[name] = Vehicle(
            name=name,
            vehicle_class=row[0],
            drivetrain=row[2],
            seats=row[3],
            manufacturer=row[4],
            race_tier=row[5],
            spoiler=row[6],
            off_roads=row[7],
            suspension=row[8],
            boost=row[9],
            drift_tyres=row[10],
            source=row[11],
            cost=row[12],
            storage=row[13],
            upgrade=row[14],
            # skipped race availability
            # regular 15
            # transform 16
            # other 17
            date_added=datetime.strptime(f"{row[18]} {row[19]}", "%d/%m %Y").timestamp()
            if "/" in row[18]
            else "",
            dlc=row[20],
            pos_overall={},
            pos_class={},
            lap_times={},
            top_speeds_mph={},
        )

        if len(row) > 21:
            vehicles[name].other_notes = row[21]

    for row in values_basic_handling_data:
        name = row[1]

        vehicles[name].engine_stock = float(row[2])
        vehicles[name].level_4_upgrade = int(row[3]) if row[3] != "-" else row[3]
        vehicles[name].engine_max = float(row[4]) if row[4] != "-" else row[4]
        vehicles[name].drag = float(row[5])
        vehicles[name].max_speed = float(row[6])
        vehicles[name].drivetrain = row[7]
        vehicles[name].power_to_front = int(row[8].replace("%", ""))
        vehicles[name].gears = int(row[9])
        vehicles[name].upshift_rate = float(row[10])
        vehicles[name].downshift_rate = float(row[11])
        vehicles[name].brake_force = float(row[12])
        vehicles[name].brake_bias = float(row[13])
        vehicles[name].cornering_grip = float(row[14])
        vehicles[name].straight_line_grip = float(row[15])
        vehicles[name].off_road_grip_loss = float(row[16])
        vehicles[name].weight_kg = int(row[17].replace(",", ""))

        row_len = len(row)
        if row_len > 18:
            vehicles[name].flags_bouncy = row[18]

            if row_len > 19:
                vehicles[name].flags_engine = row[19]

    variants = ["Min DF", "Mid DF", "Max DF"]  # for open wheel cars

    for row in values_overall_lap_time:
        name = row[3]

        variant = ""
        for v in variants:
            if v in name:
                variant = v
                name = name.replace(v, "")
                name = name.replace("()", "").strip()
                break

        vehicles[name].pos_overall["default"] = int(row[0])
        vehicles[name].pos_class["default"] = int(row[1])
        vehicles[name].lap_times["default"] = Support.minutes_seconds_to_seconds(row[4]) if row[4] else sys.maxsize
        vehicles[name].top_speeds_mph["default"] = float(row[5])

        if variant:
            vehicles[name].pos_overall[variant] = int(row[0])
            vehicles[name].pos_class[variant] = int(row[1])
            vehicles[name].lap_times[variant] = Support.minutes_seconds_to_seconds(row[4]) if row[
                4] else sys.maxsize
            vehicles[name].top_speeds_mph[variant] = float(row[5])

    page = 1
    while True:
        # https://gtalens.com/api/v1/vehicles?page=1&sorting=alphabet
        response = requests.get(
            "https://gtalens.com/api/v1/vehicles",
            params={"page": page, "sorting": "alphabet"},
        )
        response_dict = json.loads(response.text)

        if response_dict["success"]:

            if response_dict["payload"]["vehicles"]:

                for vehicle in response_dict["payload"]["vehicles"]:

                    if "name" in vehicle["meta"]:
                        name = vehicle["meta"]["name"]

                        # TODO handle variants like Police Cruiser (Buffalo)
                        # https://gtalens.com/api/v1/vehicles/vehicle/police2

                        if name in vehicles:
                            vehicles[name].gtalens_id = vehicle["_id"]
                            vehicles[name].wiki_id = vehicle["meta"]["wikiPage"]
                            vehicles[name].images = vehicle["images"]

                            if "description" in vehicle["meta"]:
                                vehicles[name].description = vehicle["meta"][
                                    "description"
                                ]

                            if "video" in vehicle["meta"]:
                                vehicles[name].video_id = vehicle["meta"]["video"]["id"]

            else:  # no vehicles
                break

        else:
            logger.info("update_vehicles failed getting GTALens information")
            break

        page += 1

    json.dump(
        {v: vehicles[v].__dict__ for v in vehicles},
        open("vehicles.json", "w"),
        indent=4,
    )


def get_possible_vehicles(name: str) :
    vehicles = get_vehicles()

    vehicle_names = list(vehicles.keys())
    poss_vehicles = get_close_matches(name.lower(), [v.lower() for v in vehicle_names])
    poss_vehicles = [vehicles[vehicle_names[i]] for i in poss_vehicles]


async def send_vehicle(
        vehicle: Vehicle, message: discord.Message, client: discord.Client
) -> discord.Message:

    # preparing complex string(s)
    manufacturer_emoji = str(discord.utils.find(
        lambda e: e.name == vehicle.manufacturer, client.get_guild(Support.GTALENS_GUILD_ID).emojis
    ))  # find the emoji in the GTALens Server that matches the manufacturer
    manufacturer_str = f"{manufacturer_emoji} {vehicle.manufacturer}"

    added_str = [
        f"Added {Support.smart_day_time_format('{S} %B %Y', datetime.fromtimestamp(vehicle.date_added))}"
    ]
    if vehicle.dlc != "-":
        added_str.append(vehicle.dlc)
    added_str = " - ".join(added_str)  # handling og cars oppose to dlc cars

    meta_str = f"[{Support.ZERO_WIDTH}](embed_meta/" \
               f"type=vehicle/" \
               f"name={vehicle.name.replace(' ', '%20')}/" \
               f"handling=[]/" \
               f"tiers=[]" \
               f")"

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f"**{manufacturer_str} {vehicle.name} ({vehicle.vehicle_class})**",
        description=f"\n[GTALens](https://gtalens.com/vehicle/{vehicle.gtalens_id}) **|** "
                    f"[Wiki](https://gta.fandom.com/{vehicle.wiki_id}) **|** "
                    f"[Donate]({Support.DONATE_LINK})"
                    f"\n{added_str}"
                    f"{meta_str}",
    )  # initial embed

    # preparing complex string(s)
    race_tier_str = (
        Support.LETTERS_EMOJIS[vehicle.race_tier.lower()]
        if vehicle.race_tier != "-"
        else vehicle.race_tier
    )

    lap_time_str = ""  # m:ss.000(*)
    if len(vehicle.lap_times) > 1:  # has variants
        lap_times = list(vehicle.lap_times.values())[1:]
        avg_lap_time = sum(lap_times) / len(lap_times)
        avg_lap_time = Support.seconds_to_minutes_seconds(avg_lap_time)
        lap_time_str = f"{avg_lap_time}\\*"

    else:
        if vehicle.lap_times:
            lap_time_str = Support.seconds_to_minutes_seconds(vehicle.lap_times['default'])
        else:
            lap_time_str = "-"

    top_speed_str = ""  # 123mph
    if len(vehicle.top_speeds_mph) > 1:  # has variants
        top_speeds = list(vehicle.top_speeds_mph.values())[1:]
        avg_top_speed = sum(top_speeds) / len(top_speeds)
        top_speed_str = f"{round(avg_top_speed, 2)}\\*"

    else:
        if vehicle.top_speeds_mph:
            top_speed_str = f"{round(vehicle.top_speeds_mph['default'], 2)}"
        else:
            top_speed_str = "-"

    flags_bouncy_str = (
        f"\n\n**{Support.FLAG_ON_POST} Bouncy:** {vehicle.flags_bouncy.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)} "
        if vehicle.flags_bouncy
        else ""
    )

    flags_engine_str = (
        f"\n**{Support.FLAG_ON_POST} Engine:** {vehicle.flags_engine.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)}"
        if vehicle.flags_engine
        else ""
    )

    # Key Attributes
    embed.add_field(
        name="**__Key Attributes__**",
        value=f"\n**Drivetrain:** {vehicle.drivetrain}"
              f"\n**Seats:** {vehicle.seats}"
              f"\n**Race Tier:** {race_tier_str}"
              f"\n**Lap Time:** {lap_time_str}"
              f"\n**Top Speed:** {top_speed_str}"
              f"{flags_bouncy_str}"
              f"{flags_engine_str}"
              f"\n{Support.SPACE_CHAR}"
    )

    # Performance Improvements
    embed.add_field(
        name="**__Improvements__**",
        value=f"\n**Spoiler:** {vehicle.spoiler.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)}"
              f"\n**Off-Roads:** {vehicle.off_roads.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)}"
              f"\n**Suspension:** {vehicle.suspension.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)}"
              f"\n**Boost:** {vehicle.boost.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)}"
              f"\n**Drift Tyres:** {vehicle.drift_tyres.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)}"
              f"\n{Support.SPACE_CHAR}"
    )

    # Buying, Storing & Upgrading
    embed.add_field(
        name="**__Ownership__**",
        value=f"\n**Source:** {vehicle.source}"
              f"\n**Cost:** {vehicle.cost}"
              f"\n**Storage:** {vehicle.storage}"
              f"\n**Upgrade:** {vehicle.upgrade}"
              f"\n{Support.SPACE_CHAR}"
    )

    image_name_conversion = {
        "scOld": "old-sc",
        "scNew": "new-sc",
        "website": "website",
        "impExp": "imp-exp",
    }
    image_name = random.choice(list(vehicle.images.keys()))
    images = (
        vehicle.images[image_name]["plates"]
        if image_name == "impExp"
        else vehicle.images[image_name]
    )
    image_filename = random.choice(images)["file"]
    image_name = image_name_conversion[image_name]

    embed.set_thumbnail(
        url=f"https://gtalens.com/assets/images/vehicles/{image_name}/{image_filename}"
    )

    if vehicle.other_notes:
        embed.set_footer(text=f"Note: {vehicle.other_notes}")

    if message.author.id == client.user.id:
        msg = await message.edit(embed=embed)
    else:
        msg = await message.channel.send(embed=embed)

    reactions_to_add = [Support.WRENCH]

    # adding tier buttons after wrench
    for v in get_vehicle_class(vehicle.vehicle_class, get_vehicles()):
        if v.race_tier not in ["-", "?"]:
            reaction = Support.LETTERS_EMOJIS[v.race_tier.lower()]
            if reaction not in reactions_to_add:
                reactions_to_add.append(reaction)

    for r in reactions_to_add:
        await msg.add_reaction(r)

    return msg


