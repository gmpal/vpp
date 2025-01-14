import time
import json
import pandas as pd

from kafka import KafkaConsumer, KafkaProducer
import json
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

import psycopg2

import configparser


def kafka_produce(root: str = "../data/"):
    """
    Produces messages to Kafka topics from CSV data files.
    This function reads wind turbine power output, solar panel generation, and synthetic load data
    from CSV files located in the specified root directory. It then sends the data as JSON messages
    to respective Kafka topics ("solar-power", "wind-power", and "load-data") at a specified interval.
    Args:
        root (str): The root directory where the CSV data files are located. Default is "../data/".
        port (int): The port number for the Kafka server. Default is 9092.
    Raises:
        FileNotFoundError: If any of the CSV files are not found in the specified root directory.
        KafkaError: If there is an issue with sending messages to Kafka topics.
    Example:
        kafka_produce(root="/path/to/data/", port=9092)
    """

    # Create a ConfigParser instance
    config = configparser.ConfigParser()

    # Read the config.ini file
    config.read("config.ini")

    # Access Kafka settings
    kafka_bootstrap_servers = config["Kafka"]["bootstrap_servers"]

    # Initialize Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(
            "utf-8"
        ),  # Serialize messages as JSON
    )

    wind_data = pd.read_csv(root + "wind_turbine_power_output.csv", index_col=0)
    solar_data = pd.read_csv(root + "solar_panel_generation.csv", index_col=0)
    load_data = pd.read_csv(root + "synthetic_load_data.csv", index_col=0)
    wind_data.columns = ["wind_power"]
    solar_data.columns = ["solar_power"]
    load_data.columns = ["load_data"]

    data = pd.concat([wind_data, solar_data, load_data], axis=1)

    for timestamp, row in data.iterrows():
        # Prepare data as JSON
        solar_message = {"timestamp": str(timestamp), "power": row["solar_power"]}
        wind_message = {"timestamp": str(timestamp), "power": row["wind_power"]}
        load_message = {"timestamp": str(timestamp), "load": row["load_data"]}

        # Send messages to respective topics
        producer.send("solar-power", solar_message)
        producer.send("wind-power", wind_message)
        producer.send("load-data", load_message)

        print(f"Point from {timestamp} sent")

        # Simulate real-time streaming (1 message per second)
        time.sleep(5)


def kafka_consume_and_store():
    # Configuration setup from config.ini
    config = configparser.ConfigParser()
    config.read("config.ini")
    kafka_bootstrap_servers = config["Kafka"]["bootstrap_servers"]
    db_connection_info = {
        "dbname": config["TimescaleDB"]["dbname"],
        "user": config["TimescaleDB"]["user"],
        "password": config["TimescaleDB"]["password"],
        "host": config["TimescaleDB"]["host"],
        "port": config["TimescaleDB"]["port"],
    }

    # Connect to TimescaleDB
    conn = psycopg2.connect(**db_connection_info)
    cursor = conn.cursor()

    consumer = KafkaConsumer(
        "solar-power",
        "wind-power",
        "load-data",
        bootstrap_servers=kafka_bootstrap_servers,
        auto_offset_reset="earliest",
        group_id="my-group",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )

    data = {"solar": 0, "wind": 0, "load": 0}

    insert_query = """
        INSERT INTO public.power_data (time, solar_power, wind_power, load_power, net_power)
        VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute("SELECT current_database();")
    print("Connected to database:", cursor.fetchone()[0])

    cursor.execute(
        """
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name = 'power_data';
    """
    )
    print("Found tables:", cursor.fetchall())

    for msg in consumer:
        topic = msg.topic

        # Update the correct field based on the topic
        if topic == "solar-power":
            data["solar"] = msg.value.get("power", 0)
        elif topic == "wind-power":
            data["wind"] = msg.value.get("power", 0)
        elif topic == "load-data":
            data["load"] = msg.value.get("load", 0)

        net_power = data["solar"] + data["wind"] - data["load"]
        current_time = datetime.now()

        # Insert the data into TimescaleDB
        cursor.execute(
            insert_query,
            (current_time, data["solar"], data["wind"], data["load"], net_power),
        )
        conn.commit()

        print(
            f"Inserted at {current_time}: Solar={data['solar']}, Wind={data['wind']}, Load={data['load']}, Net={net_power}"
        )

    # Close connection on exit (this part may vary depending on how you handle shutdown)
    cursor.close()
    conn.close()


def kafka_consume():

    # Create a ConfigParser instance
    config = configparser.ConfigParser()

    # Read the config.ini file
    config.read("config.ini")

    # Access Kafka settings
    kafka_bootstrap_servers = config["Kafka"]["bootstrap_servers"]

    # Access InfluxDB settings
    influx_url = config["InfluxDB"]["url"]
    influx_token = config["InfluxDB"]["token"]
    influx_org = config["InfluxDB"]["org"]
    influx_bucket = config["InfluxDB"]["bucket"]

    # Initialize InfluxDB client
    client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    consumer = KafkaConsumer(
        "solar-power",
        "wind-power",
        "load-data",
        bootstrap_servers=kafka_bootstrap_servers,
        auto_offset_reset="earliest",
        group_id="my-group",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )

    data = {"solar": 0, "wind": 0, "load": 0}

    for msg in consumer:
        topic = msg.topic

        # Update the correct field based on the topic
        if topic == "solar-power":
            data["solar"] = msg.value["power"]
        elif topic == "wind-power":
            data["wind"] = msg.value["power"]
        elif topic == "load-data":
            data["load"] = msg.value["load"]

        net_power = data["solar"] + data["wind"] - data["load"]
        print(
            f"Timestamp: {datetime.now()}, Net Power: {net_power}, "
            f"Solar: {data['solar']}, Wind: {data['wind']}, Load: {data['load']}"
        )

        # Prepare InfluxDB point
        point = (
            Point("vpp_power")
            .field("solar_power", float(data["solar"]))
            .field("wind_power", float(data["wind"]))
            .field("load_power", float(data["load"]))
            .field("net_power", float(net_power))
            .time(datetime.now())
        )

        # Write to InfluxDB
        write_api.write(bucket=influx_bucket, org=influx_org, record=point)
        print("Data written to InfluxDB")
