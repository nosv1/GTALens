from datetime import datetime
import gspread
import re

# COLORS

GTALENS_ORANGE = int(0xF03C00)

# IDS
GTALENS_GUILD_ID = 873054419636334633

# CHARACTERS
ZERO_WIDTH = chr(8203)  # or the thing in bewteen the dashes -​-
SPACE_CHAR = "⠀"
HEAVY_CHECKMARK = "✔"
BALLOT_CHECKMARK = "☑️"
WRENCH = "🔧"
FLAG_ON_POST = "🚩"

# GSPREAD


def get_g_client() -> gspread.Client:
    gc = gspread.service_account(filename="Secrets/phyner-a9859c6daae5.json")
    return gc


def get_args_from_content(content: str = "") -> (list[str], str):
    content = re.sub(r"[“”]", '"', content)
    content = re.sub(r"[\n\t\r]", " ", content)
    content += " "
    while "  " in content:
        content = content.replace("  ", " ")

    args = content.split(
        " "
    )  # should always have at least element given addition of extra " " above

    return args, content


def num_suffix(num: int) -> str:
    """
    :param num: ex. 2
    :return: ex. 2nd
    """

    return f"{num}{'th' if 11 <= num <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(num % 10, 'th')}"


def smart_day_time_format(date_format: str, dt: datetime) -> str:
    """
    :param date_format: day in format should be {S}
    :param dt: datetime
    :return: formatted time as String
    """

    return dt.strftime(date_format).replace("{S}", f"{num_suffix(dt.day)}")


# end time_format_with_smart_date
