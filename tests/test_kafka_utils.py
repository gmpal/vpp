import pytest
import pandas as pd
from unittest.mock import Mock, call, MagicMock
import json

from backend.src.streaming.communication import (
    _get_server_info,
    make_single_producer_info,
    make_producers_info,
    kafka_produce,
    kafka_consume_centralized,
)


# --- Test _get_server_info ---
def test_get_server_info_from_config(mocker):
    """Test retrieving bootstrap servers from config.ini."""
    # Patch ConfigParser to return a mock config object
    mocker.patch("os.environ.get", return_value=None)

    mock_config = mocker.patch("configparser.ConfigParser")
    # Configure the mock config to return a specific bootstrap_servers value
    mock_config_instance = mock_config.return_value
    mock_config_instance.__getitem__.return_value = {
        "bootstrap_servers": "kafka:9092"
    }  # Mock section access

    result = _get_server_info()
    assert result == "kafka:9092"


def test_get_server_info_from_env(mocker):
    """Test retrieving bootstrap servers from environment variable."""
    mocker.patch("configparser.ConfigParser")
    mocker.patch("os.environ.get", return_value="env:9092")

    result = _get_server_info()
    assert result == "env:9092"


# --- Test make_single_producer_info ---
def test_make_single_producer_info(mocker):
    """Test creating producer info from a CSV file."""
    mock_df = pd.DataFrame({"value": [1, 2]}, index=["2025-01-01", "2025-01-02"])
    mocker.patch("pandas.read_csv", return_value=mock_df)

    topic, source_id, df = make_single_producer_info("root_dir", "solar", "123")

    assert topic == "solar"
    assert source_id == "123"
    assert df.equals(mock_df)
    pd.read_csv.assert_called_once_with("root_dir/123_solar.csv", index_col=0)


# --- Test make_producers_info ---
def test_make_producers_info(mocker):
    """Test generating producer info from directory files."""
    mock_listdir = mocker.patch(
        "os.listdir",
        return_value=[
            "1_solar.csv",
            "2_wind.csv",
            "synthetic_load_data.csv",
            "synthetic_market_price.csv",
        ],
    )
    mock_df1 = pd.DataFrame({"value": [1]}, index=["2025-01-01"])
    mock_df2 = pd.DataFrame({"value": [2]}, index=["2025-01-01"])
    mock_df_load = pd.DataFrame({"value": [3]}, index=["2025-01-01"])
    mock_df_market = pd.DataFrame({"value": [4]}, index=["2025-01-01"])
    mocker.patch(
        "pandas.read_csv",
        side_effect=[mock_df1, mock_df2, mock_df_load, mock_df_market],
    )

    producers_info = make_producers_info("data_dir/")

    assert len(producers_info) == 4
    assert producers_info[0] == ("solar.csv", "1", mock_df1)
    assert producers_info[1] == ("wind.csv", "2", mock_df2)
    assert producers_info[2] == ("load", None, mock_df_load)
    assert producers_info[3] == ("market", None, mock_df_market)
    mock_listdir.assert_called_once_with("data_dir/")
    pd.read_csv.assert_has_calls(
        [
            call("data_dir/1_solar.csv", index_col=0),
            call("data_dir/2_wind.csv", index_col=0),
            call("data_dir/synthetic_load_data.csv", index_col=0),
            call("data_dir/synthetic_market_price.csv", index_col=0),
        ]
    )


def test_make_producers_info_empty_dir(mocker):
    """Test handling an empty directory."""
    mocker.patch(
        "os.listdir",
        return_value=["synthetic_load_data.csv", "synthetic_market_price.csv"],
    )
    mock_df_load = pd.DataFrame({"value": [1]}, index=["2025-01-01"])
    mock_df_market = pd.DataFrame({"value": [2]}, index=["2025-01-01"])
    mocker.patch("pandas.read_csv", side_effect=[mock_df_load, mock_df_market])

    producers_info = make_producers_info("data_dir/")

    assert len(producers_info) == 2
    assert producers_info == [
        ("load", None, mock_df_load),
        ("market", None, mock_df_market),
    ]


