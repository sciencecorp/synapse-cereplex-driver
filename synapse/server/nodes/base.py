from synapse.generated.api.node_pb2 import NodeConfig, NodeSocket, DataType

class BaseNode(object):
    def __init__(self, id, type) -> None:
        self.id = id
        self.type = type
        self.bind = None

    def config(self):
        return NodeConfig(
            id=self.id,
            type=self.type,
        )

    def start(self):
        pass

    def stop(self):
        pass

    def on_data_received(self):
        pass

    def emit_data(self, data):
        pass

    def node_socket(self):
        if self.bind is None:
            return False
        return NodeSocket(
            node_id=self.id,
            data_type=DataType.kAny,
            bind=self.bind,
            type=self.type,
        )
