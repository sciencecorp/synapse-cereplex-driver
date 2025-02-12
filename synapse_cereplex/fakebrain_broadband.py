import asyncio
import time
import math
import numpy as np
import pygame
from scipy.special import i0

from enum import Enum

from synapse.api.node_pb2 import NodeType
from synapse.api.nodes.electrical_broadband_pb2 import ElectricalBroadbandConfig
from synapse.api.synapse_pb2 import Peripheral
from synapse.server.nodes import BaseNode
from synapse.server.status import Status, StatusCode
from synapse.utils.ndtp_types import ElectricalBroadbandData


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
        name="FakeBrain",
        vendor="FakeVendor",
        peripheral_id=1,
        type=Peripheral.Type.kElectricalRecord,
    )
]

CHANNEL_COUNT = 96
BIT_WIDTHS = [16, 64]
SAMPLE_RATES = [500, 1000, 2000, 10000, 30000]


class FakeBrainBroadband(BaseNode):
    def __init__(self, id):
        super().__init__(id, NodeType.kElectricalBroadband)
        self.sample_rate = 0
        self.bit_width = 0
        self.__config = None

        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            self.logger.error("No joystick detected")
            raise Exception("No joystick detected")
        else:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.logger.info(f"Joystick initialized: {self.joystick.get_name()}")

        # Generate sorted preferred angles for channels
        self.preferred_angles = sorted(np.random.uniform(0, 2 * math.pi, CHANNEL_COUNT))

    def __del__(self):
        self.logger.info("Closing joystick...")
        self.joystick.quit()
        pygame.joystick.quit()
        pygame.quit()
        self.logger.info("Joystick closed")

    def get_data(self):
        try:
            # Process all pygame events
            pygame.event.pump()

            # Get joystick axes (assuming axes 0 and 1 for x and y)
            x = self.joystick.get_axis(0)
            y = self.joystick.get_axis(1)

            # Log the joystick input for debugging
            self.logger.debug(f"Joystick input - x: {x}, y: {y}")

            # Convert to angle and magnitude
            # y-axis is typically inverted in joystick
            angle = math.atan2(-y, x)  # returns value between -π and π
            if angle < 0:
                angle += 2 * math.pi  # Normalize angle to [0, 2π]
            magnitude = math.hypot(x, y)  # magnitude from 0 to sqrt(2)

            # Log the angle and magnitude for debugging
            self.logger.debug(f"Computed angle: {angle}, magnitude: {magnitude}")

            # Simulate data for each channel
            channels = range(1, CHANNEL_COUNT + 1)

            # Number of samples per channel
            time_window = 0.01  # 10 ms time window
            samples_per_channel = int(self.sample_rate * time_window)

            data = []

            # Generate variability across channels
            baseline_rates = np.random.uniform(
                5, 15, CHANNEL_COUNT
            )  # Baseline rates in Hz
            max_rates = np.random.uniform(50, 100, CHANNEL_COUNT)  # Max rates in Hz
            kappas = np.random.uniform(1, 5, CHANNEL_COUNT)  # Tuning sharpness

            for idx, (ch_id, pref_angle) in enumerate(
                zip(channels, self.preferred_angles)
            ):
                angle_diff = abs(angle - pref_angle)
                angle_diff = min(
                    angle_diff, 2 * math.pi - angle_diff
                )  # Shortest angle difference

                # Von Mises tuning curve
                kappa = kappas[idx]
                tuning_curve = math.exp(kappa * math.cos(angle_diff)) / (
                    2 * math.pi * i0(kappa)
                )  # Using imported i0

                # Compute firing rate
                baseline_rate = baseline_rates[idx]
                max_rate = max_rates[idx]
                firing_rate = (
                    baseline_rate
                    + (max_rate - baseline_rate) * tuning_curve * magnitude
                )

                # Expected number of spikes in the time window
                expected_spikes = firing_rate * time_window

                # Generate Poisson spike counts
                spike_counts = np.random.poisson(expected_spikes)

                # Generate broadband signal
                signal = np.random.normal(0, 50, samples_per_channel).astype(
                    np.int16
                )  # Background noise

                # Simulate spikes as high-amplitude events
                if spike_counts > 0:
                    spike_times = np.random.choice(
                        samples_per_channel, size=spike_counts, replace=False
                    )
                    signal[spike_times] += np.random.randint(
                        500, 1000, size=spike_counts
                    ).astype(np.int16)

                data.append([ch_id, signal])

            # t0 is current time in microseconds
            t0 = int(time.time() * 1e6)

            return data, t0

        except Exception as e:
            self.logger.error(f"Exception in get_data: {e}")
            return None, None

    async def run(self):
        while self.running:
            try:
                data, t0 = await asyncio.to_thread(self.get_data)

                if data:
                    await self.emit_data(
                        ElectricalBroadbandData(
                            sample_rate=self.sample_rate,
                            t0=t0,
                            samples=data,
                            bit_width=self.bit_width,
                        )
                    )
                await asyncio.sleep(0.01)  # Slightly longer sleep to process events

            except Exception as e:
                self.logger.warn(f"Failed to read data: {e}")

    def config(self):
        c = super().config()
        if self.__config:
            c.electrical_broadband.CopyFrom(self.__config)
        return c

    def configure(self, config: ElectricalBroadbandConfig) -> Status:
        self.logger.info(
            f"Configuring FakeBrainBroadband node with configuration {config}"
        )
        id = config.peripheral_id
        if not id:
            return Status(
                code=StatusCode.kUndefinedError, message="Must provide peripheral_id"
            )

        ps = [p for p in PERIPHERALS if p.peripheral_id == id]
        if len(ps) < 1:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"Must provide valid peripheral_id: must be {[p.peripheral_id for p in PERIPHERALS]}",
            )

        peripheral = ps[0]

        # Validate sample rate
        self.sample_rate = config.sample_rate
        if self.sample_rate not in SAMPLE_RATES:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"Invalid sample rate: must be one of {SAMPLE_RATES}",
            )

        # Validate bit width
        self.bit_width = config.bit_width
        if self.bit_width not in BIT_WIDTHS:
            return Status(
                code=StatusCode.kUndefinedError,
                message=f"Invalid bit width: must be one of {BIT_WIDTHS}",
            )

        # Validate Channels
        ch_map = {}
        for ch in config.channels:
            ch_id = ch.id

            if ch_id == 0:
                return Status(
                    code=StatusCode.kUndefinedError,
                    message=f"Invalid channel id={ch_id}: channels do not support zero-indexing",
                )
            elif ch_id > CHANNEL_COUNT:
                return Status(
                    code=StatusCode.kUndefinedError,
                    message=f"Invalid channel id={ch_id}: must be within [1, {CHANNEL_COUNT}]",
                )
            ch_map[ch_id] = ch

        # Configure active channels
        self.active_channels = ch_map.keys()

        self.__config = config

        return Status(code=StatusCode.kOk, message="Configuration successful")
