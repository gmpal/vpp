import time
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import UnknownTopicOrPartitionError, TopicAlreadyExistsError

bootstrap_servers = "kafka-service.vpp.local.vpp.local:9092"
admin_client = KafkaAdminClient(
    bootstrap_servers=bootstrap_servers, client_id="my_admin"
)

topics = ["solar", "wind", "load", "market"]


def delete_topics_if_exist(topics_to_check, wait_interval=3, max_wait=300):
    # List existing topics.
    existing_topics = admin_client.list_topics()
    topics_to_delete = [topic for topic in topics_to_check if topic in existing_topics]
    if topics_to_delete:
        print(f"Deleting topics: {topics_to_delete}", flush=True)
        try:
            admin_client.delete_topics(topics=topics_to_delete)
        except UnknownTopicOrPartitionError:
            # Topic already doesn't exist.
            pass

        # Wait until topics are fully removed.
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
    else:
        print("No topics to delete.", flush=True)
    return False


def create_topics(topics_to_create):
    new_topics = [
        NewTopic(name=topic, num_partitions=1, replication_factor=1)
        for topic in topics_to_create
    ]
    try:
        admin_client.create_topics(new_topics=new_topics, validate_only=False)
        print("Topics created successfully.", flush=True)
    except TopicAlreadyExistsError as e:
        print(
            "TopicAlreadyExistsError caught. Topics may still be marked for deletion.",
            flush=True,
        )
        print(e, flush=True)
    except Exception as e:
        print("Error creating topics:", e, flush=True)


if __name__ == "__main__":
    # First, attempt to delete topics if they exist.
    delete_topics_if_exist(topics)
    # Then, create the topics.
    create_topics(topics)
