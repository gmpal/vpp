from src.communication import kafka_consume_centralized
from multiprocessing import Process
import sys

import os
import subprocess
import socket
import json

import time
from kafka.admin import KafkaAdminClient
from kafka import KafkaConsumer

import logging

# logging.basicConfig(level=logging.DEBUG)


def check_connectivity(host, port=9092):
    try:
        sock = socket.create_connection((host, port), timeout=5)
        print(f"Successfully connected to {host}:{port}", flush=True)
        sock.close()
    except Exception as e:
        print(f"Failed to connect to {host}:{port} - {e}", flush=True)


def test_dns_resolution():
    bootstrap = os.environ.get(
        "KAFKA_BOOTSTRAP_SERVERS", "kafka-service.vpp.local.vpp.local:9092"
    )
    # Remove port if needed (nslookup expects a hostname)
    bootstrap = bootstrap.split(":")[0]
    try:
        # Use subprocess to run nslookup
        result = subprocess.run(["nslookup", bootstrap], capture_output=True, text=True)
        print("DNS Resolution Test Output:", flush=True)
        print(result.stdout, flush=True)
    except Exception as e:
        print("Error during DNS resolution test:", e, flush=True)


if __name__ == "__main__":
    print("Consumer script started", flush=True)
    # test_dns_resolution()

    # try:
    #     resolved_ip = socket.gethostbyname("kafka-service.vpp.local.vpp.local")
    #     print("Resolved IP via socket.gethostbyname:", resolved_ip, flush=True)
    # except Exception as e:
    #     print("Socket DNS resolution failed:", e, flush=True)

    # admin_client = KafkaAdminClient(
    #     bootstrap_servers="kafka-service.vpp.local.vpp.local:9092", client_id="my_admin"
    # )

    # topics = admin_client.list_topics()
    # print("Topics in cluster:", topics, flush=True)

    # check_connectivity("kafka-service.vpp.local.vpp.local")

    # consumer = KafkaConsumer(
    #     "solar",
    #     "wind",
    #     "load",
    #     "market",
    #     bootstrap_servers="kafka-service.vpp.local.vpp.local:9092",
    #     auto_offset_reset="earliest",
    #     group_id="test-group-XYZ",  # a new consumer group for testing
    #     value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    # )

    # print("Consumer created, subscription:", consumer.subscription(), flush=True)

    # for topic in ["solar", "wind", "load", "market"]:
    #     parts = consumer.partitions_for_topic(topic)
    #     print(f"Partitions for {topic}: {parts}", flush=True)

    # # Try polling repeatedly
    # for i in range(5):
    #     msg_pack = consumer.poll(timeout_ms=5000)
    #     print(f"Poll attempt {i} returned:", msg_pack, flush=True)
    #     print("Assigned partitions:", consumer.assignment(), flush=True)
    #     time.sleep(2)

    # consumer.poll(timeout_ms=5000)
    # print("Assigned partitions:", consumer.assignment(), flush=True)

    # # Also, check partitions for each topic
    # for topic in ["solar", "wind", "load", "market"]:
    #     partitions = consumer.partitions_for_topic(topic)
    #     print(f"Partitions for {topic}: {partitions}", flush=True)

    kafka_consume_centralized()
