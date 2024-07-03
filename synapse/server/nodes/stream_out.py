import logging
import queue
import socket
import threading
from synapse.server.nodes import BaseNode
from synapse.generated.api.node_pb2 import NodeType

MULTICAST_ADDR = "239.0.0.115"
MULTICAST_PORT = 6472
MULTICAST_TTL = 3

class StreamOut(BaseNode):
    def __init__(self, id):
        super().__init__(id, NodeType.kStreamOut)
        # TODO(antoniae): accept configuration
        self.__addr = MULTICAST_ADDR
        # TODO(antoniae): pick random port?
        self.__port = MULTICAST_PORT
        self.stop_event = threading.Event()
        self.data_queue = queue.Queue()
        self.bind = f"{self.__addr}:{self.__port}"

    def start(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.__socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)

        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()

    def stop(self):
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return
        self.stop_event.set()
        self.thread.join()
        self.__socket.close()
        self.__socket = None

    def on_data_received(self, data):
        self.data_queue.put(data)

    def run(self):
        while not self.stop_event.is_set():
            try:
                data = self.data_queue.get(True, 1)
            except queue.Empty:
                continue
            try:
                self.__socket.sendto(data, (self.__addr, self.__port))
            except Exception as e:
                logging.error(f"Error sending data: {e}")
