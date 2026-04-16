"""Unit tests for DeviceSimulator and SimulatorManager (no Kafka broker required)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.streaming.device_simulator import DeviceSimulator
from backend.src.streaming.simulator_manager import SimulatorManager


def run_async(coro):
    """Helper: run a coroutine synchronously (no pytest-asyncio needed)."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# DeviceSimulator — reading generation (pure logic, no Kafka)
# ---------------------------------------------------------------------------

@pytest.fixture
def solar_sim():
    return DeviceSimulator("src_solar", "solar", "comm_1", 51.0, 4.0, capacity_kw=10.0)


@pytest.fixture
def wind_sim():
    return DeviceSimulator("src_wind", "wind", "comm_1", 51.0, 4.0, capacity_kw=10.0)


@pytest.fixture
def load_sim():
    return DeviceSimulator("src_load", "load", "comm_1", 51.0, 4.0, capacity_kw=5.0)


def test_solar_output_is_non_negative(solar_sim):
    solar_sim.tick = 0
    for _ in range(20):
        solar_sim.tick += 100
        assert solar_sim._solar() >= 0.0


def test_solar_output_low_at_night(solar_sim):
    # tick=0 → hour=0 (midnight): solar factor is 0, output is noise-only (≤0 after clamp)
    solar_sim.tick = 0
    # With noise std=0.05 * capacity(10kW), output is clamped to ≥0
    # The factor at midnight is 0, so mean output = max(0, noise) ≈ 0
    readings = [solar_sim._solar() for _ in range(30)]
    assert sum(readings) / len(readings) < 1.0  # average near zero at midnight


def test_solar_output_positive_at_noon(solar_sim):
    # tick=43200 → hour=12 (noon)
    solar_sim.tick = 43200
    assert solar_sim._solar() > 0.0


def test_wind_output_is_non_negative(wind_sim):
    for i in range(50):
        wind_sim.tick = i * 10
        assert wind_sim._wind() >= 0.0


def test_wind_output_bounded_by_capacity(wind_sim):
    for i in range(100):
        wind_sim.tick = i
        assert wind_sim._wind() <= wind_sim.capacity_kw * 1.5  # noise can exceed briefly


def test_load_baseline_is_positive(load_sim):
    load_sim.tick = 0  # midnight
    assert load_sim._load() > 0.0


def test_load_higher_in_evening(load_sim):
    load_sim.tick = 0  # midnight
    midnight_load = load_sim._load()
    load_sim.tick = 19 * 3600  # 19:00 (peak)
    evening_load = load_sim._load()
    assert evening_load > midnight_load


def test_generate_reading_dispatches_correctly(solar_sim, wind_sim, load_sim):
    assert solar_sim._generate_reading() >= 0.0
    assert wind_sim._generate_reading() >= 0.0
    assert load_sim._generate_reading() > 0.0


def test_generate_reading_unknown_type_returns_zero():
    sim = DeviceSimulator("src_x", "unknown", "comm_1", 0.0, 0.0)
    assert sim._generate_reading() == 0.0


# ---------------------------------------------------------------------------
# DeviceSimulator — message format (mock KafkaProducer)
# ---------------------------------------------------------------------------

def test_simulator_sends_correct_message_format():
    """Verify the message schema sent to Kafka."""
    sent_messages = []

    mock_producer = MagicMock()
    mock_producer.send.side_effect = lambda topic, value: sent_messages.append((topic, value))

    sim = DeviceSimulator("src_1", "solar", "comm_abc", 51.0, 4.0, capacity_kw=5.0)
    sim.tick = 43200  # noon

    async def _run():
        with patch.object(sim, "_make_producer", return_value=mock_producer):
            async def fake_sleep(_):
                sim.stop()
            with patch("asyncio.sleep", side_effect=fake_sleep):
                await sim.run()

    run_async(_run())

    assert len(sent_messages) == 1
    topic, msg = sent_messages[0]
    assert topic == DeviceSimulator.TOPIC
    assert msg["source_id"] == "src_1"
    assert msg["device_type"] == "solar"
    assert msg["community_id"] == "comm_abc"
    assert "value" in msg
    assert "timestamp" in msg


