"""
Cycle Statistics Module

Tracks and persists cycle statistics including:
- Operation counts (per session and total)
- Cycle times (last, averages, by job)
- Yield rates (pass/fail ratios)

Stats are stored in persistent application data so they survive app updates.
"""

import json
import os
import sys
import time
from pathlib import Path
from collections import deque
from datetime import datetime
from typing import Optional, Dict, Any

# psutil is optional - graceful fallback if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[STATS] psutil not available - host uptime will not be shown")


def _get_stats_file():
    """Determine a writable path for the stats file."""
    fallback_dir = Path.home() / '.br-equipment-control-app'

    try:
        if sys.platform == 'win32':
            base_dir = Path(os.environ.get('APPDATA', fallback_dir))
            config_dir = base_dir / 'BR Equipment Control'
        elif sys.platform == 'darwin':
            config_dir = Path.home() / 'Library' / 'Application Support' / 'BR Equipment Control'
        else:
            base_dir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
            config_dir = base_dir / 'br-equipment-control-app'
    except Exception as e:
        print(f"Warning determining stats directory: {e}")
        config_dir = fallback_dir

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning creating stats directory at {config_dir}: {e}")
        config_dir = fallback_dir
        config_dir.mkdir(parents=True, exist_ok=True)

    return config_dir / 'cycle_stats.json'


STATS_FILE = _get_stats_file()


