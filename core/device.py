"""Detects the best available compute device.
Phase 1: informational only (the brain runs in the cloud).
Phase 5: local ML models will use this to pick GPU automatically."""


def get_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return f"GPU ({torch.cuda.get_device_name(0)})"
    except ImportError:
        pass
    return "CPU"