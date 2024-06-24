# Simple Synapse device

Intended primarily for development and testing, could potentially be extended for use cases like Blackrock or Intan drivers.

To build:

    git submodule init
    git submodule update
    pip install -r requirements.txt
    make
    python -m build

To run:

    python -m synapse.server.main