#include <common/data_types.h>
#include <compute_engine/compute_engine.h>
#include <stream/stream_environment.h>
#include <utils/conf_map.h>
#include <utils/monitoring.h>

#include <iostream>
#include <stdexcept>
#include <string>

#include "function/filter_function.h"
#include "function/map_function.h"
#include "function/sink_function.h"
#include "stream/data_stream_source/file_stream_source.h"
#include "stream/data_stream_source/simple_stream_source.h"

using namespace std;    // NOLINT
using namespace candy;  // NOLINT

const std::string CANDY_PATH = PROJECT_DIR;
#define CONFIG_DIR "/config/"

namespace candy {
void ValidateConfiguration(const ConfigMap &conf) {
  if (!conf.exist("inputPath") || !conf.exist("outputPath")) {
    throw runtime_error("Missing required configuration keys: inputPath or outputPath.");
  }
  if (!conf.exist("topK")) {
    throw runtime_error("Missing required configuration key: topK.");
  }
  if (!conf.exist("similarityThreshold")) {
    throw runtime_error("Missing required configuration key: similarityThreshold.");
  }
}

void SetupAndRunPipeline(const std::string &config_file_path) {
  StreamEnvironment env;

  const auto conf = candy::StreamEnvironment::loadConfiguration(config_file_path);

  try {
    ValidateConfiguration(conf);
  } catch (const exception &e) {
    throw;
  }

  PerformanceMonitor monitor;
  monitor.StartProfiling();

  try {
    auto concurrency_manager = env.getConcurrencyManager();
    auto index_id = concurrency_manager->create_index("test_index", IndexType::BruteForce, 3);
    auto record = make_unique<VectorRecord>(
        1, 3, VectorData{3, DataType::Float32, reinterpret_cast<char *>(new float[3]{1, 2, 3})});
    concurrency_manager->insert(index_id, std::move(record));
    record = make_unique<VectorRecord>(
        2, 3, VectorData{3, DataType::Float32, reinterpret_cast<char *>(new float[3]{4, 5, 6})});
    concurrency_manager->insert(index_id, std::move(record));
    record = make_unique<VectorRecord>(
        3, 3, VectorData{3, DataType::Float32, reinterpret_cast<char *>(new float[3]{7, 8, 9})});
    concurrency_manager->insert(index_id, std::move(record));
    auto file_stream = make_shared<SimpleStreamSource>("FileStream", conf.getString("inputPath"));
    file_stream
        ->filter(std::make_unique<FilterFunction>("filter1",
                                                  [](const std::unique_ptr<VectorRecord> &record) -> bool {
                                                    const auto rec = record.get();
                                                    std::cout << "A ";
                                                    return (rec->data_.data_)[0] > 0;
                                                  }))
        ->topk(index_id, 1)
        ->writeSink(std::make_unique<SinkFunction>(
            "sink1", [](const std::unique_ptr<VectorRecord> &record) { std::cout << "B "; }));
    env.addStream(std::move(file_stream));
    env.execute();
  } catch (const std::exception &e) {
    throw;
  }

  monitor.StopProfiling();
}
}  // namespace candy

auto main(int argc, char *argv[]) -> int {
  const std::string default_config_file = CANDY_PATH + CONFIG_DIR + "default_config.toml";

  string config_file_path;
  if (argc < 2) {
    config_file_path = default_config_file;
  } else {
    config_file_path = CANDY_PATH + CONFIG_DIR + string(argv[1]);
  }

  try {
    SetupAndRunPipeline(config_file_path);
  } catch (const exception &e) {
    cerr << "Error: " << e.what() << '\n';
    return 1;
  }

  return 0;
}
