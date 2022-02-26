from dataclasses import dataclass
import discord
import docx
import json
import logging
import re
import requests
from simplify_docx import simplify

import Support

logger = logging.getLogger("discord")

SEARCH_ALIASES = ["wheel", "wheels", "tyre", "tyres", "tire", "tires"]
EMBED_TYPES = [
    'wheel',
    'wheel_search',
]
WHEEL_TYPE_CORRECTIONS = {
    "High End": "High Ends",
    "Lowrider": "Lowriders",
    "Muscle": "Muscles",
    "Offroad": "Offroads", 
    "Sport": "Sports", 
    "SUV’s": "SUVs", 
    "Tuners": "Tuners", 
    "Street": "Streets", 
    "Benny’s Bespoke": "Benny's Bespokes", 
    "Benny’s Originals": "Benny's Originals", 
    "Track": "Tracks"
}
WHEEL_EFFECTS_CORRECTIONS = {
    "Traction Bias": "bias",
    "Anti-roll": "ar",
    "Slip Angle": "slip"
}

SPEARS_TYRE_DOC_ID = '18wmgSQPmHatQzXgmqT-y7yU5D4aGP3xC'
SPEARS_TYRE_DOC_LINK = f'https://docs.google.com/document/d/{SPEARS_TYRE_DOC_ID}/edit'

@dataclass
class Wheel_Effect:
    bias: str
    slip_angle: str
    anti_roll: str
    note: str


class Wheel:
    def __init__(
        self, 
        wheel_type: str = None,
        name: str = None, 
        wheel_effects: str = None,  # processed into list
        suggested_state: str = None,  # processed into thumbsup emoji, thumbsdown emoji, shrug emoji
        price: str = None,
    ) -> None:
        """
        :param wheel_type: Type of wheel, High End, Offroad, ...
        :param name: Name of the wheel
        :param effects: Wheel effects
        :param suggested_state: Suggested state of the wheel, thumbsup emoji, thumbsdown emoji, shrug emoji
        :param price: Price of the wheel
        """
        
        self.wheel_type = wheel_type
        self.name = name

        if type(wheel_effects) is str:
            self.wheel_effects = self.process_effects(wheel_effects)

        else:  # should be a dict if not a str
            self.wheel_effects = Wheel_Effect(**wheel_effects)

        if suggested_state not in [Support.THUMBSDOWN, Support.THUMBSUP, Support.SHRUG]:
            self.suggested_state = self.process_suggestion(suggested_state)

        else:
            self.suggested_state = suggested_state

        self.price = price
        self.price = price


    def process_effects(self, effects: str) -> list:
        """
        :param effects: List of effects
        :return: List of effects
        """

        effects = effects.lower()
        bias = ''
        anti_roll = ''
        slip_angle = ''
        note = ''
        
        if 'traction' in effects:  # traction bias

            if 'rear' in effects:
                bias = 'rear'

            elif any(b in effects for b in ['front', 'forward']):
                bias = 'front'

            else:
                bias = 'neutral'

        if 'roll' in effects:  # anti roll

            # he only put 'anti-roll' after any 'traction bias' stuff, so this is assuption here is only a - or + after anti-roll
            # ignoring times when he used hyphen insted of minus sign ...
            if '-' in effects.split('roll')[-1]:
                anti_roll = '-'

            else:
                anti_roll = '+'

        if 'angle' in effects:  # slip angle

            # for slip angle he didn't always use a - or +, sometimes it was just blank... we ignore those, but other than that we use same logic as anti-roll
            if '-' in effects.split('angle')[-1]:
                slip_angle = '-'

            else:
                slip_angle = '+'

        if '(' in effects:  # notes
            note = effects.split('(')[-1].split(')')[0].strip()

        return Wheel_Effect(bias, slip_angle, anti_roll, note)


    def process_suggestion(self, suggested_state_hex) -> str:
        if suggested_state_hex == '00ff00':  # green
            return Support.THUMBSUP
    
        if suggested_state_hex == 'ff9900':  # orange
            return Support.SHRUG

        if suggested_state_hex == 'ff0000':  # red
            return Support.THUMBSDOWN


async def on_reaction_add(
        msg: discord.Message,
        emoji: str,
        user: discord.User,
        client: discord.Client,
        embed_meta: str = ""
) -> None:
    embed_type = embed_meta.split('type=')[1].split('/')[0]

    if embed_type == 'wheel':
        pass

    elif embed_type == 'wheel_search':

        if emoji in embed_meta:
            wheel_name = embed_meta.split(
                f"{emoji}=")[1].split('/')[0].replace('%20', ' ').replace('%21', '/'
            )
            wheel = get_wheels()[wheel_name]
            try:
                await msg.clear_reactions()
            except discord.Forbidden:
                pass
            await send_wheel(msg, client, wheel)


