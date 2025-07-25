# Import all macros to make them easily discoverable
from .push import Push
from .pop import Pop
from .inc import Inc
from .dec import Dec
from .call import Call
from .ret import Ret
from .enter import Enter
from .leave import Leave
from .scall import SCall
from .enter_isr import EnterISR
from .leave_isr import LeaveISR

# List of macro classes for the parser to use
ALL_MACROS = [
    Inc(), Dec(), Push(), Pop(), SCall(), Ret(), Call(), Enter(), Leave(), EnterISR(), LeaveISR()
]

