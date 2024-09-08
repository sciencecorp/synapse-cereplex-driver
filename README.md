# Blackrock (CerePlex) Synapse Devie

To build:

    git submodule update --init
    pip install -r requirements.txt

On Unix machines:

    make

On Windows machines:

    python compile_protos.py

Then:

    python -m build

To run:

    python -m synapse.server.main
