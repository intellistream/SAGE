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
    auto index_id = concurrency_manager->create_index("test_index", IndexType::BruteForce, 10);
    auto base_stream = make_shared<SimpleStreamSource>("FileStream", "data/vector_records_high_base.bin");
    base_stream->Init();
    std::unique_ptr<VectorRecord> record;
    while ((record = base_stream->Next())) {
      concurrency_manager->insert(index_id, std::move(record));
    }
    auto file_stream = make_shared<SimpleStreamSource>("FileStream", "data/vector_records_high_query.bin");
    file_stream->topk(index_id, 5);
    env.addStream(std::move(file_stream));
    auto begin = std::chrono::high_resolution_clock::now();
    env.execute();
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - begin);
    std::cout << "Execution time: " << duration.count() << " ms\n";
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
