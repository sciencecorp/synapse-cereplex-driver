import logging
import queue
import socket
import struct
import threading
from synapse.server.nodes import BaseNode
from synapse.generated.api.node_pb2 import NodeType
from synapse.generated.api.nodes.stream_out_pb2 import StreamOutConfig

PORT = 6480
MULTICAST_TTL = 3


class StreamOut(BaseNode):
    def __init__(self, id, config=StreamOutConfig()):
        super().__init__(id, NodeType.kStreamOut)
        self.__stop_event = threading.Event()
        self.__data_queue = queue.Queue()
        self.__multicast_group = None
        self.socket = PORT

        self.reconfigure(config)

    def config(self):
        c = super().config()
        o = StreamOutConfig()
        if self.__multicast_group:
            o.multicast_group = self.__multicast_group
        c.stream_out.CopyFrom(o)
        return c

    def reconfigure(self, config: StreamOutConfig):
        self.__socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )

        multicast_group = config.multicast_group
        if multicast_group:
            self.__multicast_group = multicast_group
            self.__socket.setsockopt(
                socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL
            )
            self.__socket.bind(("", 0))
            addr, port = self.__socket.getsockname()

            host = socket.gethostbyname(socket.gethostname())
            mreq = socket.inet_aton(addr) + socket.inet_aton(host)
            mreq = struct.pack("4sL", socket.inet_aton(addr), socket.INADDR_ANY)
            self.__socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            logging.info(
                f"StreamOut (node {self.id}): created multicast socket with group {multicast_group}"
            )

        else:
            host = socket.gethostbyname(socket.gethostname())
            logging.info(
                f"StreamOut (node {self.id}): created unicast socket on {host}:{self.socket}"
            )

    def start(self):
        logging.info("StreamOut (node %d): starting..." % self.id)

        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()

        logging.info("StreamOut (node %d): started" % self.id)

    def stop(self):
        logging.info("StreamOut (node %d): stopping..." % self.id)
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return

        self.__stop_event.set()
        self.thread.join()
        self.__socket.close()
        self.__socket = None
        logging.info("StreamOut (node %d): stopped" % self.id)

    def on_data_received(self, data):
        self.__data_queue.put(data)

    def run(self):
        logging.info("StreamOut (node %d): starting to send data..." % self.id)
        while not self.__stop_event.is_set():
            try:
                data = self.__data_queue.get(True, 1)
            except queue.Empty:
                continue
            try:
                addr = self.__multicast_group if self.__multicast_group else ""
                self.__socket.sendto(data, (addr, PORT))
            except Exception as e:
                logging.error(f"Error sending data: {e}")
