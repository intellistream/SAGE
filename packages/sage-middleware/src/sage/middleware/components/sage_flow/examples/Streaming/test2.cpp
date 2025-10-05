#include <common/data_types.h>
#include <compute_engine/compute_engine.h>
#include <stream/stream_environment.h>
#include <utils/conf_map.h>
#include <utils/monitoring.h>

#include <iostream>
#include <stdexcept>
#include <string>

#include "function/aggregate_function.h"
#include "function/filter_function.h"
#include "function/itopk_function.h"
#include "function/map_function.h"
#include "function/sink_function.h"
#include "function/window_function.h"
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
    auto file_stream = make_shared<SimpleStreamSource>("FileStream", conf.getString("inputPath"));
    int cnt = 0;
    float sum = 0;
    file_stream
        ->writeSink(std::make_unique<SinkFunction>("sink1",
                                                   [&cnt, &sum](const std::unique_ptr<VectorRecord> &record) {
                                                     cnt++;
                                                     sum += *(float*)(record->data_.data_.get());
                                                     if (cnt == 50) {
                                                       std::cout << "window support to print: " << sum / cnt << "\n";
                                                       cnt = 0;
                                                       sum = 0;
                                                     }
                                                   }))
        ->window(std::make_unique<WindowFunction>("window1", 50, 0, WindowType::Tumbling))
        ->aggregate(std::make_unique<AggregateFunction>("aggregate1", AggregateType::Avg))
        ->writeSink(std::make_unique<SinkFunction>("sink2", [](const std::unique_ptr<VectorRecord> &record) {
          std::cout << "aggregate val: " << *(float*)(record->data_.data_.get()) << '\n';
        }));
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
