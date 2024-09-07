import queue
import logging
import threading
from synapse.server.nodes import BaseNode
from synapse.generated.api.node_pb2 import NodeType
from synapse.generated.api.nodes.optical_stim_pb2 import OpticalStimConfig


class OpticalStimulation(BaseNode):
    def __init__(self, id):
        super().__init__(id, NodeType.kOpticalStim)
        self.stop_event = threading.Event()
        self.data_queue = queue.Queue()

    def start(self):
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()
        self.logger.info("started" % self.id)

    def stop(self):
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return
        self.logger.info("stopping..." % self.id)
        self.stop_event.set()
        self.thread.join()
        self.logger.info("stopped" % self.id)

    def on_data_received(self, data):
        self.data_queue.put(data)

    def run(self):
        self.logger.info(
            "Starting to receive data..." % self.id
        )
        while not self.stop_event.is_set():
            try:
                data = self.data_queue.get(True, 1)
            except queue.Empty:
                continue
            # write to the device somehow, but here, just log it
            value = int.from_bytes(data, byteorder="big")
            self.logger.info("received data: %i" % (self.id, value))

        self.logger.info("exited thread" % self.id)
