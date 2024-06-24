import queue
import logging
import threading
from synapse.server.nodes import BaseNode
from synapse.generated.api.node_pb2 import NodeType


class OpticalStimulation(BaseNode):

    def __init__(self, id):
        super().__init__(id, NodeType.kOpticalStim)
        self.stop_event = threading.Event()
        self.data_queue = queue.Queue()

    def start(self):
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()
        logging.info("OpticalStimulatuon (node %d): started" % self.id)

    def stop(self):
        if not hasattr(self, "thread") or not self.thread.is_alive():
            return
        logging.info("OpticalStimulatuon (node %d): stopping..." % self.id)
        self.stop_event.set()
        self.thread.join()
        logging.info("OpticalStimulatuon (node %d): stopped" % self.id)

    def on_data_received(self, data):
        self.data_queue.put(data)

    def run(self):
        logging.info(
            "OpticalStimulation (node %d): Starting to receive data..." % self.id
        )
        while not self.stop_event.is_set():
            try:
                data = self.data_queue.get(True, 1)
            except queue.Empty:
                continue
            # write to output device as appropriate
        logging.info("OpticalStimulation (node %d): exited thread" % self.id)
