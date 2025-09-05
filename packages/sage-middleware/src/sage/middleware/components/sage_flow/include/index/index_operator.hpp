/*
 * Copyright 2024 SAGE Flow Team
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#pragma once

#include <memory>
#include <string>
#include <utility>

namespace sage_flow {

class Index;
class MemoryPool;

/**
 * @brief Base class for index operators
 * Reference: flow_old/include/index/index.h
 */
class IndexOperator {
public:
  explicit IndexOperator(std::shared_ptr<MemoryPool> memory_pool)
      : memory_pool_(std::move(memory_pool)) {}

  virtual ~IndexOperator() = default;

  // Prevent copying
  IndexOperator(const IndexOperator&) = delete;
  auto operator=(const IndexOperator&) -> IndexOperator& = delete;

  // Allow moving
  IndexOperator(IndexOperator&&) = default;
  auto operator=(IndexOperator&&) -> IndexOperator& = default;

  /**
   * @brief Process the operation with given index
   * @param index The index to operate on
   * @return true if operation successful
   */
  virtual auto Process(std::shared_ptr<Index> index) -> bool = 0;

  /**
   * @brief Get operator type name
   * @return Operator type as string
   */
  virtual auto GetOperatorType() const -> std::string = 0;

  /**
   * @brief Configure the operator with parameters
   * @param config Configuration string
   * @return true if configuration successful
   */
  virtual auto Configure(const std::string& config) -> bool = 0;

protected:
  std::shared_ptr<MemoryPool> memory_pool_;
};

}  // namespace sage_flow
