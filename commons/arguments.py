import typing
from enum import Enum

ARGUMENTS_PATTERN = r"\s-{1,2}[a-zA-Z0-9][a-zA-Z0-9_-]*"


class ArgumentRole(Enum):
    FLAG = 0
    STDIN_ENABLER = 1
    FILE_ENABLER = 2
    STRING_ENABLER = 3

    def __str__(self) -> str:
        return self.name


class ArgumentsPair:
    first: str
    second: str
    valid_roles: typing.List[ArgumentRole]

    def __init__(self) -> None:
        self.first = None
        self.second = None
        self.valid_roles = []

    def to_str(self) -> str:
        if not self.first:
            return ""
        elif not self.second:
            return self.first
        else:
            return f"{self.first} {self.second}"

    def to_hex_id(self) -> str:
        if not self.first:
            return "none"

        return self.to_str().encode("utf-8").hex().upper()
