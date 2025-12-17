"""
Timing Utilities for Latency Instrumentation

Provides context managers and utilities for logging execution times
of nodes and API calls in the validation pipeline.
"""

import time
import asyncio
import functools
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Callable, Any


def log_timing(node_name: str, action: str, duration_ms: Optional[float] = None):
    """Log a timing event in standard format."""
    if duration_ms is not None:
        print(f"[TIMING] {node_name}: {action} — duration={duration_ms:.0f}ms")
    else:
        print(f"[TIMING] {node_name}: {action}")


@contextmanager
def sync_timer(node_name: str, action: str = "OPERATION"):
    """Synchronous context manager for timing operations."""
    log_timing(node_name, f"{action} START")
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        log_timing(node_name, f"{action} END", duration_ms)


@asynccontextmanager
async def async_timer(node_name: str, action: str = "OPERATION"):
    """Async context manager for timing operations."""
    log_timing(node_name, f"{action} START")
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        log_timing(node_name, f"{action} END", duration_ms)


def timed_async(node_name: str):
    """Decorator for timing async functions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            async with async_timer(node_name, "NODE"):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


class StepTimer:
    """
    Utility class for timing multiple steps within a node.
    
    Usage:
        timer = StepTimer("reddit")
        with timer.step("tavily_search"):
            await search()
        with timer.step("embeddings"):
            await embed()
        timer.summary()
    """
    
    def __init__(self, node_name: str):
        self.node_name = node_name
        self.steps: dict[str, float] = {}
        self.start_time = time.perf_counter()
    
    @contextmanager
    def step(self, step_name: str):
        """Time a single step."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.steps[step_name] = duration_ms
            log_timing(self.node_name, step_name, duration_ms)
    
    @asynccontextmanager
    async def async_step(self, step_name: str):
        """Time a single async step."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.steps[step_name] = duration_ms
            log_timing(self.node_name, step_name, duration_ms)
    
    def summary(self):
        """Log summary of all steps."""
        total_ms = (time.perf_counter() - self.start_time) * 1000
        log_timing(self.node_name, "TOTAL", total_ms)
        return total_ms
