from coolname import generate_slug
from synapse.api.node_pb2 import NodeType
from synapse.server.entrypoint import main, ENTRY_DEFAULTS
from synapse.server.nodes import SERVER_NODE_OBJECT_MAP
from synapse_cereplex.broadband_source import BroadbandSource
from synapse_cereplex.utils.cerebus import PERIPHERALS

defaults = ENTRY_DEFAULTS.copy()
defaults["device_serial"] = "BLACKROCK-CPLX-001"
defaults["server_name"] = "blackrock-" + generate_slug(2)

nodes = SERVER_NODE_OBJECT_MAP.copy()
nodes[NodeType.kBroadbandSource] = BroadbandSource


def run():
    main(nodes, PERIPHERALS, defaults)


if __name__ == "__main__":
    run()