# --- Test kafka_produce ---
def test_kafka_produce(mocker):
    """Test producing messages to Kafka."""
    mock_producer_init = mocker.patch("kafka.KafkaProducer.__init__", return_value=None)
    mock_producer_send = mocker.patch("kafka.KafkaProducer.send", return_value=None)
    mock_get_server_info = mocker.patch(
        "backend.src.streaming.communication._get_server_info",
        return_value="localhost:9092",
    )
    mock_sleep = mocker.patch("time.sleep")

    df = pd.DataFrame(
        {"value": [10.0, 20.0]}, index=["2025-01-01T00:00:00", "2025-01-01T01:00:00"]
    )
    producer_info = ("solar", "solar_1", df)

    kafka_produce(producer_info, sleeping_time=1)

    # 2. KafkaProducer.send was called twice (once per row) with correct topic and messages
    assert mock_producer_send.call_count == 2


# --- Test kafka_consume_centralized ---
def test_kafka_consume_centralized(mocker):
    """Test consuming and processing messages from Kafka topics."""
    # Mock _get_server_info
    mock_get_server_info = mocker.patch(
        "backend.src.streaming.communication._get_server_info",
        return_value="localhost:9092",
    )

    # Mock the KafkaConsumer instance behavior
    mock_consumer_instance = MagicMock()
    # Define sample messages
    deserializer = lambda x: json.loads(x.decode("utf-8"))
    messages = [
        MagicMock(
            topic="solar",
            value=deserializer(
                json.dumps(
                    {
                        "source_id": "solar_1",
                        "timestamp": "2025-01-01T00:00:00",
                        "data": 10.0,
                    }
                ).encode("utf-8")
            ),
        ),
        MagicMock(
            topic="wind",
            value=deserializer(
                json.dumps(
                    {
                        "source_id": "wind_1",
                        "timestamp": "2025-01-01T01:00:00",
                        "data": 15.0,
                    }
                ).encode("utf-8")
            ),
        ),
    ]
    # Create a mock consumer instance
    mock_consumer_instance = MagicMock()
    # Make the consumer iterable with your sample messages
    mock_consumer_instance.__iter__.return_value = iter(messages)

    # Patch the KafkaConsumer in the module where it's used
    kafka_consumer_patch = mocker.patch(
        "backend.src.streaming.communication.KafkaConsumer",
        return_value=mock_consumer_instance,
    )

    # Mock DatabaseManager and CrudManager
    mock_db_manager = mocker.patch(
        "backend.src.streaming.communication.DatabaseManager"
    )
    mock_crud_manager = mocker.patch("backend.src.streaming.communication.CrudManager")
    mock_crud_instance = mock_crud_manager.return_value

    # Mock pd.to_datetime
    mock_to_datetime = mocker.patch("pandas.to_datetime")

    # Call the function
    kafka_consume_centralized()

    # Assertions

    # 2. DatabaseManager and CrudManager were instantiated
    mock_db_manager.assert_called_once()
    mock_crud_manager.assert_called_once_with(mock_db_manager.return_value)

    # 3. save_to_db was called for each message
    assert mock_crud_instance.save_to_db.call_count == 2
    expected_calls = [
        mocker.call("solar", mock_to_datetime.return_value, "solar_1", 10.0),
        mocker.call("wind", mock_to_datetime.return_value, "wind_1", 15.0),
    ]
    mock_crud_instance.save_to_db.assert_has_calls(expected_calls, any_order=False)

    # 4. pd.to_datetime was called with correct timestamps
    assert mock_to_datetime.call_count == 2
    mock_to_datetime.assert_has_calls(
        [
            mocker.call("2025-01-01T00:00:00"),
            mocker.call("2025-01-01T01:00:00"),
        ],
        any_order=False,
    )

    # 5. _get_server_info was called once
    mock_get_server_info.assert_called_once()
