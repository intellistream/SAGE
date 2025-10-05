#include <common/data_types.h>
#include <compute_engine/compute_engine.h>
#include <stream/stream_environment.h>
#include <utils/conf_map.h>
#include <utils/monitoring.h>

#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_set>

#include "function/filter_function.h"
#include "function/itopk_function.h"
#include "function/map_function.h"
#include "function/sink_function.h"
#include "function/window_function.h"
#include "stream/data_stream_source/file_stream_source.h"
#include "stream/data_stream_source/sift_stream_source.h"
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
    auto itopk_record = make_unique<VectorRecord>(
        -1, 128, VectorData{128, DataType::Float32, reinterpret_cast<char *>(new float[128])});
    auto file_stream = make_shared<SiftStreamSource>("FileStream", "./data/siftsmall/siftsmall_base.fvecs");
    int cnt = 0;
    std::unordered_map<uint64_t, int> map;
    file_stream->window(std::make_unique<WindowFunction>("window1", 500, 400, WindowType::Tumbling))
        ->itopk(std::make_unique<ITopkFunction>("itopk1", 10, 128, std::move(itopk_record)))
        ->writeSink(std::make_unique<SinkFunction>("sink1", [&cnt, &map](const std::unique_ptr<VectorRecord> &record) {
          cnt++;
          if (map.contains(record->uid_)) {
            map[record->uid_]++;
          } else {
            map.emplace(record->uid_, 1);
          }
        }));
    env.addStream(std::move(file_stream));
    auto begin = std::chrono::high_resolution_clock::now();
    env.execute();
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - begin).count();
    int total = 0;
    for (const auto &[fst, snd] : map) {
      if (snd > 1) {
        total += snd;
      }
    }
    std::cout << "Duplicate records: " << total << " of " << cnt << std::endl;
    std::cout << cnt / 10 << " Operation " << "Execution time: " << duration << " ms" << std::endl;
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
