import typing


class _UNSET:
    __instance: typing.Self | None = None

    def __new__(cls: type[typing.Self]) -> typing.Self:
        if cls.__instance is None:
            ret = super().__new__(cls)
            cls.__instance = ret
            return ret
        return cls.__instance

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET = _UNSET()