def get_wheels() -> dict[str, Wheel]:
    wheels = json.load(open("wheels.json", "r"))
    for wheel_name in wheels:
        wheels[wheel_name] = Wheel(**wheels[wheel_name])

    return wheels


def update_wheels():
    """
    :return: None, Saves to wheels.json
    """

    ''' SUPPORT FUNCTIONS '''

    def download_file_from_google_drive(id, destination):
        URL = "https://docs.google.com/uc?export=download"

        session = requests.Session()

        response = session.get(URL, params = { 'id' : id }, stream = True)
        token = get_confirm_token(response)

        if token:
            params = { 'id' : id, 'confirm' : token }
            response = session.get(URL, params = params, stream = True)

        save_response_content(response, destination)  
    # end download_file_from_google_drive  

    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value

        return None
    # end get_confirm_token

    def save_response_content(response, destination):
        CHUNK_SIZE = 32768

        with open(destination, "wb") as f:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
    # end save_response_content


    ''' START OF FUNCTION '''


    destination = 'tyre_doc.docx'
    download_file_from_google_drive(SPEARS_TYRE_DOC_ID, destination)

    tyre_doc = docx.Document('tyre_doc.docx')

    wheels = {}

    for table in tyre_doc.tables:
        wheel_type = table.rows[0].cells[0].text.strip()

        for row in table.rows:
            color = None
            name = None
            wheel_effects = None
            price = None

            for i, cell in enumerate(row.cells):

                if i == 0:  # Name
                    pattern = re.compile('w:fill=\"(\S*)\"')
                    match = pattern.search(cell._tc.xml)
                    if match:
                        color = match.group(1)

                    name = cell.text.strip()

                elif i == 1:  # Effects
                    wheel_effects = cell.text.strip()

                elif i == 2:  # Price
                    price = cell.text.strip()

            wheel = Wheel(
                wheel_type=wheel_type,
                name=name,
                wheel_effects=wheel_effects,
                suggested_state=color,
                price=price
            )

            if wheel.suggested_state:
                wheels[f"{name} ({wheel_type})"] = wheel

    json.dump(
        wheels, 
        open('wheels.json', 'w'), 
        indent=4, 
        default=lambda o: o.__dict__
    )


async def send_possible_wheels(
    msg: discord.Message, 
    client: discord.Client, 
    possible_wheels: list[Wheel], 
    wheel_name: str
) -> None:

    if len(possible_wheels) == 1:  # send wheel
        await send_wheel(msg, client, possible_wheels[0])

    else:  # create list of possible wheels
        letters = list(Support.LETTERS_EMOJIS.keys())
        possible_wheels_str = ""
        embed_meta = f"embed_meta/type=wheel_search/"

        for i, wheel in enumerate(possible_wheels):
            possible_wheels_str += f"\n{Support.LETTERS_EMOJIS[letters[i]]} " \
                                   f"{wheel.name} ({wheel.wheel_type})"

            meta_wheel_name = f"{wheel.name.replace(' ', '%20')}%20({wheel.wheel_type})"
            embed_meta += f"{Support.LETTERS_EMOJIS[letters[i]]}={meta_wheel_name}/"

        if not possible_wheels_str:
            possible_wheels_str = "\n\nThere were no close matches for your search." \
                                  "It can only be suggested you use more letters in your query."


        embed = discord.Embed(
            color=discord.Color(Support.GTALENS_ORANGE),
            title=f"Search: **{wheel_name}***",
            description=f"[Spear's Tyre Doc]({SPEARS_TYRE_DOC_LINK}) **|** "
                        f"[Donate]({Support.DONATE_LINK})"
                        f"\n\n**Results:**"
                        f"{possible_wheels_str}"
                        f"[{Support.ZERO_WIDTH}]({embed_meta})"
        )

        embed.set_footer(text="More wheel commands: .lens wheel help")

        await msg.edit(embed=embed)

        for i, j in enumerate(possible_wheels):
            await msg.add_reaction(Support.LETTERS_EMOJIS[letters[i]])

    return msg


