from coolname import generate_slug
from synapse.server.entrypoint import main, ENTRY_DEFAULTS
from synapse.server.nodes import SERVER_NODE_OBJECT_MAP
from synapse_cereplex.electrical_broadband import (
    ElectricalBroadband,
    PERIPHERALS as ElectricalBroadbandPeripherals,
)
from synapse.api.node_pb2 import NodeType

defaults = ENTRY_DEFAULTS.copy()
defaults["device_serial"] = "BLACKROCK-CPLX-001"
defaults["server_name"] = "blackrock-" + generate_slug(2)


def run():
    main(
        SERVER_NODE_OBJECT_MAP
        | {
            NodeType.kElectricalBroadband: ElectricalBroadband,
        },
        ElectricalBroadbandPeripherals,
        defaults,
    )


if __name__ == "__main__":
    run()
