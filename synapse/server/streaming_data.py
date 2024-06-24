from threading import Thread
import zmq
import random
from synapse.server.nodes import BaseNode
from generated.api.node_pb2 import NodeType


class StreamOut(BaseNode):

    def __init__(self, id, server):
        super().__init__(id, NodeType.kStreamOut, server)
        self.ctx = zmq.Context.instance()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind_to_random_port(
            "tcp://127.0.0.1", min_port=64401, max_port=64799, max_tries=100
        )

    def start(self):
        self.thread = Thread(target=self.run, args=())
        self.thread.start()

    def stop(self):
        self.thread.join()
        self.socket.close()
        self.ctx.term()

    def on_data_received(self):
        pass

    def run(self):
        print("Starting to send data...")
        while not self.server.stop_event.is_set():
            datum = random.randint(0, 100).to_bytes(4, byteorder="big")
            try:
                self.socket.send(datum)
            except zmq.ZMQError as e:
                print(f"Error sending data: {e}")
        print("Stopped sending data")


class StreamIn(BaseNode):

    def __init__(self, id, server):
        super().__init__(id, NodeType.kStreamIn, server)
        self.ctx = zmq.Context.instance()
        self.socket = self.ctx.socket(zmq.SUB)
        self.socket.bind_to_random_port(
            "tcp://127.0.0.1", min_port=64401, max_port=64799, max_tries=100
        )
        self.socket.RCVTIMEO = 1000
        self.socket.setsockopt(zmq.SUBSCRIBE, b"")
        self.socket.setsockopt(zmq.LINGER, 0)

    def start(self):
        self.thread = Thread(target=self.run, args=())
        self.thread.start()

    def stop(self):
        self.thread.join()
        self.socket.close()
        self.ctx.term()

    def on_data_received(self):
        pass

    def run(self):
        while not self.server.stop_event.is_set():
            try:
                data = self.socket.recv()
                self.on_data_received(data)
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue
                print(f"Error receiving data: {e}")
        print("StreamIn (node %d) stopped" % self.id)
