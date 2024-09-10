import logging

logging.basicConfig(level=logging.DEBUG)

from synapse.server.entrypoint import main
from synapse.server.nodes import SERVER_NODE_OBJECT_MAP
from synapse_cereplex.electrical_broadband import (
    ElectricalBroadband,
    PERIPHERALS as ElectricalBroadbandPeripherals,
)
from synapse.api.node_pb2 import NodeType

if __name__ == "__main__":
    main(
        SERVER_NODE_OBJECT_MAP.extend(
            {
                NodeType.kElectricalBroadband: ElectricalBroadband,
            }
        ),
        [ElectricalBroadbandPeripherals],
    )
