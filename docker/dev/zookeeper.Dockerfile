FROM confluentinc/cp-zookeeper:latest

# Environment variables for Zookeeper
ENV ZOOKEEPER_CLIENT_PORT=2181
ENV ZOOKEEPER_TICK_TIME=2000

# Expose the Zookeeper client port
EXPOSE 2181