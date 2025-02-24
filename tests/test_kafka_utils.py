import pytest
import pandas as pd
from unittest.mock import Mock, call
from your_module import (
    _get_server_info,
    make_single_producer_info,
    make_producers_info,
    kafka_produce,
    kafka_consume_centralized,
)


# --- Test _get_server_info ---
def test_get_server_info_from_config(mocker):
    """Test retrieving bootstrap servers from config.ini."""
    mock_config = mocker.patch("configparser.ConfigParser")
    mock_config.return_value.__getitem__.return_value = {
        "bootstrap_servers": "localhost:9092"
    }
    mocker.patch("os.environ.get", return_value=None)

    result = _get_server_info()
    assert result == "localhost:9092"
    mock_config.return_value.read.assert_called_once_with("config.ini")


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
    assert producers_info[0] == ("solar", "1", mock_df1)
    assert producers_info[1] == ("wind", "2", mock_df2)
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
    mock_producer = Mock()
    mocker.patch("your_module.KafkaProducer", return_value=mock_producer)
    mocker.patch("your_module._get_server_info", return_value="localhost:9092")
    mocker.patch("time.sleep")

    df = pd.DataFrame(
        {"value": [10.0, 20.0]}, index=["2025-01-01T00:00:00", "2025-01-01T01:00:00"]
    )
    producer_info = ("solar", "solar_1", df)

    kafka_produce(producer_info, sleeping_time=1)

    expected_calls = [
        call(
            "solar",
            value={
                "source_id": "solar_1",
                "timestamp": "2025-01-01T00:00:00",
                "data": 10.0,
            },
            partition=0,
        ),
        call(
            "solar",
            value={
                "source_id": "solar_1",
                "timestamp": "2025-01-01T01:00:00",
                "data": 20.0,
            },
            partition=0,
        ),
    ]
    mock_producer.send.assert_has_calls(expected_calls)
    assert mock_producer.send.call_count == 2
    assert time.sleep.call_count == 2


# --- Test kafka_consume_centralized ---
def test_kafka_consume_centralized(mocker):
    """Test consuming and processing Kafka messages."""
    mock_consumer = Mock()
    mock_consumer.__iter__.return_value = [
        Mock(
            topic="solar",
            value={
                "source_id": "solar_1",
                "timestamp": "2025-01-01T00:00:00",
                "data": 100.0,
            },
        ),
        Mock(
            topic="load",
            value={
                "source_id": None,
                "timestamp": "2025-01-01T01:00:00",
                "data": 200.0,
            },
        ),
    ]
    mocker.patch("your_module.KafkaConsumer", return_value=mock_consumer)
    mocker.patch("your_module._get_server_info", return_value="localhost:9092")
    mock_db_manager = mocker.patch("your_module.DatabaseManager")
    mock_crud = Mock()
    mocker.patch("your_module.CrudManager", return_value=mock_crud)

    # Run the function (limited iteration for testing)
    kafka_consume_centralized()

    # Check database save calls
    expected_calls = [
        call("solar", pd.to_datetime("2025-01-01T00:00:00"), "solar_1", 100.0),
        call("load", pd.to_datetime("2025-01-01T01:00:00"), None, 200.0),
    ]
    mock_crud.save_to_db.assert_has_calls(expected_calls)
    assert mock_crud.save_to_db.call_count == 2
