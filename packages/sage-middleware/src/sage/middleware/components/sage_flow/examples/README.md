apps/
├── db_client/ # A command-line client for interacting with the vector database
│ ├── db_client.cpp # The main application source file for the database client
│ └── CMakeLists.txt # CMake file to build this application, linking to core library
├── query_tool/ # Tool for issuing interactive queries to the vector database
│ ├── query_tool.cpp # Main source file for the query tool
│ └── CMakeLists.txt # CMake file to build this tool, linking to the core library
├── ml_optimizer_tool/ # Tool to interact with and benchmark ML-based optimization
│ ├── ml_optimizer_tool.cpp # The main application source file for ML optimization
│ └── CMakeLists.txt # CMake file for building this tool, linking to ML optimization library
└── benchmark_tool/ # Tool for benchmarking database performance
├── benchmark_tool.cpp # The main application source file for benchmarking the database
└── CMakeLists.txt # CMake file to build the benchmark tool, linking to core and performance libraries