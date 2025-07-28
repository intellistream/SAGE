package com.my.examples.redpandaFlink;

import org.apache.flink.api.common.functions.FlatMapFunction;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.util.Collector;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;

// this code was mostly cobbled together from an original demo found at:
// https://github.com/redpanda-data/flink-kafka-examples/blob/main/src/main/java/io/redpanda/examples/WordCount.java

public class StreamingJob {
    final static String inputTopic = "words";
    final static String outputTopic = "words-count";
    final static String jobTitle = "WordCount";

    public static void main(String[] args) throws Exception {
        // Redpanda is listening on localhost. Remember to use the container name for the address
        final String bootstrapServers = args.length > 0 ? args[0] : "redpanda-1:9092";

        // set up the streaming execution environment
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        KafkaSource<String> source = KafkaSource.<String>builder()
                .setBootstrapServers(bootstrapServers)
                .setTopics(inputTopic)
                .setStartingOffsets(OffsetsInitializer.earliest())
                .setValueOnlyDeserializer(new SimpleStringSchema())
                .build();

        KafkaRecordSerializationSchema<String> serializer = KafkaRecordSerializationSchema.builder()
                .setValueSerializationSchema(new SimpleStringSchema())
                .setTopic(outputTopic)
                .build();

        KafkaSink<String> sink = KafkaSink.<String>builder()
                .setBootstrapServers(bootstrapServers)
                .setRecordSerializer(serializer)
                .build();


        /**
         * Adds a data {@link Source} to the environment to get a {@link DataStream}.
         *
         * <p>The result will be either a bounded data stream (that can be processed in a batch way) or
         * an unbounded data stream (that must be processed in a streaming way), based on the
         * boundedness property of the source, as defined by {@link Source#getBoundedness()}.
         *
         * <p>The result type (that is used to create serializers for the produced data events) will be
         * automatically extracted. This is useful for sources that describe the produced types already
         * in their configuration, to avoid having to declare the type multiple times. For example the
         * file sources and Kafka sources already define the produced byte their
         * parsers/serializers/formats, and can forward that information.
         *
         * @param source the user defined source
         * @param sourceName Name of the data source
         * @param <OUT> type of the returned stream
         * @return the data stream constructed
         */
        @PublicEvolving
        public <OUT> DataStreamSource<OUT> fromSource(
                Source<OUT, ?, ?> source,
                WatermarkStrategy<OUT> timestampsAndWatermarks,
                String sourceName) {
            return fromSource(source, timestampsAndWatermarks, sourceName, null);
        }

        DataStream<String> text = env.fromSource(source, WatermarkStrategy.noWatermarks(), "Redpanda Source");

        // Split up the lines in pairs (2-tuples) containing: (word,1)
        DataStream<String> counts = text.flatMap(new Tokenizer())
        // Group by the tuple field "0" and sum up tuple field "1"
        .keyBy(value -> value.f0)
        .sum(1)
        .flatMap(new Reducer());

        // Add the sinkTo so results
        // are written to the outputTopic
        counts.sinkTo(sink);

        // Execute program
        env.execute(jobTitle);
    }

    /**
     * Implements the string tokenizer that splits sentences into words as a user-defined
     * FlatMapFunction. The function takes a line (String) and splits it into multiple pairs in the
     * form of "(word,1)" ({@code Tuple2<String, Integer>}).
     */
    public static final class Tokenizer
            implements FlatMapFunction<String, Tuple2<String, Integer>> {

        @Override
        public void flatMap(String value, Collector<Tuple2<String, Integer>> out) {
            // Normalize and split the line
            String[] tokens = value.toLowerCase().split("\\W+");

            // Emit the pairs
            for (String token : tokens) {
                if (token.length() > 0) {
                    out.collect(new Tuple2<>(token, 1));
                }
            }
        }
    }

    // Implements a simple reducer using FlatMap to
    // reduce the Tuple2 into a single string for
    // writing to kafka topics
    public static final class Reducer
            implements FlatMapFunction<Tuple2<String, Integer>, String> {

        @Override
        public void flatMap(Tuple2<String, Integer> value, Collector<String> out) {
            // Convert the pairs to a string
            // for easy writing to Kafka Topic
            String count = value.f0 + " " + value.f1;
            out.collect(count);
        }
    }
}