# ---------------------------------------------------------------------------
# SimulatorManager
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_manager():
    """Ensure SimulatorManager state is clean before/after each test."""
    SimulatorManager._running.clear()
    yield
    SimulatorManager._running.clear()


def test_start_simulator_registers_it():
    async def _run():
        with patch.object(DeviceSimulator, "run", new_callable=AsyncMock):
            await SimulatorManager.start_simulator("src_1", "solar", "comm_1", 51.0, 4.0)
            assert SimulatorManager.is_running("src_1")
    run_async(_run())


def test_start_simulator_idempotent():
    async def _run():
        with patch.object(DeviceSimulator, "run", new_callable=AsyncMock):
            await SimulatorManager.start_simulator("src_1", "solar", "comm_1", 51.0, 4.0)
            await SimulatorManager.start_simulator("src_1", "solar", "comm_1", 51.0, 4.0)
            assert len(SimulatorManager.running_ids()) == 1
    run_async(_run())


def test_stop_simulator_removes_it():
    async def _run():
        with patch.object(DeviceSimulator, "run", new_callable=AsyncMock):
            await SimulatorManager.start_simulator("src_1", "solar", "comm_1", 51.0, 4.0)
            await SimulatorManager.stop_simulator("src_1")
            assert not SimulatorManager.is_running("src_1")
    run_async(_run())


def test_stop_nonexistent_simulator_is_noop():
    run_async(SimulatorManager.stop_simulator("does_not_exist"))  # should not raise


def test_stop_all_clears_all():
    async def _run():
        with patch.object(DeviceSimulator, "run", new_callable=AsyncMock):
            await SimulatorManager.start_simulator("src_1", "solar", "comm_1", 51.0, 4.0)
            await SimulatorManager.start_simulator("src_2", "wind", "comm_1", 51.0, 4.0)
            await SimulatorManager.stop_all()
            assert SimulatorManager.running_ids() == []
    run_async(_run())


# ---------------------------------------------------------------------------
# Consumer routing (_handle_device_reading)
# ---------------------------------------------------------------------------

def test_handle_device_reading_solar():
    from backend.src.streaming.communication import _handle_device_reading

    mock_db = MagicMock()
    msg = {
        "device_type": "solar",
        "source_id": "src_1",
        "community_id": "comm_abc",
        "value": 3.5,
        "timestamp": "2025-01-01T12:00:00+00:00",
    }
    _handle_device_reading(mock_db, msg)
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0]
    assert "solar" in call_args[0]
    assert call_args[1][1] == "src_1"
    assert call_args[1][3] == "comm_abc"


def test_handle_device_reading_wind():
    from backend.src.streaming.communication import _handle_device_reading

    mock_db = MagicMock()
    msg = {
        "device_type": "wind",
        "source_id": "src_w",
        "community_id": "comm_1",
        "value": 7.2,
        "timestamp": "2025-01-01T12:00:00+00:00",
    }
    _handle_device_reading(mock_db, msg)
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0]
    assert "wind" in call_args[0]


def test_handle_device_reading_load():
    from backend.src.streaming.communication import _handle_device_reading

    mock_db = MagicMock()
    msg = {
        "device_type": "load",
        "source_id": "src_l",
        "community_id": "comm_1",
        "value": 2.1,
        "timestamp": "2025-01-01T18:00:00+00:00",
    }
    _handle_device_reading(mock_db, msg)
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0]
    assert "load" in call_args[0]


def test_handle_device_reading_unknown_type_noop():
    from backend.src.streaming.communication import _handle_device_reading

    mock_db = MagicMock()
    msg = {
        "device_type": "market",
        "source_id": "src_m",
        "community_id": "comm_1",
        "value": 0.1,
        "timestamp": "2025-01-01T12:00:00+00:00",
    }
    _handle_device_reading(mock_db, msg)
    mock_db.execute.assert_not_called()


def test_handle_device_reading_z_suffix_timestamp():
    from backend.src.streaming.communication import _handle_device_reading

    mock_db = MagicMock()
    msg = {
        "device_type": "solar",
        "source_id": "src_1",
        "community_id": "comm_1",
        "value": 1.0,
        "timestamp": "2025-01-01T12:00:00Z",
    }
    # Should not raise
    _handle_device_reading(mock_db, msg)
    mock_db.execute.assert_called_once()
