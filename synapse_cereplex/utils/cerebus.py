from enum import Enum

from cerebus import cbpy
from synapse.api.synapse_pb2 import Peripheral


class SampleGroup(Enum):
    NONE = 0
    SR500Hz = 1
    SR1000Hz = 2
    SR2000Hz = 3
    SR10000Hz = 4
    SR30000Hz = 5


CONFIG_MAP_SAMPLE_RATE = {
    500: SampleGroup.SR500Hz,
    1000: SampleGroup.SR1000Hz,
    2000: SampleGroup.SR2000Hz,
    10000: SampleGroup.SR10000Hz,
    30000: SampleGroup.SR30000Hz,
}
BIT_WIDTHS = [16, 64]
SAMPLE_RATES = [500, 1000, 2000, 10000, 30000]
CHANNEL_COUNT = 192
PERIPHERALS = [
    Peripheral(
        name=f"Hub",
        vendor="Blackrock Neurotech",
        peripheral_id=1,
        type=Peripheral.Type.kBroadbandSource,
    )
]


class CerebusConnection:
    """Singleton class to manage Cerebus connection."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not CerebusConnection._initialized:
            res, con_info = cbpy.open(parameter=cbpy.defaultConParams())
            if res == 0:
                print("Cerebus connection opened", con_info)
            CerebusConnection._initialized = True

    def __del__(self):
        if CerebusConnection._initialized:
            print("closing cerebus connection...")
            cbpy.close()
            print("cerebus connection closed")
            CerebusConnection._initialized = False
