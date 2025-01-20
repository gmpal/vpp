import pytest
from unittest.mock import patch, mock_open
from src.db import read_db_info


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="[TimescaleDB]\ndbname=test_db\nuser=test_user\npassword=test_pass\nhost=test_host\nport=5432",
)
@patch("configparser.ConfigParser.read")
def test_read_db_info(mock_read, mock_open):
    expected_result = {
        "dbname": "test_db",
        "user": "test_user",
        "password": "test_pass",
        "host": "test_host",
        "port": "5432",
    }

    result = read_db_info()
    assert result == expected_result


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="[TimescaleDB]\ndbname=test_db\nuser=test_user\npassword=test_pass\nhost=test_host\nport=5432",
)
@patch("configparser.ConfigParser.read")
def test_read_db_info_missing_section(mock_read, mock_open):
    with pytest.raises(KeyError):
        read_db_info()


if __name__ == "__main__":
    pytest.main()