async def send_wheel(
    message: discord.Message, client: discord.Client, wheel: Wheel
) -> None:
    """
    :param msg: 
    :param client: 
    :param wheel: Wheel to send
    :return: None
    """

    # https://gta.fandom.com/wiki/Los_Santos_Customs/Wheels
    # embed.set_thumbnail(url=wheel.suggested_state)

    embed_meta = f"[{Support.ZERO_WIDTH}](embed_meta/" \
                 f"type=wheel/" \
                 f"name={wheel.name.replace(' ', '%20')}/" \
                 f")"
    
    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f"**{wheel.name} ({wheel.wheel_type})**",
        description=f"\n[GTALens](https://gtalens.com/) **|** "
                    f"[Spear's Tyre Doc]({SPEARS_TYRE_DOC_LINK}) **|** "
                    f"[Donate]({Support.DONATE_LINK})\n\n"
    )  # initial embed

    embed.description += f"**Price:** {wheel.price}\n"

    # effects
    embed.description += f"**Traction Bias:** "
    if wheel.wheel_effects.bias:
        embed.description += f"{wheel.wheel_effects.bias}%\n"

    else:
        embed.description += "- \n"

    embed.description += f"**Anti-Roll:** "
    if wheel.wheel_effects.anti_roll:
        embed.description += f"{wheel.wheel_effects.anti_roll}\n"

    else:
        embed.description += "- \n"
        
    embed.description += f"**Slip Angle:** "
    if wheel.wheel_effects.slip_angle:
        embed.description += f"{wheel.wheel_effects.slip_angle}\n"

    else:
        embed.description += "- \n"

    embed.description += f"**Suggested:** {wheel.suggested_state}"

    # note
    if wheel.wheel_effects.note:
        embed.description += f"\n\n**Note:** {wheel.wheel_effects.note}"

    embed.description += embed_meta

    embed.set_footer(text="All information regarding wheels and their effects is retrieved from Spear's Tyre Document linked above.")

    msg = message
    if message.author.id not in Support.CLIENT_IDS.values():
        msg = await msg.channel.send(embed=embed)

    else:
        await msg.edit(embed=embed)

    logger.info(f"Sent Wheel: {wheel.name}")

    return msg


async def send_wheel_type(msg: discord.Message, wheels: list[Wheel]):
    """
    :param msg: 
    :param client: 
    :param wheel: Wheel to send
    :return: None
    """

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f"**{wheels[0].wheel_type} ({len(wheels)})**",
        description=f"\n[GTALens](https://gtalens.com/) **|** "
                    f"[Spear's Tyre Doc]({SPEARS_TYRE_DOC_LINK}) **|** "
                    f"[Donate]({Support.DONATE_LINK})"
    )  # initial embed

    suggested_states = [
        Support.THUMBSUP,
        Support.SHRUG,
        Support.THUMBSDOWN
    ]
    
    for wheel in wheels:
        wheel.suggested_state = suggested_states.index(wheel.suggested_state)

    wheels.sort(key=lambda wheel: wheel.suggested_state)

    value = f"\n\n{suggested_states[0]}\n"
    for i, wheel in enumerate(wheels):

        # extra line between suggested stats
        if i:
            if wheel.suggested_state != wheels[i-1].suggested_state:
                value += f"\n{suggested_states[wheel.suggested_state]}\n"

        value += f"**{wheel.name}** "

        if wheel.wheel_effects.bias:
            value += f"| Traction Bias: {wheel.wheel_effects.bias} "
        
        if wheel.wheel_effects.anti_roll:
            value += f"| Anti-roll: {wheel.wheel_effects.anti_roll} "

        if wheel.wheel_effects.slip_angle:
            value += f"| Slip Angle: {wheel.wheel_effects.slip_angle} "

        value += "\n"

    embed.description += value

    embed.set_footer(text="All information regarding wheels and their effects is retrieved from Spear's Tyre Document linked above.")

    await msg.edit(embed=embed)

    logger.info(f"Sent Wheel Type: {wheels[0].wheel_type}")

    return msg


