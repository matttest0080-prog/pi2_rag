# Lightweight RAG on Raspberry Pi 2

This repository provides a retrieval baseline designed for Raspberry Pi 2-class hardware. It deliberately avoids local embedding models, FAISS, Chroma, and other heavyweight vector stacks.

## Design

The baseline uses two standard-library tools:

- `tools/rag_build.py` scans verified Markdown knowledge and creates `.rag/index.json`.
- `tools/rag_query.py` searches the index with BM25-style lexical ranking.

Indexed sources currently include:

- `skills/raspberry-pi-hardware-control/references/*.md`
- `README.md`
- `docs/ARCHITECTURE.md`

Generated `.rag/` data is local runtime state and should not be committed.

## Build the index

From the repository root:

```bash
python3 tools/rag_build.py
```

The command creates:

```text
.rag/index.json
```

No third-party Python package is required.

## Query examples

```bash
python3 tools/rag_query.py "PCA9685 servo external power"
python3 tools/rag_query.py "VL53L0X distance changes servo"
python3 tools/rag_query.py "GY-9250 tilt channel 1"
python3 tools/rag_query.py "CSI camera YOLO tiny"
```

Machine-readable output for an agent:

```bash
python3 tools/rag_query.py --json --top-k 3 "PCA9685 I2C address"
```

## Hermes Agent IoT integration

A Hermes Agent / Hermes Agent IoT workflow can treat `rag_query.py --json` as a retrieval command:

```text
user request
    -> identify hardware keywords
    -> run rag_query.py --json
    -> read the top verified chunks
    -> verify device and power state
    -> select the relevant hardware-control skill/script
    -> execute only after safety checks
```

The retrieval result is evidence, not permission to actuate hardware. Servo, motor, relay, or other physical commands remain side effects and must follow the safety rules in the skill and architecture documentation.

## Why lexical retrieval first

For the current repository size, lexical retrieval is preferable on Raspberry Pi 2 because it has:

- no model download;
- no model inference RAM cost;
- no native vector-library build requirement;
- deterministic offline operation;
- a small generated index;
- easy JSON integration with an external agent.

## Future remote embedding mode

If semantic retrieval becomes necessary, keep the Pi2 as the edge client and move embeddings/vector search to a stronger host. The local CLI contract can remain similar: a query enters, ranked source chunks return, and Hermes uses those chunks as grounded context.
