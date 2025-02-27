# kafka.Dockerfile
FROM confluentinc/cp-kafka:latest

# Environment variables for Kafka configuration
ENV KAFKA_BROKER_ID=1
ENV KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
ENV KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
ENV KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1

# Expose Kafka's default port
EXPOSE 9092