from enum import Enum
import threading

from cerebus import cbpy

from synapse.api.node_pb2 import NodeOptions, NodeType
from synapse.api.nodes.electrical_broadband_pb2 import (
    ElectricalBroadbandConfig,
    ElectricalBroadbandOptions,
)
from synapse.api.datatype_pb2 import DataType
from synapse.api.synapse_pb2 import Peripheral
from synapse.server.nodes import BaseNode
from synapse.server.status import Status, StatusCode


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

PERIPHERALS = [
    Peripheral(
        name="Hub 1",
        vendor="Blackrock Neurotech",
        peripheral_id=1,
        type=Peripheral.Type.kElectricalRecord,
        options=NodeOptions(
            type=NodeType.kElectricalBroadband,
            id=1,
            electrical_broadband=ElectricalBroadbandOptions(
                ch_count=192,
                bit_width=[16, 64],  # Signed 16 bit  # Double
                sample_rate=[500, 1000, 2000, 10000, 30000],
                gain=[],
            ),
        ),
    )
]


class ElectricalBroadband(BaseNode):
    def __init__(self, id):
        super().__init__(id, NodeType.kElectricalBroadband)
        self.stop_event = threading.Event()

        res, con_info = cbpy.open(parameter=cbpy.defaultConParams())

        if res == 0:
            self.logger.info("Cerebus connection opened", con_info)

    def __del__(self):
        self.logger.info("closing cerebus connection...")
        cbpy.close()
        self.logger.info("cerebus connection closed")

    def start(self) -> Status:
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()
        self.logger.info("started")

        return Status()

    def stop(self) -> Status:
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return
        self.logger.info("stopping...")
        self.stop_event.set()
        self.thread.join()
        self.logger.info("stopped")

        return Status()

    def run(self):
        while not self.stop_event.is_set():
            try:
                try:
                    # data is a list of [channel_id, np.array(samples, dtype=int16)] tuples
                    # t0 is the timestamp at sample 0
                    res, data, t0 = cbpy.trial_continuous(reset=True)
                except Exception as e:
                    self.logger.error(f"Exception in cbpy.trial_continuous: {e}")
                    continue

                if res != 0:
                    self.logger.warn(f"failed to read data: code {res}")
                    continue

                if len(data) < 1:
                    continue

                if self.emit_data:
                    self.emit_data((DataType.kBroadband, t0, data))
            except Exception as e:
                self.logger.warn(f"failed to read data: {e}")

    def configure(self, config: ElectricalBroadbandConfig, iface_ip) -> Status:
        self.logger.info(
            f"Configuring ElectricalBroadband node with configuration {config}"
        )
        id = config.peripheral_id
        if not id:
            return Status(
                code=StatusCode.kUndefinedError, message="must provide peripheral_id"
            )

        ps = [p for p in PERIPHERALS if p.peripheral_id == id]
        if len(ps) < 1:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"must provide valid peripheral_id: must be {[p.peripheral_id for p in PERIPHERALS]}",
            )

        peripheral = ps[0]
        peripheral_options = peripheral.options.electrical_broadband

        # Validate sample rate
        sample_rate = config.sample_rate
        if sample_rate not in peripheral_options.sample_rate:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"invalid sample rate: must be one of {peripheral_options.sample_rate}",
            )

        sample_group = CONFIG_MAP_SAMPLE_RATE[sample_rate]

        # Validate bit width
        bit_width = config.bit_width
        if bit_width not in peripheral_options.bit_width:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"invalid bit width: must be one of {peripheral_options.bit_width}",
            )

        # Validate gain
        gain = config.gain
        if gain and gain not in peripheral_options.gain:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"invalid gain: must be one of {peripheral_options.gain}",
            )

        # Validate Channels
        ch_map = {}
        ch_count = peripheral_options.ch_count
        for ch in config.channels:
            ch_id = ch.id
            if ch_id >= ch_count:
                return Status(
                    code=StatusCode.kUndefinedError,
                    message=f"invalid channel id={ch_id}: must be less than {ch_count}",
                )
            ch_map[ch_id] = ch

        # Configure channels (on / off, sample group / rate)
        for c in range(ch_count):
            ch_sample_group = SampleGroup.NONE

            if c in ch_map:
                ch_sample_group = sample_group

            status = self._configure_channel(peripheral, c, ch_sample_group)
            if not status.ok():
                return status

        # Configure system (bit depth)
        res, reset = cbpy.trial_config(
            reset=True,
            buffer_parameter={
                "absolute_time": True,
                "continuous_length": 30000,
                "event_length": 0,
                "double": bit_width == 64,
            },
            noevent=1,
            nocontinuous=0,
            nocomment=1,
        )

        if res != 0:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"failed to configure system: code {res}",
            )

        return Status(code=StatusCode.kOk, message="Configuration successful")

    def _configure_channel(
        self, peripheral: Peripheral, ch: int, sample_group: SampleGroup
    ) -> Status:
        # Synapse channels are 0 indexed
        # Blackrock channels are 1 indexed
        blackrock_ch_index = ch + 1
        res = None
        info = None

        self.logger.debug(
            f"configuring channel {ch} (blackrock i: {blackrock_ch_index}) with group {sample_group}"
        )
        try:
            res, info = cbpy.get_channel_config(blackrock_ch_index)

            if res != 0:
                return Status(
                    code=StatusCode.kUndefinedError,
                    message=f"failed to get config for channel {ch}: code {res}",
                )

            info["smpgroup"] = sample_group.value

        except RuntimeError as e:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"failed to get config for channel {ch}: {e}",
            )

        try:
            res = cbpy.set_channel_config(blackrock_ch_index, info)

        except RuntimeError as e:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"failed to set config for channel {ch}: {e}",
            )

        self.logger.debug(f" - configured channel {ch}")

        return Status(code=StatusCode.kOk, message="Channel configuration successful")