class CycleStats:
    """
    Manages cycle statistics with persistence.
    
    Tracks:
    - Operations since boot (session)
    - Operations total (persistent)
    - Last cycle time
    - Cycle times for averages (stored as rolling window)
    - Pass/Fail counts for yield calculation
    """
    
    # Rolling window sizes
    WINDOW_100 = 100
    WINDOW_1000 = 1000
    
    def __init__(self):
        self._stats = self._load_stats()
        self._session_start_time = time.time()
        self._session_operations = 0
        self._current_job = None
        self._last_job = self._stats.get('last_job', None)  # Track last completed job
        
        # In-memory rolling windows for cycle times (don't persist all of these)
        self._recent_100_times = deque(maxlen=self.WINDOW_100)
        self._recent_1000_times = deque(maxlen=self.WINDOW_1000)
        self._recent_100_results = deque(maxlen=self.WINDOW_100)  # True=pass, False=fail
        self._recent_1000_results = deque(maxlen=self.WINDOW_1000)
        
        # Load recent data from persistent storage
        self._load_rolling_windows()
        
    def _load_stats(self) -> Dict[str, Any]:
        """Load stats from persistent storage."""
        if STATS_FILE.exists():
            try:
                with STATS_FILE.open('r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning reading stats file: {e}")
        
        # Default stats structure
        return {
            'total_operations': 0,
            'total_passes': 0,
            'total_fails': 0,
            'total_cycle_time_sum': 0.0,
            'last_cycle_time': None,
            'jobs': {},  # job_id -> {operations, passes, fails, cycle_time_sum}
            'recent_100_times': [],
            'recent_1000_times': [],
            'recent_100_results': [],
            'recent_1000_results': [],
        }
    
    def _save_stats(self):
        """Save stats to persistent storage."""
        try:
            # Update rolling windows in stats before saving
            self._stats['recent_100_times'] = list(self._recent_100_times)
            self._stats['recent_1000_times'] = list(self._recent_1000_times)
            self._stats['recent_100_results'] = list(self._recent_100_results)
            self._stats['recent_1000_results'] = list(self._recent_1000_results)
            
            STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with STATS_FILE.open('w') as f:
                json.dump(self._stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    def _load_rolling_windows(self):
        """Load rolling windows from persistent storage."""
        for t in self._stats.get('recent_100_times', []):
            self._recent_100_times.append(t)
        for t in self._stats.get('recent_1000_times', []):
            self._recent_1000_times.append(t)
        for r in self._stats.get('recent_100_results', []):
            self._recent_100_results.append(r)
        for r in self._stats.get('recent_1000_results', []):
            self._recent_1000_results.append(r)
    
    def set_current_job(self, job_id: Optional[str]):
        """Set the current job ID for job-specific tracking."""
        # If changing jobs and current job had operations, save it as last job
        if self._current_job and self._current_job != job_id:
            job_stats = self._stats['jobs'].get(self._current_job)
            if job_stats and job_stats['operations'] > 0:
                self._last_job = self._current_job
                self._stats['last_job'] = self._current_job
                self._save_stats()
        self._current_job = job_id
    
    def record_cycle(self, cycle_time: float, passed: bool):
        """
        Record a completed cycle.
        
        Args:
            cycle_time: Duration of the cycle in seconds
            passed: Whether the cycle passed (True) or failed (False)
        """
        # Update session stats
        self._session_operations += 1
        
        # Update total stats
        self._stats['total_operations'] += 1
        self._stats['total_cycle_time_sum'] += cycle_time
        self._stats['last_cycle_time'] = cycle_time
        
        if passed:
            self._stats['total_passes'] += 1
        else:
            self._stats['total_fails'] += 1
        
        # Update rolling windows
        self._recent_100_times.append(cycle_time)
        self._recent_1000_times.append(cycle_time)
        self._recent_100_results.append(passed)
        self._recent_1000_results.append(passed)
        
        # Update job stats
        if self._current_job:
            if self._current_job not in self._stats['jobs']:
                self._stats['jobs'][self._current_job] = {
                    'operations': 0,
                    'passes': 0,
                    'fails': 0,
                    'cycle_time_sum': 0.0
                }
            
            job_stats = self._stats['jobs'][self._current_job]
            job_stats['operations'] += 1
            job_stats['cycle_time_sum'] += cycle_time
            if passed:
                job_stats['passes'] += 1
            else:
                job_stats['fails'] += 1
        
        # Save to disk
        self._save_stats()
    
    def get_host_uptime(self) -> Optional[float]:
        """Get host computer uptime in seconds."""
        if not HAS_PSUTIL:
            return None
        try:
            return time.time() - psutil.boot_time()
        except Exception:
            return None
    
    def get_session_uptime(self) -> float:
        """Get app session uptime in seconds."""
        return time.time() - self._session_start_time
    
    def get_session_operations(self) -> int:
        """Get number of operations since app boot."""
        return self._session_operations
    
    def get_total_operations(self) -> int:
        """Get total number of operations ever."""
        return self._stats['total_operations']
    
    def get_last_cycle_time(self) -> Optional[float]:
        """Get the last cycle time in seconds."""
        return self._stats['last_cycle_time']
    
    def get_job_average_cycle_time(self) -> Optional[float]:
        """Get average cycle time for current job."""
        if not self._current_job:
            return None
        job_stats = self._stats['jobs'].get(self._current_job)
        if job_stats and job_stats['operations'] > 0:
            return job_stats['cycle_time_sum'] / job_stats['operations']
        return None
    
    def get_last_job_average_cycle_time(self) -> Optional[float]:
        """Get average cycle time for last job."""
        if not self._last_job:
            return None
        job_stats = self._stats['jobs'].get(self._last_job)
        if job_stats and job_stats['operations'] > 0:
            return job_stats['cycle_time_sum'] / job_stats['operations']
        return None
    
    def get_average_cycle_time_100(self) -> Optional[float]:
        """Get average cycle time for last 100 cycles."""
        if len(self._recent_100_times) > 0:
            return sum(self._recent_100_times) / len(self._recent_100_times)
        return None
    
    def get_average_cycle_time_1000(self) -> Optional[float]:
        """Get average cycle time for last 1000 cycles."""
        if len(self._recent_1000_times) > 0:
            return sum(self._recent_1000_times) / len(self._recent_1000_times)
        return None
    
    def get_average_cycle_time_total(self) -> Optional[float]:
        """Get average cycle time for all cycles ever."""
        if self._stats['total_operations'] > 0:
            return self._stats['total_cycle_time_sum'] / self._stats['total_operations']
        return None
    
    def get_job_yield(self) -> Optional[float]:
        """Get yield (pass rate) for current job as percentage."""
        if not self._current_job:
            return None
        job_stats = self._stats['jobs'].get(self._current_job)
        if job_stats and job_stats['operations'] > 0:
            return (job_stats['passes'] / job_stats['operations']) * 100
        return None
    
    def get_last_job_yield(self) -> Optional[float]:
        """Get yield (pass rate) for last job as percentage."""
        if not self._last_job:
            return None
        job_stats = self._stats['jobs'].get(self._last_job)
        if job_stats and job_stats['operations'] > 0:
            return (job_stats['passes'] / job_stats['operations']) * 100
        return None
    
    def get_yield_100(self) -> Optional[float]:
        """Get yield for last 100 cycles as percentage."""
        if len(self._recent_100_results) > 0:
            passes = sum(1 for r in self._recent_100_results if r)
            return (passes / len(self._recent_100_results)) * 100
        return None
    
    def get_yield_1000(self) -> Optional[float]:
        """Get yield for last 1000 cycles as percentage."""
        if len(self._recent_1000_results) > 0:
            passes = sum(1 for r in self._recent_1000_results if r)
            return (passes / len(self._recent_1000_results)) * 100
        return None
    
    def get_yield_total(self) -> Optional[float]:
        """Get total yield as percentage."""
        total = self._stats['total_operations']
        if total > 0:
            return (self._stats['total_passes'] / total) * 100
        return None
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all stats as a dictionary for display."""
        return {
            'session_uptime': self.get_session_uptime(),
            'host_uptime': self.get_host_uptime(),
            'operations_since_boot': self.get_session_operations(),
            'operations_total': self.get_total_operations(),
            'last_cycle_time': self.get_last_cycle_time(),
            'job_average_cycle_time': self.get_job_average_cycle_time(),
            'last_job_average_cycle_time': self.get_last_job_average_cycle_time(),
            'average_cycle_time_100': self.get_average_cycle_time_100(),
            'average_cycle_time_1000': self.get_average_cycle_time_1000(),
            'average_cycle_time_total': self.get_average_cycle_time_total(),
            'yield_job': self.get_job_yield(),
            'yield_last_job': self.get_last_job_yield(),
            'last_job': self._last_job,
            'yield_100': self.get_yield_100(),
            'yield_1000': self.get_yield_1000(),
            'yield_total': self.get_yield_total(),
            'current_job': self._current_job,
            'sample_size_100': len(self._recent_100_results),
            'sample_size_1000': len(self._recent_1000_results),
        }


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds is None:
        return '--'
    
    if seconds < 60:
        return f'{seconds:.1f}s'
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f'{mins}m {secs}s'
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f'{hours}h {mins}m'


def format_cycle_time(seconds: Optional[float]) -> str:
    """Format cycle time in MM:SS format."""
    if seconds is None:
        return '--:--'
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f'{mins:02d}:{secs:02d}'


def format_yield(percentage: Optional[float]) -> str:
    """Format yield as percentage string."""
    if percentage is None:
        return '--'
    return f'{percentage:.1f}%'


# Global stats instance
_stats_instance: Optional[CycleStats] = None


def get_stats() -> CycleStats:
    """Get the global stats instance."""
    global _stats_instance
    if _stats_instance is None:
        _stats_instance = CycleStats()
    return _stats_instance

