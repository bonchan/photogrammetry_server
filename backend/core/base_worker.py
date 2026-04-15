import signal
import sys
import time
from database import update_job_status

class BaseWorker:
    def __init__(self, job_id: int):
        self.job_id = job_id
        self.interrupted = False
        
        # Timing state
        self.start_time = None
        self.step_start_time = None
        
        # Register system signals
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        self.interrupted = True
        self.on_shutdown()
        update_job_status(self.job_id, status="FAILED", step="INTERRUPTED")
        sys.exit(0)

    def on_shutdown(self):
        """Override in child (e.g., MetashapeWorker) to save .psx"""
        pass

    def start_step_timer(self):
        """Call this at the beginning of every major Metashape task."""
        self.step_start_time = time.time()

    def calculate_eta(self, progress: float):
        """
        Calculates ETA based on the current step's start time.
        Returns a formatted string 'MM:SS' or '--:--'
        """
        if not self.step_start_time or progress <= 5:
            return "--:--"
            
        elapsed = time.time() - self.step_start_time
        # (Elapsed / Progress%) = Total Estimated Time
        total_est = elapsed / (progress / 100)
        remaining = max(0, total_est - elapsed)
        
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def update_progress(self, step: str, progress: float):
        """Standardized DB update with automatic ETA."""
        if self.interrupted:
            raise Exception("Worker Interrupted")

        eta_str = self.calculate_eta(progress)
        
        # We store the ETA in the 'step_info' column
        update_job_status(
            self.job_id, 
            step=step, 
            progress=progress,
            step_info=f"ETA: {eta_str}"
        )

    def run(self):
        raise NotImplementedError()