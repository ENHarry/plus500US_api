"""Auto-add this directory to sys.path so generated protobuf imports resolve.

Generated pb2 files use absolute imports like ``from t4.v1.common import ...``
which requires the directory containing ``t4/`` (i.e. this directory) to be on
sys.path.
"""
import sys
from pathlib import Path

_proto_root = str(Path(__file__).parent)
if _proto_root not in sys.path:
    sys.path.insert(0, _proto_root)
