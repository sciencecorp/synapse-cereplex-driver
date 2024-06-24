import zmq
import logging
import threading
from synapse.server.nodes import BaseNode
from synapse.generated.api.node_pb2 import NodeType


class StreamIn(BaseNode):

    def __init__(self, id):
        super().__init__(id, NodeType.kStreamIn)
        self.stop_event = threading.Event()

    def start(self):
        ctx = zmq.Context.instance()
        self.socket = ctx.socket(zmq.SUB)
        self.socket.bind_to_random_port(
            "tcp://127.0.0.1", min_port=64401, max_port=64799, max_tries=100
        )
        self.socket.RCVTIMEO = 1000
        self.socket.setsockopt(zmq.SUBSCRIBE, b"")
        self.socket.setsockopt(zmq.LINGER, 0)

        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()
        logging.info("StreamIn (node %d): started" % self.id)

    def stop(self):
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return
        logging.info("StreamIn (node %d): stopping..." % self.id)
        self.stop_event.set()
        self.thread.join()
        self.socket.close()
        self.socket = None
        logging.info("StreamIn (node %d): stopped" % self.id)

    def on_data_received(self):
        pass

    def run(self):
        logging.info("StreamOut (node %d): Starting to receive data..." % self.id)
        while not self.stop_event.is_set():
            try:
                data = self.socket.recv()
                self.on_data_received(data)
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue
                logging.error(f"Error receiving data: {e}")
        logging.info("StreamIn (node %d): exited thread" % self.id)
