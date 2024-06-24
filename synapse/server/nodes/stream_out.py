import threading
import zmq
import random
import logging
from threading import Thread
from synapse.server.nodes import BaseNode
from synapse.generated.api.node_pb2 import NodeType


class StreamOut(BaseNode):

    def __init__(self, id):
        super().__init__(id, NodeType.kStreamOut)
        self.stop_event = threading.Event()

    def start(self):
        ctx = zmq.Context.instance()
        self.socket = ctx.socket(zmq.PUB)
        self.socket.bind_to_random_port(
            "tcp://127.0.0.1", min_port=64401, max_port=64799, max_tries=100
        )

        self.thread = Thread(target=self.run, args=())
        self.thread.start()
        logging.info("StreamOut (node %d): started" % self.id)

    def stop(self):
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return
        logging.info("StreamOut (node %d): stopping..." % self.id)
        self.stop_event.set()
        self.thread.join()
        self.socket.close()
        self.socket = None
        logging.info("StreamOut (node %d): stopped" % self.id)

    def on_data_received(self):
        pass

    def run(self):
        logging.info("StreamOut (node %d): Starting to send data..." % self.id)
        while not self.stop_event.is_set():
            datum = random.randint(0, 100).to_bytes(4, byteorder="big")
            try:
                self.socket.send(datum)
            except zmq.ZMQError as e:
                logging.error(f"Error sending data: {e}")
        logging.info("StreamOut (node %d): exited thread" % self.id)
