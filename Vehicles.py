from datetime import datetime
import discord
import discord.types.embed
import google.auth.exceptions
import json
import logging
import random
import requests
import sys

import Support

logger = logging.getLogger("discord")

SEARCH_ALIASES = ["car", "truck", "vehicle"]
TIER_ALIASES = ["tier"]
CLASS_ALIASES = ["class"]

EMBED_TYPES = [
    'vehicle',
    'vehicle_search',
]

BROUGHY_SPREADSHEET = "https://docs.google.com/spreadsheets/d/1nQND3ikiLzS3Ij9kuV-rVkRtoYetb79c52JWyafb4m4"
KEY_VEHICLE_INFO_SHEET_ID = 1689972026
BASIC_HANDLING_DATA_SHEET_ID = 110431106
OVERALL_LAP_TIME_SHEET_ID = 60309153

VEHICLE_CLASS_CORRECTIONS = {
    'Boats': 'boat',
    'Commercial': 'commercial',
    'Compacts': 'compacts',
    'Coupes': 'coupe',
    'Cycles': 'cycle',
    'Emergency': 'emergency',
    'Helicopters': 'helicopter',
    'Industrial': 'industrial',
    'Military': 'military',
    'Motorcycles': 'motorcycle',
    'Muscle': 'muscle',
    'Off-Road': 'off_road',
    'Open Wheel': 'open_wheel',
    'Planes': 'plane',
    'Sedans': 'sedan',
    'Service': 'service',
    'Sports': 'sport',
    'Sports Classics': 'sport_classic',
    'Supers': 'super',
    'SUVs': 'suv',
    'Utility': 'utility',
    'Vans': 'van'
}


