import os, sys, tempfile
from pathlib import Path
_tmp = tempfile.mkdtemp()
os.environ["APPDATA"] = _tmp
os.environ["XDG_DATA_HOME"] = _tmp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
