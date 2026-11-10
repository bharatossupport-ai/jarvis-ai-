"""Downloads the models that ship INSIDE the app (run once before building).
models/
  Hermes-3-Llama-3.2-3B.Q4_K_M.gguf   (~2.0 GB, built-in AI)
  whisper-base/                        (~145 MB, speech recognition, Hindi + English)
  piper/hi_IN-pratham-medium.onnx      (Hindi voice)
  piper/en_US-lessac-medium.onnx       (English voice)
"""
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download

M = Path(__file__).resolve().parent.parent / "models"
(M / "piper").mkdir(parents=True, exist_ok=True)

hf_hub_download("NousResearch/Hermes-3-Llama-3.2-3B-GGUF", "Hermes-3-Llama-3.2-3B.Q4_K_M.gguf", local_dir=M)
snapshot_download("Systran/faster-whisper-base", local_dir=M / "whisper-base")
for f in ["hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx", "hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json",
          "en/en_US/lessac/medium/en_US-lessac-medium.onnx", "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"]:
    p = hf_hub_download("rhasspy/piper-voices", f, local_dir=M / "_piper")
    target = M / "piper" / Path(f).name
    if not target.exists():
        Path(p).replace(target)
for junk in [M / "_piper", M / ".cache", M / "whisper-base" / ".cache"]:
    import shutil
    shutil.rmtree(junk, ignore_errors=True)
print("Models ready in", M)
