from src.communication import kafka_consume_centralized
from multiprocessing import Process

if __name__ == "__main__":
    consumer_process = Process(target=kafka_consume_centralized).start()
