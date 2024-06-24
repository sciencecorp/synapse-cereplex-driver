import grpc
import threading

from threading import Thread
from synapse.server.streaming_data import StreamIn, StreamOut
from generated.api.synapse_pb2 import Status, StatusCode, DeviceInfo, DeviceState
from generated.api.node_pb2 import NodeType
from generated.api.synapse_pb2_grpc import (
    SynapseDeviceServicer,
    add_SynapseDeviceServicer_to_server,
)


async def serve(server_name, device_serial, rpc_port) -> None:
    server = grpc.aio.server()
    add_SynapseDeviceServicer_to_server(
        SynapseServicer(server_name, device_serial), server
    )
    server.add_insecure_port("[::]:%d" % rpc_port)
    await server.start()
    await server.wait_for_termination()


NODE_TYPE_OBJECT_MAP = {
    NodeType.kStreamIn: StreamIn,
    NodeType.kStreamOut: StreamOut,
}


class SynapseServicer(SynapseDeviceServicer):
    """Provides methods that implement functionality of route guide server."""

    state = DeviceState.kInitializing
    configuration = None
    nodes = []
    stop_event = None

    def __init__(self, name, serial):
        self.name = name
        self.serial = serial

    def Info(self, request, context):
        return DeviceInfo(
            name=self.name,
            serial=self.serial,
            synapse_version=10,
            firmware_version=1,
            status=Status(
                message=None,
                code=StatusCode.kOk,
                sockets=self._sockets_status_info(),
                state=self.state,
            ),
            peripherals=[],
            configuration=self.configuration,
        )

    def Configure(self, request, context):
        if not self._reconfigure(request):
            return Status(
                message="Failed to configure",
                code=StatusCode.kUndefinedError,
                sockets=self._sockets_status_info(),
                state=self.state,
            )

        return Status(
            message=None,
            code=StatusCode.kOk,
            sockets=self._sockets_status_info(),
            state=self.state,
        )

    def Start(self, request, context):
        if not self._start_streaming():
            return Status(
                message="Failed to start streaming",
                code=StatusCode.kUndefinedError,
                sockets=self._sockets_status_info(),
                state=self.state,
            )
        return Status(
            message=None,
            code=StatusCode.kOk,
            sockets=self._sockets_status_info(),
            state=self.state,
        )

    def Stop(self, request, context):
        if not self._stop_streaming():
            return Status(
                message="Failed to stop streaming",
                code=StatusCode.kUndefinedError,
                sockets=self._sockets_status_info(),
                state=self.state,
            )
        return Status(
            message=None,
            code=StatusCode.kOk,
            sockets=self._sockets_status_info(),
            state=self.state,
        )

    def _reconfigure(self, configuration):
        self.state = DeviceState.kInitializing

        for node in self.nodes:
            node.stop()

        for node in configuration.nodes:
            if node.type not in list(NODE_TYPE_OBJECT_MAP.keys()):
                return False
            node = NODE_TYPE_OBJECT_MAP[node.type](node.id, self)
            self.nodes.append(node)
        self.configuration = configuration
        return True

    def _start_streaming(self):
        print("Starting streaming...")
        self.stop_event = threading.Event()
        for node in self.nodes:
            node.start()
        self.state = DeviceState.kRunning
        return True

    def _stop_streaming(self):
        if self.stop_event is None:
            return False
        print("Stopping streaming...")
        self.stop_event.set()
        for node in self.nodes:
            node.stop()
        self.state = DeviceState.kStopped
        return True

    def _sockets_status_info(self):
        return [node.node_socket() for node in self.nodes]
