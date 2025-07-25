from enum import Enum, auto

class Register(Enum):
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5
    R6 = 6
    R7 = 7
    R8 = 8
    R9 = 9
    R10 = 10
    R11 = 11
    R12 = 12
    BP = 13  # Base Pointer
    SP = 14  # Stack Pointer
    RA = 15  # Return Address

    @classmethod
    def parse_str(cls, name: str) -> 'Register | None':
        try:
            return cls[name.upper()]
        except KeyError:
            return None

    def __str__(self) -> str:
        return self.name

