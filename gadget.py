import inspect
import time
import sys
import os
import shutil
import re

__version__ = "0.1.0"

class Gadget:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.t0 = None
        self.group_times = {}
    
    def __call__(self, s='', group=None, _caller_frame=None):
        """Make the instance callable like a function."""
        if not self.verbose:
            return
            
        current_time = time.time()
        if self.t0 is None:
            self.t0 = current_time
        elapsed = current_time - self.t0
        self.t0 = time.time()

        # Use provided caller frame or get it from stack
        if _caller_frame is None:
            caller_frame = inspect.currentframe().f_back
        else:
            caller_frame = _caller_frame
        frame_info = inspect.getframeinfo(caller_frame)

        line_number = frame_info.lineno

        try:
            with open(frame_info.filename, 'r') as f:
                lines = f.readlines()
                line_content = lines[line_number - 2].rstrip()
        except:
            line_content = ""

        green_color = "\033[32m"
        reset_color = "\033[0m"
        
        # Shorten the file path - make it relative to cwd or just use filename
        try:
            short_path = os.path.relpath(frame_info.filename)
        except:
            short_path = os.path.basename(frame_info.filename)
        
        # Clickable file path for VS Code
        file_link = f"{short_path}:{line_number}"
        
        # Handle group tracking
        group_info = ""
        if group:
            if group not in self.group_times:
                self.group_times[group] = 0.0
            self.group_times[group] += elapsed
            group_info = f" [{group}: {elapsed:.6f}s (total: {self.group_times[group]:.6f}s)]"
        
        # Build the left side of the output
        left_output = f"{green_color}[line={line_number}] {elapsed:.6f}s {line_content}{reset_color} {s}{group_info}"
        
        # Get terminal width and right-align the file link
        terminal_width = shutil.get_terminal_size().columns
        # Strip ANSI codes for accurate length calculation
        left_output_plain = re.sub(r'\033\[[0-9;]+m', '', left_output)
        left_length = len(left_output_plain)
        
        # Calculate padding needed
        file_link_display = f"→ {file_link}"
        padding_needed = terminal_width - left_length - len(file_link_display) - 1
        padding = " " * max(1, padding_needed)  # At least one space
        
        output = f"{left_output}{padding}{file_link_display}"
        print(output)
    
    def reset(self, group=None):
        """Reset group timer(s). If group is None, reset all groups."""
        if group is None:
            self.group_times = {}
        elif group in self.group_times:
            del self.group_times[group]
    
    def mem(self, label='', _caller_frame=None):
        """Log memory usage at a checkpoint. Requires psutil (optional dependency).
        
        Color-coded output:
        - Green: all memory < 50%
        - Yellow: any memory 50-80%
        - Red: any memory > 80%
        
        Usage:
            timer = Gadget()
            timer.mem("after_loading_data")
            timer.mem("model_initialized")
        """
        try:
            import psutil
        except ImportError:
            print("gadget_mem requires psutil: pip install 'gadget-timer[mem]' or pip install psutil")
            return
        
        if not self.verbose:
            return
        
        # Use provided caller frame or get it from stack
        if _caller_frame is None:
            caller_frame = inspect.currentframe().f_back
        else:
            caller_frame = _caller_frame
        frame_info = inspect.getframeinfo(caller_frame)
        line_number = frame_info.lineno
        
        # Memory metrics
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        rss_gb = mem.rss / 1e9
        
        sys_mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Calculate percentage from displayed values
        sys_percent = (sys_mem.used / sys_mem.total) * 100
        
        # RSS as % of total system memory
        rss_percent = (rss_gb / (sys_mem.total / 1e9)) * 100
        
        # Calculate swap percentage
        swap_percent = 0
        if swap.total > 0:
            swap_percent = (swap.used / swap.total) * 100
        
        # Build output parts with percentages
        parts = [
            f"RSS={rss_gb:.2f}GB({rss_percent:.0f}%)",
            f"swap={swap.used / 1e9:.2f}GB({swap_percent:.0f}%)",
            f"sys={sys_mem.used / 1e9:.1f}/{sys_mem.total / 1e9:.1f}GB({sys_percent:.0f}%)",
        ]
        
        # Collect all percentages for color determination
        percentages = [sys_percent, rss_percent]
        
        if swap.total > 0:
            percentages.append(swap_percent)
        
        # Optional GPU info
        try:
            import torch
            if torch.cuda.is_available():
                gpu_used = torch.cuda.memory_allocated() / 1e9
                gpu_total = torch.cuda.get_device_properties(0).total_memory / 1e9
                gpu_percent = (gpu_used / gpu_total) * 100
                parts.append(f"gpu={gpu_used:.1f}/{gpu_total:.1f}GB({gpu_percent:.0f}%)")
                percentages.append(gpu_percent)
        except:
            pass
        
        # Determine color based on highest usage
        max_percent = max(percentages)
        if max_percent > 80:
            color = "\033[31m"  # Red
        elif max_percent >= 50:
            color = "\033[33m"  # Yellow
        else:
            color = "\033[32m"  # Green
        
        reset_color = "\033[0m"
        
        # Format file location
        try:
            short_path = os.path.relpath(frame_info.filename)
        except:
            short_path = os.path.basename(frame_info.filename)
        
        file_link = f"→ {short_path}:{line_number}"
        mem_label = f"[mem:{label}]" if label else "[mem]"
        output = f"{color}{mem_label} {' '.join(parts)}{reset_color} {file_link}"
        print(output)

# Create a default instance for convenience
_default_gadget = Gadget()

# Convenience functions that use the default instance
def gadget(s='', group=None):
    """Convenience function using default Gadget instance."""
    caller_frame = inspect.currentframe().f_back
    _default_gadget(s, group, _caller_frame=caller_frame)

def gadget_reset(group=None):
    """Convenience function using default Gadget instance."""
    _default_gadget.reset(group)

def gadget_config(verbose=True):
    """Configure the default Gadget instance."""
    global _default_gadget
    _default_gadget = Gadget(verbose=verbose)

def gadget_mem(label=''):
    """Convenience function for memory logging using default Gadget instance.
    
    Color-coded output:
    - Green: all memory < 50%
    - Yellow: any memory 50-80%
    - Red: any memory > 80%
    
    Usage:
        gadget_mem("after_loading_data")
        gadget_mem("model_initialized")
    """
    caller_frame = inspect.currentframe().f_back
    _default_gadget.mem(label, _caller_frame=caller_frame)