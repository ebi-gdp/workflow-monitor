from enum import Enum, auto


class PlatformNameSpace(Enum):
    DEV = auto()
    TEST = auto()
    PROD = auto()

    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return PlatformNameSpace[s.upper()]
        except KeyError:
            return s
