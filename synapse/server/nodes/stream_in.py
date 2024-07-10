import logging
import select
import socket
import struct
import threading
from synapse.generated.api.node_pb2 import NodeType
from synapse.generated.api.nodes.stream_in_pb2 import StreamInConfig
from synapse.server.nodes import BaseNode

class StreamIn(BaseNode):
    def __init__(self, id, config = StreamInConfig()):
        super().__init__(id, NodeType.kStreamIn)
        self.__socket = None
        self.__stop_event = threading.Event()
        self.__multicast_group = None

        self.reconfigure(config)

    def config(self):
        c = super().config()
        
        i = StreamInConfig()
        if self.__multicast_group:
            i.multicast_group = self.__multicast_group

        c.stream_in.CopyFrom(i)
        return c

    def reconfigure(self, config: StreamInConfig = StreamInConfig()):
        host = socket.gethostbyname(socket.gethostname())

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)


        multicast_group = config.multicast_group
        if multicast_group:
            addr = multicast_group
            self.__socket.bind((addr, 0))
            port = self.__socket.getsockname()[1]

            host = socket.gethostbyname(socket.gethostname())
            mreq = socket.inet_aton(addr) + socket.inet_aton(host)
            mreq = struct.pack("4sL", socket.inet_aton(addr), socket.INADDR_ANY)
            self.__socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            self.__multicast_group = multicast_group
            self.socket = port
            logging.info(f"StreamIn (node {self.id}): - joined multicast group {addr}:{port}")

        else:
            self.__socket.bind(("", 0))
            self.socket = self.__socket.getsockname()[1]
            logging.info(f"StreamIn (node {self.id}): - listening on {self.socket}")
        

    def start(self):
        logging.info("StreamIn (node %d): starting..." % self.id)
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()
        logging.info("StreamIn (node %d): started" % self.id)

    def stop(self):
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return
        logging.info("StreamIn (node %d): stopping..." % self.id)
        self.__stop_event.set()
        self.thread.join()
        self.__socket.close()
        self.__socket = None
        logging.info("StreamIn (node %d): stopped" % self.id)

    def run(self):
        logging.info("StreamIn (node %d): starting to receive data..." % self.id)
        while not self.__stop_event.is_set():
            try:
                ready = select.select([self.__socket], [], [], 1)
                if ready[0]:
                    data, _ = self.__socket.recvfrom(1024)
                    
                    self.emit_data(data)
                    pass
            except Exception as e:
                logging.error(f"Error receiving data: {e}")
    
        logging.info("StreamIn (node %d): exited thread" % self.id)
