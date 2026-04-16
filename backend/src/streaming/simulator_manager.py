"""Manages the lifecycle of active DeviceSimulator asyncio tasks."""
import asyncio
from typing import Dict, Tuple

from backend.src.streaming.device_simulator import DeviceSimulator


class SimulatorManager:
    """Registry of running simulators, keyed by source_id."""

    # Class-level dict shared across all instances / imports
    _running: Dict[str, Tuple[DeviceSimulator, asyncio.Task]] = {}

    @classmethod
    async def start_simulator(
        cls,
        source_id: str,
        source_type: str,
        community_id: str,
        latitude: float,
        longitude: float,
        capacity_kw: float = 10.0,
    ) -> None:
        if source_id in cls._running:
            return  # already running

        sim = DeviceSimulator(
            source_id=source_id,
            source_type=source_type,
            community_id=community_id,
            latitude=latitude,
            longitude=longitude,
            capacity_kw=capacity_kw,
        )
        task = asyncio.create_task(sim.run(), name=f"sim-{source_id}")
        cls._running[source_id] = (sim, task)

    @classmethod
    async def stop_simulator(cls, source_id: str) -> None:
        if source_id not in cls._running:
            return
        sim, task = cls._running.pop(source_id)
        sim.stop()
        try:
            await asyncio.wait_for(task, timeout=3)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            task.cancel()

    @classmethod
    def is_running(cls, source_id: str) -> bool:
        return source_id in cls._running

    @classmethod
    def running_ids(cls) -> list[str]:
        return list(cls._running.keys())

    @classmethod
    async def stop_all(cls) -> None:
        for source_id in list(cls._running.keys()):
            await cls.stop_simulator(source_id)
