#!/bin/bash
# SAGE Kafka Stop Script

KAFKA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping SAGE Kafka services..."

# Stop Kafka
if pgrep -f "sage-server.properties" > /dev/null; then
    echo "Stopping Kafka..."
    "$KAFKA_DIR/bin/kafka-server-stop.sh"
    sleep 2
fi

# Stop Zookeeper
if pgrep -f "sage-zookeeper.properties" > /dev/null; then
    echo "Stopping Zookeeper..."
    "$KAFKA_DIR/bin/zookeeper-server-stop.sh"
    sleep 2
fi

echo "SAGE Kafka services stopped"