async def send_wheel_effects(
    msg: discord.Message, wheels: list[Wheel], args: list[str]
):
    args = [a.lower() for a in args]

    # get the effects specified in args
    effects = {}

    if 'type' in args:
        effects['type'] = args.index('type')

    for effect, e in WHEEL_EFFECTS_CORRECTIONS.items():
        if e in args:
            effects[effect] = args.index(e)

    effects = zip(effects.keys(), effects.values())
    effects = sorted(effects, key=lambda e: e[1])
    effects = dict(effects)

    await msg.channel.send(effects)

    effect_keys = list(effects.keys())
    for i, effect in enumerate(effect_keys):
        start = effects[effect] + 1
        stop = effects[effect_keys[i+1]] if i < len(effect_keys) - 1 else len(args) - 1
        effects[effect] = " ".join(args[start:stop])

    # get the title
    title = []
        
    for effect in effects:
        title.append(
            f"{effect.capitalize()}: {effects[effect]}"
        )

    title = '\n'.join(title)

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title=f"**{title}**",
        description=f"\n[GTALens](https://gtalens.com/) **|** "
                    f"[Spear's Tyre Doc]({SPEARS_TYRE_DOC_LINK}) **|** "
                    f"[Donate]({Support.DONATE_LINK})\n"
    ) # initial embed

    # check for invalid args
    description = ""
    for effect in effect_keys:
        if effect == "Type":
            wheel_type_names = list(WHEEL_TYPE_CORRECTIONS.keys())
            possible_wheel_type_names = Support.get_possible(
                effects[effect],
                wheel_type_names,
                objects=False
            )

            if not possible_wheel_type_names:
                description += f"**Invalid wheel type** - use `offroad, tuner, sports, etc`\n"
                del effects[effect]

        elif effect == "Traction Bias":
            if effects[effect] not in ['front', 'rear']:
                description += f"**Invalid traction bias** - use `front or rear`\n"
                del effects[effect]

        elif effect in ["Anti-roll", "Slip Angle"]:
            if effects[effect] not in ['+', '-']:
                description += f"**Invalid {effect.lower()}** - use `+ or -`\n"
                del effects[effect]

    if description:
        description += "\n"

    # find wheels with the specified effects
    wheels_found = []
    for wheel in wheels:
        use_wheel = True
        for effect in effects:
            if effect == "Type":
                if wheel.wheel_type != WHEEL_EFFECTS_CORRECTIONS[possible_wheel_type_names[0]]:
                    use_wheel = False
            
            if effect == "Traction Bias":
                if wheel.wheel_effects.bias != effects[effect]:
                    use_wheel = False

            if effect == "Anti-roll":
                if wheel.wheel_effects.anti_roll != effects[effect]:
                    use_wheel = False

            if effect == "Slip Angle":
                if wheel.wheel_effects.slip_angle != effects[effect]:
                    use_wheel = False

        if use_wheel:
            wheels_found.append(wheel)

    suggested_states = [
        Support.THUMBSUP,
        Support.SHRUG,
        Support.THUMBSDOWN
    ]

    for wheel in wheels_found:
        wheel.suggested_state = suggested_states.index(wheel.suggested_state)

    wheels_found.sort(key=lambda wheel: wheel.suggested_state)
    
    description += f"**__Wheels Found__ ({len(wheels_found)})**\n"
    for i, wheel in enumerate(wheels_found):
            
            # extra line between suggested stats
            if i:
                if wheel.suggested_state != wheels_found[i-1].suggested_state:
                    description += f"\n"
    
            wheel_type = f" ({wheel.wheel_type}) " if "Type" not in effects else ""

            description += f"{wheel.name}{wheel_type} {suggested_states[wheel.suggested_state]}\n"

    embed.description = description

    await msg.edit(embed=embed)


async def send_help(message: discord.Message) -> None:

    embed = discord.Embed(
        colour=discord.Colour(Support.GTALENS_ORANGE),
        title="**Wheels Help**",
        description=f"[GTALens](https://gtalens.com/) **|** " \
                    f"[Spear's Tyre Doc]({SPEARS_TYRE_DOC_LINK}) **|** " \
                    f"[Donate]({Support.DONATE_LINK})\n\n" \
                    "All information regarding wheels and their effects is retrieved from Spear's Tyre Document linked above.\n⠀"
    )

    # .lens wheel NAME
    value = ""
    value += "Searches the wheel, then returns wheel effects, price, and if it's suggested by Spear\n"
    value += f"`.lens wheel NAME`\n"
    value += f"`.lens wheel Azreals`\n"
    value += Support.SPACE_CHAR
    embed.add_field(
        name="**__Specific Wheel Search__**",
        value=value,
        inline=False
    )

    # .lens wheel TYPE
    value = ""
    value += "Returns all wheels of a specific type (e.g. all offroad wheels)\n"
    value += f"`.lens wheel type TYPE`\n"
    value += f"`.lens wheel type offroad`\n"
    value += Support.SPACE_CHAR
    embed.add_field(
        name="**__Wheel Type Search__**",
        value=value,
        inline=False
    )

    # .lens wheel TYPE EFFECTS
    value = ""
    value += "Returns all wheels with specific effects (e.g. all wheels with specific traction bias, and/or anti-roll, and/or slip angle)\n"
    value += f"`.lens wheel type TYPE bias BIAS ar AR slip SLIP`\n"
    value += f"`.lens wheel type offroad bias front`\n"
    value += f"`.lens wheel bias back ar +`\n"
    value += f"`.lens wheel bias front slip -`\n"
    value += f"`.lens wheel ar - slip +`\n"
    value += "Not all parameters are required.\n"
    # value += Support.SPACE_CHAR
    embed.add_field(
        name="**__Wheel Effect Search__**",
        value=value,
        inline=False
    )

    await message.channel.send(embed=embed)

# update_wheels()