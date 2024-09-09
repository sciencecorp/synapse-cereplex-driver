import queue
import socket
import struct
import threading
from typing import List, Tuple
from synapse.server.nodes import BaseNode
from synapse.server.status import Status
from synapse.generated.api.status_pb2 import StatusCode
from synapse.generated.api.datatype_pb2 import DataType
from synapse.generated.api.node_pb2 import NodeType
from synapse.generated.api.nodes.stream_out_pb2 import StreamOutConfig

PORT = 6480
MULTICAST_TTL = 3


class StreamOut(BaseNode):
    __n = 0

    def __init__(self, id):
        super().__init__(id, NodeType.kStreamOut)
        self.__i = StreamOut.__n
        StreamOut.__n += 1
        self.__stop_event = threading.Event()
        self.__data_queue = queue.Queue()

    def config(self):
        c = super().config()

        o = StreamOutConfig()

        o.multicast_group = self.multicastGroup
        o.use_multicast = True

        c.stream_out.CopyFrom(o)
        return c

    def configure(self, config: StreamOutConfig, iface_ip) -> Status:
        if not config.multicast_group:
            return Status(StatusCode.kUndefinedError, "No multicast group specified")

        self.__socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )

        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        port = PORT + self.__i

        self.__socket.bind((iface_ip, port))

        self.multicastGroup = config.multicast_group
        mreq = struct.pack("=4sl", socket.inet_aton(self.multicastGroup), socket.INADDR_ANY)
        self.__socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        self.__socket.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL
        )

        self.socket = [self.multicastGroup, port]

        self.logger.info(
            f"created multicast socket on {self.socket}, group {self.multicastGroup}"
        )
        return Status()

    def start(self) -> Status:
        self.logger.info("starting...")

        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()

        self.logger.info("started")

        return Status()

    def stop(self) -> Status:
        self.logger.info("stopping...")
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return

        self.__stop_event.set()
        self.thread.join()
        self.__socket.close()
        self.__socket = None
        self.logger.info("stopped")

        return Status()

    def on_data_received(self, data):
        self.__data_queue.put(data)

    def run(self):
        self.logger.info("starting to send data...")
        while not self.__stop_event.is_set():
            if not self.socket:
                self.logger.error("socket not configured")
                return
            try:
                data = self.__data_queue.get(True, 1)
            except queue.Empty:
                self.logger.warning("queue is empty")
                continue

            if data[0] == DataType.kBroadband:
                # detect data type arriving at you (should be packaged in `data` above)
                # encode it appropriately for NDTP
                data_type, t0, samples = data
                encoded_data = self.serialize_broadband_data(t0, samples)
            else:
                self.logger.error(f"Unsupported data type, dropping: {data[0]}")
                continue

            try:
                self.__socket.sendto(encoded_data, (self.socket[0], self.socket[1]))
                if not self.socket:
                    self.socket = self.__socket.getsockname()

            except Exception as e:
                self.logger.error(f"Error sending data: {e}")

    def serialize_broadband_data(self, t0, data: List[Tuple[int, List[int]]]) -> bytes:
        if len(data) == 0:
            return bytes()

        result = bytearray()
        result.extend(struct.pack("ciqchh", b"0", DataType.kBroadband, t0, b"0", len(data), len(data[0])))

        # for ch_packet in data:
        #     c = ch_packet[0] - 1
        #     ch_data = ch_packet[1:]
        #     result.extend(struct.pack("l", c))

        #     for value in ch_data:
        #         result.extend(struct.pack("l", value))

        return bytes(result)
