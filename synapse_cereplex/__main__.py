from synapse.server.entrypoint import main
from synapse.server.nodes import SERVER_NODE_OBJECT_MAP
from synapse_cereplex.electrical_broadband import (
    ElectricalBroadband,
    PERIPHERALS as ElectricalBroadbandPeripherals,
)
from synapse.api.node_pb2 import NodeType


def run():
    main(
        SERVER_NODE_OBJECT_MAP
        | {
            NodeType.kElectricalBroadband: ElectricalBroadband,
        },
        ElectricalBroadbandPeripherals,
    )


if __name__ == "__main__":
    run()
