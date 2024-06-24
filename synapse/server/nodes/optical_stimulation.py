from synapse.server.nodes import BaseNode
from synapse.generated.api.node_pb2 import NodeType


class OpticalStimulation(BaseNode):

    def __init__(self, id):
        super().__init__(id, NodeType.kOpticalStim)

    def start(self):
        pass

    def stop(self):
        pass

    def on_data_received(self):
        pass
