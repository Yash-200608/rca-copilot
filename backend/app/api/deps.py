from dataclasses import dataclass

from fastapi import Header


@dataclass
class Actor:
    name: str
    role: str  # 'investigator' | 'qa'  (DEMO ONLY - taken from a header, there is no real authentication)


def get_actor(x_demo_user: str = Header(default="Investigator (demo)"), x_demo_role: str = Header(default="investigator")) -> Actor:
    return Actor(name=x_demo_user[:80], role="qa" if x_demo_role.lower() == "qa" else "investigator")
