import zmq
from typing import Any
from generated.api.node_pb2 import NodeSocket, DataType


class BaseNode(object):
    def __init__(self, id, type, server) -> None:
        self.id = id
        self.server = server
        self.socket = None
        self.zmq_context = None

    def start(self):
        pass

    def stop(self):
        pass

    def node_socket(self):
        if self.socket is None:
            return False
        return (
            self.zmq_context,
            self.socket,
            NodeSocket(
                node_id=self.id,
                data_type=DataType.kAny,
                bind=self.socket.getsockopt(zmq.LAST_ENDPOINT).decode("ascii"),
                type=self.type,
            ),
        )
