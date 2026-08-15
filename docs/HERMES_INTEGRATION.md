# Hermes Agent IoT Retrieval Integration

This document defines a minimal integration contract between `pi2_rag` and Hermes Agent / Hermes Agent IoT.

## Principle

`pi2_rag` is the evidence source. Hermes Agent is the planner/orchestrator. Hardware scripts are side-effecting tools and must not be selected solely because retrieval returned a matching document.

## Retrieval command

Build the local lexical index after cloning or after knowledge files change:

```bash
cd ~/pi2_rag
python3 tools/rag_build.py
```

Query it from Hermes or another agent process:

```bash
python3 tools/rag_query.py --json --top-k 3 "VL53L0X servo distance change"
```

The command returns a JSON array with this shape:

```json
[
  {
    "score": 3.42,
    "path": "skills/raspberry-pi-hardware-control/references/vl53l0x-distance-servo-rag.md",
    "chunk": 2,
    "title": "...",
    "text": "..."
  }
]
```

## Recommended agent flow

```text
1. Parse the user's hardware intent.
2. Query pi2_rag with non-destructive descriptive keywords.
3. Read the top 3-5 evidence chunks.
4. Identify the exact board/device/channel involved.
5. Verify current hardware state and power requirements.
6. Select a documented script/template only if the evidence supports it.
7. Run a conservative test before a sustained behavior.
8. Observe sensor/actuator results and report failures explicitly.
```

## Suggested Hermes tool wrapper

A Hermes-side wrapper can execute the retrieval CLI without importing this repository as a Python package:

```python
import json
import subprocess


def query_pi2_rag(query: str, repo="/home/pi2/pi2_rag", top_k=3):
    cmd = [
        "python3",
        f"{repo}/tools/rag_query.py",
        "--index",
        f"{repo}/.rag/index.json",
        "--json",
        "--top-k",
        str(top_k),
        query,
    ]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)
```

The wrapper is intentionally retrieval-only. It does not execute servo or sensor scripts.

## Index refresh policy

Rebuild the index when any of these change:

- `README.md`
- `docs/ARCHITECTURE.md`
- files under `skills/raspberry-pi-hardware-control/references/`

For this repository size, rebuilding on demand is simpler than running a background indexing daemon.

## Failure behavior

The agent should not invent hardware facts when retrieval returns no result. It should either:

- ask for the missing board/device details;
- inspect the hardware using a safe diagnostic command; or
- state that the repository does not yet contain verified evidence for the requested operation.

## Future semantic mode

A future remote service can replace lexical scoring with embeddings while preserving the same logical contract: query text in, ranked source chunks out. This keeps Raspberry Pi 2 as a lightweight edge client and avoids forcing embedding inference onto 1 GB-class hardware.
