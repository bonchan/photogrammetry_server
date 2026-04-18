from typing import Any, Dict
from .base import MetashapeTaskBase

class DummyTask(MetashapeTaskBase):
    def run(self, params: Dict[str, Any]) -> bool:
        # 1. Get the callback the worker sent us
        progress_cb = params.get("progress_cb")
        
        self.log("Starting dummy work...")
        
        # 2. Use the callback directly (Metashape style)
        if progress_cb:
            progress_cb(50.0) # Tell the UI we are 50% done
            
        return True