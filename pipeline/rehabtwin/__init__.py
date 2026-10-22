"""rehabtwin — the video -> SKEL -> OpenSim slice of the Rehab Agent pipeline.

Every stage reads and writes files (docs/architecture.md): a marker/SKEL
sequence (.npz), OpenSim inputs/outputs (.trc/.osim/.mot/.sto) and JSON
records (session.json, qc.json, validation-report.json).
"""
__version__ = "0.1.0"
