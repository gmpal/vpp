import time
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import (
    UnknownTopicOrPartitionError,
    TopicAlreadyExistsError,
    NoBrokersAvailable,
)
import sys


def create_admin_client(
    bootstrap_servers="kafka:9092", max_retries=10, retry_interval=2
):
    """
    Create a KafkaAdminClient with retry logic to handle initial connection failures.
    """
    for attempt in range(max_retries):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id="db-init-client",
            )
            print("Successfully connected to Kafka.", flush=True)
            return admin_client
        except NoBrokersAvailable as e:
            print(
                f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}",
                flush=True,
            )
            if attempt == max_retries - 1:
                print(
                    "Could not connect to Kafka after max retries. Exiting.", flush=True
                )
                sys.exit(1)
            time.sleep(retry_interval)


def delete_topics_if_exist(
    admin_client, topics_to_check, wait_interval=3, max_wait=300
):
    """
    Delete specified Kafka topics if they exist and wait for deletion to complete.
    Returns True if all topics are deleted or don't exist, False if timeout occurs.
    """
    # List existing topics
    existing_topics = admin_client.list_topics()
    topics_to_delete = [topic for topic in topics_to_check if topic in existing_topics]

    if topics_to_delete:
        print(f"Deleting topics: {topics_to_delete}", flush=True)
        try:
            admin_client.delete_topics(topics=topics_to_delete)
        except UnknownTopicOrPartitionError:
            # Topic already doesn't exist
            pass

        # Wait until topics are fully removed
        waited = 0
        while waited < max_wait:
            current_topics = admin_client.list_topics()
            still_present = [t for t in topics_to_delete if t in current_topics]
            if not still_present:
                print("Topics deleted successfully.", flush=True)
                return True
            print(
                f"Waiting for topics to be deleted... still present: {still_present}",
                flush=True,
            )
            time.sleep(wait_interval)
            waited += wait_interval
        print("Timeout waiting for topic deletion.", flush=True)
        return False
    else:
        print("No topics to delete.", flush=True)
        return True


def create_topics(admin_client, topics_to_create, max_retries=5, retry_interval=5):
    """
    Create Kafka topics with retry logic to handle TopicAlreadyExistsError.
    """
    new_topics = [
        NewTopic(name=topic, num_partitions=1, replication_factor=1)
        for topic in topics_to_create
    ]

    for attempt in range(max_retries):
        try:
            existing_topics = admin_client.list_topics()
            topics_to_create_filtered = [
                topic for topic in new_topics if topic.name not in existing_topics
            ]
            if not topics_to_create_filtered:
                print("All topics already exist.", flush=True)
                return

            admin_client.create_topics(
                new_topics=topics_to_create_filtered, validate_only=False
            )
            print(
                f"Topics created successfully: {[topic.name for topic in topics_to_create_filtered]}",
                flush=True,
            )
            return
        except TopicAlreadyExistsError as e:
            print(
                f"TopicAlreadyExistsError on attempt {attempt + 1}/{max_retries}: {e}",
                flush=True,
            )
            if attempt == max_retries - 1:
                print("Failed to create topics after max retries. Exiting.", flush=True)
                sys.exit(1)
            print("Retrying after topics are fully deleted...", flush=True)
            time.sleep(retry_interval)
        except Exception as e:
            print(f"Error creating topics: {e}", flush=True)
            sys.exit(1)


if __name__ == "__main__":
    # Initialize Kafka admin client with retries
    admin_client = create_admin_client()

    # Define topics
    topics = ["solar", "wind", "load", "market"]

    # Delete existing topics and wait
    if not delete_topics_if_exist(admin_client, topics):
        print("Failed to delete topics within timeout. Exiting.", flush=True)
        sys.exit(1)

    # Create topics with retries
    create_topics(admin_client, topics)
