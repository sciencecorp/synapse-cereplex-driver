import grpc
import threading

from threading import Thread
from synapse.streaming_data import (
    send_fake_data_async,
    recv_data_async,
    create_node_socket,
)
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


class SynapseServicer(SynapseDeviceServicer):
    """Provides methods that implement functionality of route guide server."""

    sockets = []
    threads = []
    state = DeviceState.kInitializing
    configuration = None
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
        self._sockets_tear_down()
        for node in configuration.nodes:
            if node.type in [NodeType.kStreamIn, NodeType.kStreamOut]:
                self.sockets.append(create_node_socket(node))
        self.configuration = configuration
        return True

    def _start_streaming(self):
        print("Starting streaming...")
        self.stop_event = threading.Event()
        for socket in self.sockets:
            if socket[2].type == NodeType.kStreamIn:
                t = Thread(
                    target=recv_data_async, args=(self.stop_event, socket[1], print)
                )
            else:
                t = Thread(
                    target=send_fake_data_async,
                    args=(
                        self.stop_event,
                        socket[1],
                    ),
                )
            t.start()
            self.threads.append(t)
        self.state = DeviceState.kRunning
        return True

    def _stop_streaming(self):
        if self.stop_event is None:
            return False
        print("Stopping streaming...")
        self.stop_event.set()
        for t in self.threads:
            t.join()
        self.threads = []
        self.state = DeviceState.kStopped
        return True

    def _sockets_tear_down(self):
        self.state = DeviceState.kInitializing
        for socket in self.sockets:
            socket[1].close()
            socket[0].term()
        self.sockets = []

    def _sockets_status_info(self):
        return [x[2] for x in self.sockets]
