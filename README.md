# Simple Synapse device

Intended primarily for development and testing, could potentially be extended for use cases like Blackrock or Intan drivers.

To build:

    git submodule init
    git submodule update
    pip install -r requirements.txt

On Unix machines:

    make

On Windows machines:

    python compile_protos.py

Then:

    python -m build

To run:

    python -m synapse.server.main