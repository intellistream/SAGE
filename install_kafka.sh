# 下载 Kafka 并进入目录
cd ~
# wget https://downloads.apache.org/kafka/3.7.2/kafka_2.13-3.7.2.tgz
# tar -xzf kafka_2.13-3.7.2.tgz
delete kafka
mv kafka_2.13-3.7.2 kafka

# 启动 zookeeper
nohup ~/kafka/bin/zookeeper-server-start.sh ~/kafka/config/zookeeper.properties > zk.log 2>&1 &

# 启动 kafka
nohup ~/kafka/bin/kafka-server-start.sh ~/kafka/config/server.properties > kafka.log 2>&1 &
