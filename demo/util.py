from json import dumps, loads
from urllib.parse import quote, urlunsplit

from debatrix.core.common import DebateInfo


def format_info(debate_info: DebateInfo, *, with_info_slide: bool = True) -> list[str]:
    sections: list[str] = [
        f"Motion: {debate_info.motion}",
        f"Pro: {', '.join(debater_info.name for debater_info in debate_info.pro_side)}",
        f"Con: {', '.join(debater_info.name for debater_info in debate_info.con_side)}",
    ]

    if with_info_slide:
        sections.append(f"Info slide:\n{debate_info.info_slide}")

    return sections


def get_avatar_url(name: str) -> str:
    return urlunsplit(("https", "robohash.org", quote(f"/{name}"), "set=set4", ""))


def prettify_json(raw: str) -> str:
    try:
        raw = dumps(loads(raw.strip()), indent=2)
        return f"```\n{raw}\n```"
    except Exception:
        return raw
