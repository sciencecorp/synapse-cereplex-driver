import logging
import socket
import struct
import threading
from synapse.server.nodes import BaseNode
from synapse.generated.api.node_pb2 import NodeType

MULTICAST_ADDR = "239.0.0.115"
MULTICAST_PORT = 6473
from synapse.generated.api.nodes.stream_in_pb2 import StreamInConfig

class StreamIn(BaseNode):
    def __init__(self, id, config = StreamInConfig()):
        super().__init__(id, NodeType.kStreamIn)
        self.__socket = None
        self.__stop_event = threading.Event()
        self.__group = MULTICAST_ADDR
        self.__port = MULTICAST_PORT
        self.bind = f"{self.__group}:{self.__port}"

    def start(self):
        if self.__socket is None:
            self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

            self.__socket.bind((self.__group, self.__port))

            host = socket.gethostbyname(socket.gethostname())
            mreq = socket.inet_aton(self.__group) + socket.inet_aton(host)

            mreq = struct.pack("4sL", socket.inet_aton(self.__group), socket.INADDR_ANY)
            self.__socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        self.__thread = threading.Thread(target=self.run, args=())
        self.__thread.start()
        logging.info("StreamIn (node %d): started" % self.id)

    def stop(self):
        if not hasattr(self, "__thread") or not self.__thread.is_alive():
            return
        logging.info("StreamIn (node %d): stopping..." % self.id)
        self.__stop_event.set()
        self.__thread.join()
        self.__socket.close()
        self.__socket = None
        logging.info("StreamIn (node %d): stopped" % self.id)

    def run(self):
        logging.info("StreamIn (node %d): starting to receive data..." % self.id)
        while not self.__stop_event.is_set():
            try:
                data, _ = self.__socket.recvfrom(1024)
                self.emit_data(data)
                pass
            except Exception as e:
                logging.error(f"Error receiving data: {e}")
    
        logging.info("StreamIn (node %d): exited thread" % self.id)