class Vehicle:
    def __init__(
            self,
            name: str = None,
            vehicle_class: str = None,  # .Title()

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
            lap_times: dict[str, float] = None,  # {default, variants...: milliseconds}
            top_speeds_mph: dict[str, float] = None,  # {default, variants...: ...}
            # GTALens Information

            # GTALens
            gtalens_id: str = None,
            wiki_id: str = None,  # gta.fandom.com id
            images=None,  # dict[str, list[dict]]
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

    # for some reason, the attributes were none when tryna do this at init
    def get_brakes(self):
        brake_total = (self.brake_force * 10) * self.brake_bias
        diff = brake_total - self.cornering_grip

        if diff > 0.4:  # the stock brakes overcome the lack of cornering grip
            return Support.BALLOT_CHECKMARK

        else:
            return ""


async def on_reaction_add(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:
    embed_type = embed_meta.split('type=')[1].split('/')[0]

    if embed_type == 'vehicle':

        if emoji == Support.WRENCH:
            vehicle_name = embed_meta.split("name=")[1].split("/")[0].replace('%20', ' ')
            vehicle = get_vehicles()[vehicle_name]
            await toggle_handling(msg, msg.embeds[0], embed_meta, vehicle)

        elif emoji in embed_meta:  # tier button clicked
            vehicle_name = embed_meta.split("name=")[1].split("/")[0].replace('%20', ' ')
            vehicle = get_vehicles()[vehicle_name]
            tier = list(Support.LETTERS_EMOJIS.keys())[list(Support.LETTERS_EMOJIS.values()).index(emoji)].upper()
            await toggle_tier(
                msg, msg.embeds[0], embed_meta, vehicle, tier)

    elif embed_type == 'vehicle_search':

        if emoji in embed_meta:
            vehicle_name = embed_meta.split(f"{emoji}=")[1].split('/')[0].replace('%20', ' ')
            vehicle = get_vehicles()[vehicle_name]
            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass
            await send_vehicle(msg, client, vehicle)


async def on_reaction_remove(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:
    embed_type = embed_meta.split('type=')[1].split('/')[0]

    if embed_type == 'vehicle':

        if emoji == Support.WRENCH:
            vehicle_name = embed_meta.split("name=")[1].split("/")[0].replace('%20', ' ')
            vehicle = get_vehicles()[vehicle_name]

            msg = await toggle_handling(msg, msg.embeds[0], embed_meta, vehicle)

        elif emoji in embed_meta:  # tier button clicked
            vehicle_name = embed_meta.split("name=")[1].split("/")[0].replace('%20', ' ')
            vehicle = get_vehicles()[vehicle_name]
            tier = list(Support.LETTERS_EMOJIS.keys())[list(Support.LETTERS_EMOJIS.values()).index(emoji)].upper()
            await toggle_tier(
                msg, msg.embeds[0], embed_meta, vehicle, tier)


async def toggle_tier(
        msg: discord.Message, embed: discord.Embed, embed_meta: str, vehicle: Vehicle, tier: str
) -> discord.Message:
    old_tiers_displayed = embed_meta.split('tiers_displayed=')[1].split("/")[0]
    tiers_displayed = [t for t in embed_meta.split('tiers_displayed=')[1].split("/")[0].split(',') if t]

    old_tier_indices = [
        int(i) for i in embed_meta.split('tier_indices=')[1].split("/")[0].split(',') if i != ''
    ]
    old_handling_indices = [
        int(i) for i in embed_meta.split('handling_indices=')[1].split("/")[0].split(',') if i != ''
    ]
    old_indices = old_tier_indices + old_handling_indices

    if tier not in old_tiers_displayed:  # display tier
        tiers_displayed.append(tier)
        tiers_displayed = ','.join(tiers_displayed).replace('S', '.').split(",")
        tiers_displayed.sort()
        tiers_displayed = ','.join(tiers_displayed).replace('.', 'S').split(',')

    else:
        del tiers_displayed[tiers_displayed.index(tier)]

    tier_fields: list[dict] = []
    vehicles = get_vehicles()
    for tier in tiers_displayed:
        if tier:  # first tier may be blank cause tiers_displayed=/ and split gives ''
            vehicles_tier, str_vehicles_tier = get_tier(tier, vehicle=vehicle, vehicles=vehicles)
            tier_field = {
                'name': f'__**{tier} Tier**__',
                'value': f'{str_vehicles_tier}',
                'inline': True
            }
            tier_fields.append(tier_field)

    embed = embed.to_dict()

    default_fields: list[discord.types.embed.EmbedField] = []
    for i, field in enumerate(embed['fields']):
        if i not in old_indices:
            default_fields.append(field)

    embed['fields'] = default_fields + tier_fields
    tier_indices = ','.join(str(i + len(default_fields)) for i in range(len(tier_fields)))

    embed = discord.Embed.from_dict(embed)

    embed_meta = embed_meta.replace(
        f"tier_indices={','.join(str(i) for i in old_tier_indices)}",
        f"tier_indices={tier_indices}"
    )

    embed_meta = embed_meta.replace(
        f"tiers_displayed={old_tiers_displayed}",
        f"tiers_displayed={','.join(tiers_displayed)}"
    )

    embed_meta = embed_meta.replace(
        f"handling_indices={','.join(str(i) for i in old_handling_indices)}",
        f"handling_indices="
    )

    embed.description = embed.description.replace(
        embed.description.split('embed_meta/')[1],
        embed_meta
    )

    await msg.edit(embed=embed)

    return msg


async def toggle_handling(
        msg: discord.Message, embed: discord.Embed, embed_meta: str, vehicle: Vehicle
) -> discord.Message:
    old_tier_indices = [
        int(i) for i in embed_meta.split('tier_indices=')[1].split("/")[0].split(',') if i != ''
    ]
    old_handling_indices = [
        int(i) for i in embed_meta.split('handling_indices=')[1].split("/")[0].split(',') if i != ''
    ]
    old_indices = old_tier_indices + old_handling_indices

    embed = embed.to_dict()

    default_fields: list[discord.types.embed.EmbedField] = []
    for i, field in enumerate(embed['fields']):
        if i not in old_indices:
            default_fields.append(field)

    embed['fields'] = default_fields

    if not old_handling_indices:  # make handling fields
        handling_fields = [
            {
                'name': f"**__Speed__**",
                'value': f"**Engine (Stock)**: {vehicle.engine_stock}"
                         f"\n**Lvl 4 Upgrade**: {vehicle.level_4_upgrade}"
                         f"\n**Drag**: {vehicle.drag}"
                         f"\n**Max Speed**: {vehicle.max_speed}"
                         f"\n{Support.SPACE_CHAR}",
                'inline': True
            },
            {
                'name': f"**__Acceleration__**",
                'value': f"**Power To Front**: {vehicle.power_to_front}%"
                         f"\n**Gears**: {vehicle.gears}"
                         f"\n**Upshift Rate**: {vehicle.upshift_rate}"
                         f"\n**Downshift Rate**: {vehicle.downshift_rate}"
                         f"\n{Support.SPACE_CHAR}",
                'inline': True
            },
            {
                'name': f"**__Braking__**",
                'value': f"**Brake Force**: {vehicle.brake_force}"
                         f"\n**Brake Bias**: {vehicle.brake_bias}"
                         f"\n{Support.SPACE_CHAR}",
                'inline': True
            },
            {
                'name': f"**__Traction__**",
                'value': f"**Cornering Grip:** {vehicle.cornering_grip}"
                         f"\n**Straight Line Grip:** {vehicle.straight_line_grip}"
                         f"\n**Off-Road Grip Loss:** {vehicle.off_road_grip_loss}"
                         f"\n{Support.SPACE_CHAR}",
                'inline': True
            },
            {
                'name': "**__Collisions__**",
                'value': f"**Weight**: {vehicle.weight_kg}kg"
                         f"\n{Support.SPACE_CHAR}",
                'inline': True
            },
        ]

    else:
        handling_fields = []

    embed['fields'] = default_fields + handling_fields

    embed = discord.Embed.from_dict(embed)

    embed_meta = embed_meta.replace(
        f"handling_indices={','.join(str(i) for i in old_handling_indices)}",
        f"handling_indices={','.join(str(i + len(default_fields)) for i in range(len(handling_fields)))}"
    )

    embed_meta = embed_meta.replace(
        f"tier_indices={','.join(str(i) for i in old_tier_indices)}",
        f"tier_indices="
    )

    # embed_meta = embed_meta.replace(
    #     f"tiers_displayed={embed_meta.split('tiers_displayed=')[1].split('/')[0]}",
    #     f"tiers_displayed="
    # )  # leaving this out, lets it remember what tiers were displayed if handling is toggled

    embed.description = embed.description.replace(
        embed.description.split('embed_meta/')[1],
        embed_meta
    )

    await msg.edit(embed=embed)
    return msg


def get_vehicles() -> dict[str, Vehicle]:
    vehicles = json.load(open("vehicles.json", "r"))
    for vehicle_name in vehicles:
        vehicles[vehicle_name] = Vehicle(**vehicles[vehicle_name])

    return vehicles


def get_vehicle_class(vehicle_class: str, vehicles: dict[str, Vehicle]) -> list[Vehicle]:
    vehicle_class = [vehicles[v] for v in vehicles if vehicles[v].vehicle_class == vehicle_class]
    vehicle_class.sort(key=lambda v: (v.lap_times['default'] if v.lap_times else sys.maxsize))
    return vehicle_class


async def send_vehicle_class(
        msg: discord.Message, vehicles_class: list[Vehicle], vehicle_class: str
) -> discord.Message:

    embed = discord.Embed(
        color=discord.Color(Support.GTALENS_ORANGE),
        title=f"**{vehicle_class} ({len(vehicles_class)})**",
        description=f"[GTALens](https://gtalens.com/vehicles/?classes[0]={VEHICLE_CLASS_CORRECTIONS[vehicle_class]}) "
                    f"**|** [Donate]({Support.DONATE_LINK})"
    )

    # this is terrible, but basically, storing tier letters in tiers and then again in the dict
    # sort the tiers, then loop through that and getting the strings from the dict
    tiers = []
    tier_strs = {}
    for vehicle in vehicles_class:

        tier = vehicle.race_tier.lower()

        if tier == "s":  # big S to sort at front
            tier = "S"
        elif tier == "-":  # x and z to put at the back
            tier = "x"
        elif tier == "?":
            tier = "z"

        if tier not in tiers:
            vehicles_tier, vehicles_tier_str = get_tier(
                vehicle.race_tier, vehicles_class=vehicles_class
            )

            tiers.append(tier)
            tier_strs[tier] = vehicles_tier_str

    tiers.sort(key=lambda x: x[0])

    for tier in tiers:
        vehicles_tier_str = tier_strs[tier]
        tier = tier.upper()
        if tier == "X":
            tier_str = "**__Not Raceable__**"

        elif tier == "Z":
            tier_str = "**__Unknown__**"

        else:
            tier_str = f"**__{tier} Tier__**"

        if len(vehicles_tier_str) > 1024:  # of course this only works if it's less than < 1024 * 2
            vehicle_tier_str_lines = vehicles_tier_str.split("\n")[:-1]  # removing space char
            len_vehicle_tier_str_lines = len(vehicle_tier_str_lines)

            vehicle_tier_strs_lines = [
                vehicle_tier_str_lines[:len_vehicle_tier_str_lines // 2],
                vehicle_tier_str_lines[len_vehicle_tier_str_lines // 2:]
            ]

            embed.add_field(
                name=tier_str,
                value=f'\n'.join(vehicle_tier_strs_lines[0]) + f"\n{Support.SPACE_CHAR}"
            )

            embed.add_field(
                name=f"{tier_str} **__cont.__**",
                value=f'\n'.join(vehicle_tier_strs_lines[1]) + f"\n{Support.SPACE_CHAR}"
            )

        else:
            embed.add_field(
                name=f"{tier_str}",
                value=vehicles_tier_str
            )

    await msg.edit(embed=embed)
    return msg


def get_tier(
        tier: str, vehicle: Vehicle = None, vehicles_class: list[Vehicle] = None, vehicles: dict[str, Vehicle] = None
) -> (list[Vehicle], str):
    """

    :param vehicles_class:
    :param tier: uppercase tier
    :param vehicle: deltas based on vehicle if provided, else top of tier
    :param vehicles_class: required if no vehicle
    :param vehicles:
    :return:
    """

    if not vehicles:
        vehicles = get_vehicles()

    if not vehicles_class:
        vehicles_class = get_vehicle_class(vehicle.vehicle_class, vehicles)

    vehicles_tier: list[Vehicle] = [v for v in vehicles_class if v.race_tier == tier]
    vehicles_tier.sort(key=lambda v: v.lap_times['default'] if 'default' in v.lap_times else sys.maxsize)

    if not vehicles_tier:  # likely invalid tier given, possible with .lens tier
        return [], ''

    str_vehicles_tier_lines: list[str] = []

    if vehicle and 'default' in vehicle.lap_times:
        base_time = vehicle.lap_times['default']

    elif 'default' in vehicles_tier[0].lap_times:  # tier may be ? sometimes, like in send_class
        base_time = vehicles_tier[0].lap_times['default']

    else:
        base_time = 0

    for tier_vehicle in vehicles_tier:

        line = ""
        if 'default' in tier_vehicle.lap_times:
            line += f"`{tier_vehicle.lap_times['default'] - base_time:+.3f}` {tier_vehicle.name}"

        else:
            line += f"`-{0:.3f}` {tier_vehicle.name}"

        str_vehicles_tier_lines.append(line if vehicle and tier_vehicle.name != vehicle.name else f"**{line}**")

    str_vehicles_tier_lines.append(Support.SPACE_CHAR)

    return vehicles_tier, '\n'.join(str_vehicles_tier_lines)


async def send_tier(
        msg: discord.Message,
        tier: str,
        vehicles_tier: list[Vehicle],
        vehicles_tier_str: str,
        vehicles_class: list[Vehicle]
) -> discord.Message:

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f"__**{tier} Tier ({vehicles_class[0].vehicle_class})**__",
    )

    if vehicles_tier:  # vehicles actually in the tier
        embed.description = vehicles_tier_str[:-1]  # removing space_char

    else:
        a_an = "an" if tier in ['A', 'E', 'F', 'H', 'I', 'L', 'M', 'N', 'O', 'R', 'S'] else 'a'
        embed.description = f"The {vehicles_class[0].vehicle_class} class does not have {a_an} {tier} Tier."

    await msg.edit(embed=embed)
    return msg


async def update_vehicles():
    """
    :return: None, Saves to vehicles.json
    """

    g_client = Support.get_g_client()
    broughy_spreadsheet = g_client.open_by_url(BROUGHY_SPREADSHEET)

    while True:
        try:
            logger.debug("s_kvi")
            sheet_key_vehicle_info = broughy_spreadsheet.get_worksheet_by_id(
                KEY_VEHICLE_INFO_SHEET_ID
            )
            logger.debug("s_bhd")
            sheet_basic_handling_data = broughy_spreadsheet.get_worksheet_by_id(
                BASIC_HANDLING_DATA_SHEET_ID
            )
            logger.debug("s_olt")
            sheet_overall_lap_time = broughy_spreadsheet.get_worksheet_by_id(
                OVERALL_LAP_TIME_SHEET_ID
            )

            logger.debug("v_kvi")
            values_key_vehicle_info = sheet_key_vehicle_info.get_values(
                f"A4:V{sheet_key_vehicle_info.row_count}"
            )
            logger.debug("v_bhd")
            values_basic_handling_data = sheet_basic_handling_data.get_values(
                f"A4:T{sheet_basic_handling_data.row_count}"
            )
            logger.debug("v_olt")
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
        url = f"https://gtalens.com/api/v1/vehicles?page={page}&sorting=alphabet"
        logger.debug(f"Vehicles.update_vehicles() {url}")

        r_json = await Support.get_url(url)

        if r_json["success"]:

            if r_json["payload"]["vehicles"]:

                for vehicle in r_json["payload"]["vehicles"]:

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
            logger.info(f"update_vehicles failed getting GTALens information {url}")
            break

        page += 1

    json.dump(
        {v: vehicles[v].__dict__ for v in vehicles},
        open("vehicles.json", "w"),
        indent=4,
    )

    logger.info("Vehicles Updated")


async def send_possible_vehicles(
        msg: discord.Message, client: discord.Client, possible_vehicles: list[Vehicle], vehicle_name: str
) -> discord.Message:

    if len(possible_vehicles) == 1:  # straight to sending the job embed
        msg = await send_vehicle(msg, client, possible_vehicles[0])

    else:  # create embed for possible jobs list
        letters = list(Support.LETTERS_EMOJIS.keys())
        possible_vehicles_str = ""
        embed_meta = f"[{Support.ZERO_WIDTH}](embed_meta/type=vehicle_search/)"

        for i, vehicle in enumerate(possible_vehicles):
            possible_vehicles_str += f"\n{Support.LETTERS_EMOJIS[letters[i]]} " \
                                     f"[{vehicle.name}](https://gtalens.com/vehicle/{vehicle.gtalens_id}) - " \
                                     f"[{vehicle.vehicle_class}](https://gtalens.com/vehicles/?classes[0]=" \
                                     f"{VEHICLE_CLASS_CORRECTIONS[vehicle.vehicle_class]})"

            embed_meta += f"{Support.LETTERS_EMOJIS[letters[i]]}={vehicle.name.replace(' ', '%20')}/"

        if not possible_vehicles_str:
            possible_vehicles_str = "\n\nThere were no close matches for your search. " \
                                    "It can only be suggested you use more letters in your query."

        embed = discord.Embed(
            color=discord.Color(Support.GTALENS_ORANGE),
            title=f"**Search: *{vehicle_name}***",
            description=f"[Search GTALens](https://gtalens.com/vehicles/?t={vehicle_name.replace(' ', '%20')}) **|** "
                        f"[Donate]({Support.DONATE_LINK})"
                        f"\n\n**Results:**"
                        f"{possible_vehicles_str}"
                        f"[{Support.ZERO_WIDTH}]({embed_meta})"
        )

        embed.set_footer(text=".lens tier CLASS TIER | .lens class CLASS")

        await msg.edit(embed=embed)

        for i, j in enumerate(possible_vehicles):
            await msg.add_reaction(Support.LETTERS_EMOJIS[letters[i]])

    return msg


async def send_vehicle(message: discord.Message, client: discord.Client, vehicle: Vehicle
                       ) -> discord.Message:
    # preparing complex string(s)
    manufacturer_emoji = discord.utils.find(
        lambda e: e.name == vehicle.manufacturer, client.get_guild(Support.GTALENS_GUILD_ID).emojis
    )  # find the emoji in the GTALens Server that matches the manufacturer
    manufacturer_str = f"{f'{manufacturer_emoji} ' if manufacturer_emoji else ''}{vehicle.manufacturer}"

    added_str = []
    if vehicle.date_added:
        added_str.append(
            f"Added {Support.smart_day_time_format('{S} %B %Y', datetime.fromtimestamp(vehicle.date_added))}"
        )

    else:
        added_str.append("Not added yet")

    if vehicle.dlc != "-":
        added_str.append(vehicle.dlc)
    added_str = " - ".join(added_str)  # handling og cars oppose to dlc cars

    vehicle_class = get_vehicle_class(vehicle_class=vehicle.vehicle_class, vehicles=get_vehicles())
    tiers = []
    for v in vehicle_class:
        if v.race_tier not in ["-", "?"]:
            if v.race_tier not in tiers:
                tiers.append(v.race_tier)

    embed_meta = f"[{Support.ZERO_WIDTH}](embed_meta/" \
                 f"type=vehicle/" \
                 f"name={vehicle.name.replace(' ', '%20')}/" \
                 f"handling_indices=/" \
                 f"tier_indices=/" \
                 f"tiers_displayed=/" \
                 f"tiers_avail={','.join([Support.LETTERS_EMOJIS[t.lower()] for t in tiers])}/" \
                 f")"

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f"**{manufacturer_str} {vehicle.name} ({vehicle.vehicle_class})**",
        description=f"\n[GTALens](https://gtalens.com/vehicle/{vehicle.gtalens_id}) **|** "
                    f"[Wiki](https://gta.fandom.com/{vehicle.wiki_id}) **|** "
                    f"[Donate]({Support.DONATE_LINK})"
                    f"\n{added_str}"
                    f"{embed_meta}",
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
        f"\n\n**{Support.FLAG_ON_POST} Bouncy:** "
        f"{vehicle.flags_bouncy.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)} "
        if vehicle.flags_bouncy
        else ""
    )

    flags_engine_str = (
        f"\n**{Support.FLAG_ON_POST} Engine:** "
        f"{vehicle.flags_engine.replace(Support.HEAVY_CHECKMARK, Support.BALLOT_CHECKMARK)}"
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
              f"\n**Stock Brakes:** {vehicle.get_brakes()}"
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

    # TODO apparently some vehicles don't have images, that's due to the names not matching from broughy spreadsheet and gtalens
    if vehicle.images:
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
        await message.edit(embed=embed)
        msg = message
    else:
        msg = await message.channel.send(embed=embed)

    reactions_to_add = [Support.WRENCH]

    # adding tier buttons after wrench
    [reactions_to_add.append(Support.LETTERS_EMOJIS[t.lower()]) for t in tiers]

    for r in reactions_to_add:
        await msg.add_reaction(r)

    logger.info(f"Sent vehicle: {vehicle.name}")

    return msg
