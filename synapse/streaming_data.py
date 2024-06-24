import zmq
import random
from generated.api.node_pb2 import NodeSocket, NodeType, DataType


def create_zmq_output_socket():
    ctx = zmq.Context.instance()
    socket = ctx.socket(zmq.PUB)
    socket.bind_to_random_port(
        "tcp://127.0.0.1", min_port=64401, max_port=64799, max_tries=100
    )
    return ctx, socket


def create_zmq_input_socket():
    ctx = zmq.Context.instance()
    socket = ctx.socket(zmq.SUB)
    socket.bind_to_random_port(
        "tcp://127.0.0.1", min_port=64401, max_port=64799, max_tries=100
    )
    socket.RCVTIMEO = 1000
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    return ctx, socket


def create_node_socket(node):
    if node.type == NodeType.kStreamIn:
        ctx, sock = create_zmq_input_socket()
    elif node.type == NodeType.kStreamOut:
        ctx, sock = create_zmq_output_socket()
    return (
        ctx,
        sock,
        NodeSocket(
            node_id=node.id,
            data_type=DataType.kAny,
            bind=sock.getsockopt(zmq.LAST_ENDPOINT).decode("ascii"),
            type=node.type,
        ),
    )


def send_fake_data_async(stop_event, socket):
    print("Starting to send data...")
    while not stop_event.is_set():
        datum = random.randint(0, 100).to_bytes(4, byteorder="big")
        try:
            socket.send(datum)
        except zmq.ZMQError as e:
            print(f"Error sending data: {e}")
    print("Stopped sending data")


def recv_data_async(stop_event, socket, handler):
    print("Starting to receive data...")
    while not stop_event.is_set():
        try:
            data = socket.recv()
            handler(data)
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                continue
            print(f"Error receiving data: {e}")
    print("Stopped receiving data")
