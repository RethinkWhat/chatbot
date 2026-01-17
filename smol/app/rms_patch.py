# app/rms_patch.py

import torch.nn as nn

# Only define RMSNorm if missing
if not hasattr(nn, "RMSNorm"):
    try:
        from transformers.models.llama.modeling_llama import LlamaRMSNorm
        nn.RMSNorm = LlamaRMSNorm
    except ImportError as e:
        raise ImportError("RMSNorm patch failed. Use transformers >= 4.31.0") from e
