/**
 * @file test_operators.cpp
 * @brief 操作符单元测试
 * 
 * 测试 Map, Filter, Aggregate, Source, Sink 等核心操作符
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <memory>
#include <vector>
#include <string>
#include <functional>
#include <algorithm>
#include <chrono>

// 简化的操作符测试实现
namespace sage_flow {

// 基础操作符接口
class BaseOperator {
public:
    virtual ~BaseOperator() = default;
    virtual bool process(const std::vector<std::string>& input, 
                        std::vector<std::string>& output) = 0;
    virtual std::string get_type() const = 0;
};

// Map 操作符
class MapOperator : public BaseOperator {
public:
    using MapFunction = std::function<std::string(const std::string&)>;
    
    explicit MapOperator(MapFunction func) : map_func_(func) {}
    
    bool process(const std::vector<std::string>& input, 
                std::vector<std::string>& output) override {
        output.clear();
        output.reserve(input.size());
        
        for (const auto& item : input) {
            output.push_back(map_func_(item));
        }
        return true;
    }
    
    std::string get_type() const override { return "map"; }

private:
    MapFunction map_func_;
};

// Filter 操作符
class FilterOperator : public BaseOperator {
public:
    using FilterFunction = std::function<bool(const std::string&)>;
    
    explicit FilterOperator(FilterFunction func) : filter_func_(func) {}
    
    bool process(const std::vector<std::string>& input, 
                std::vector<std::string>& output) override {
        output.clear();
        
        for (const auto& item : input) {
            if (filter_func_(item)) {
                output.push_back(item);
            }
        }
        return true;
    }
    
    std::string get_type() const override { return "filter"; }

private:
    FilterFunction filter_func_;
};

// Aggregate 操作符
class AggregateOperator : public BaseOperator {
public:
    using AggregateFunction = std::function<std::string(const std::vector<std::string>&)>;
    
    explicit AggregateOperator(AggregateFunction func) : agg_func_(func) {}
    
    bool process(const std::vector<std::string>& input, 
                std::vector<std::string>& output) override {
        output.clear();
        if (!input.empty()) {
            output.push_back(agg_func_(input));
        }
        return true;
    }
    
    std::string get_type() const override { return "aggregate"; }

private:
    AggregateFunction agg_func_;
};

// Source 操作符
class SourceOperator : public BaseOperator {
public:
    explicit SourceOperator(std::vector<std::string> data) 
        : data_(std::move(data)), current_index_(0) {}
    
    bool process(const std::vector<std::string>& input, 
                std::vector<std::string>& output) override {
        output.clear();
        
        if (current_index_ < data_.size()) {
            output.push_back(data_[current_index_++]);
            return true;
        }
        return false; // 没有更多数据
    }
    
    std::string get_type() const override { return "source"; }
    
    bool has_more_data() const { return current_index_ < data_.size(); }
    void reset() { current_index_ = 0; }

private:
    std::vector<std::string> data_;
    size_t current_index_;
};

// Sink 操作符
class SinkOperator : public BaseOperator {
public:
    bool process(const std::vector<std::string>& input, 
                std::vector<std::string>& output) override {
        // Sink 操作符收集数据但不产生输出
        for (const auto& item : input) {
            collected_data_.push_back(item);
        }
        output.clear();
        return true;
    }
    
    std::string get_type() const override { return "sink"; }
    
    const std::vector<std::string>& get_collected_data() const { 
        return collected_data_; 
    }
    
    void clear() { collected_data_.clear(); }

private:
    std::vector<std::string> collected_data_;
};

// Join 操作符
class JoinOperator : public BaseOperator {
public:
    using KeyExtractor = std::function<std::string(const std::string&)>;
    
    JoinOperator(KeyExtractor left_key, KeyExtractor right_key)
        : left_key_extractor_(left_key), right_key_extractor_(right_key) {}
    
    void set_left_data(const std::vector<std::string>& data) {
        left_data_ = data;
    }
    
    void set_right_data(const std::vector<std::string>& data) {
        right_data_ = data;
    }
    
    bool process(const std::vector<std::string>& input, 
                std::vector<std::string>& output) override {
        output.clear();
        
        // 简化的 inner join 实现
        for (const auto& left_item : left_data_) {
            std::string left_key = left_key_extractor_(left_item);
            
            for (const auto& right_item : right_data_) {
                std::string right_key = right_key_extractor_(right_item);
                
                if (left_key == right_key) {
                    output.push_back(left_item + "+" + right_item);
                }
            }
        }
        
        return true;
    }
    
    std::string get_type() const override { return "join"; }

private:
    KeyExtractor left_key_extractor_;
    KeyExtractor right_key_extractor_;
    std::vector<std::string> left_data_;
    std::vector<std::string> right_data_;
};

} // namespace sage_flow

using namespace sage_flow;

// MapOperator 测试套件
class MapOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建一个简单的大写转换函数
        auto uppercase_func = [](const std::string& input) {
            std::string result = input;
            std::transform(result.begin(), result.end(), result.begin(), ::toupper);
            return result;
        };
        
        map_op_ = std::make_unique<MapOperator>(uppercase_func);
        test_input_ = {"hello", "world", "test"};
    }

    std::unique_ptr<MapOperator> map_op_;
    std::vector<std::string> test_input_;
};

TEST_F(MapOperatorTest, BasicTransformation) {
    std::vector<std::string> output;
    
    EXPECT_TRUE(map_op_->process(test_input_, output));
    EXPECT_EQ(output.size(), test_input_.size());
    
    // 验证转换结果
    EXPECT_EQ(output[0], "HELLO");
    EXPECT_EQ(output[1], "WORLD");
    EXPECT_EQ(output[2], "TEST");
}

TEST_F(MapOperatorTest, EmptyInput) {
    std::vector<std::string> empty_input;
    std::vector<std::string> output;
    
    EXPECT_TRUE(map_op_->process(empty_input, output));
    EXPECT_TRUE(output.empty());
}

TEST_F(MapOperatorTest, TypeCheck) {
    EXPECT_EQ(map_op_->get_type(), "map");
}

// FilterOperator 测试套件
class FilterOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建一个过滤长度大于3的字符串的函数
        auto length_filter = [](const std::string& input) {
            return input.length() > 3;
        };
        
        filter_op_ = std::make_unique<FilterOperator>(length_filter);
        test_input_ = {"hi", "hello", "test", "a", "world"};
    }

    std::unique_ptr<FilterOperator> filter_op_;
    std::vector<std::string> test_input_;
};

TEST_F(FilterOperatorTest, BasicFiltering) {
    std::vector<std::string> output;
    
    EXPECT_TRUE(filter_op_->process(test_input_, output));
    
    // 应该过滤出长度大于3的字符串
    EXPECT_EQ(output.size(), 3);
    EXPECT_THAT(output, testing::Contains("hello"));
    EXPECT_THAT(output, testing::Contains("test"));
    EXPECT_THAT(output, testing::Contains("world"));
    EXPECT_THAT(output, testing::Not(testing::Contains("hi")));
    EXPECT_THAT(output, testing::Not(testing::Contains("a")));
}

TEST_F(FilterOperatorTest, NoMatchesFilter) {
    // 创建一个永远返回false的过滤器
    auto reject_all = [](const std::string&) { return false; };
    FilterOperator reject_filter(reject_all);
    
    std::vector<std::string> output;
    EXPECT_TRUE(reject_filter.process(test_input_, output));
    EXPECT_TRUE(output.empty());
}

// AggregateOperator 测试套件
class AggregateOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建一个连接所有字符串的聚合函数
        auto concat_func = [](const std::vector<std::string>& input) {
            std::string result;
            for (size_t i = 0; i < input.size(); ++i) {
                if (i > 0) result += ",";
                result += input[i];
            }
            return result;
        };
        
        agg_op_ = std::make_unique<AggregateOperator>(concat_func);
        test_input_ = {"apple", "banana", "cherry"};
    }

    std::unique_ptr<AggregateOperator> agg_op_;
    std::vector<std::string> test_input_;
};

TEST_F(AggregateOperatorTest, BasicAggregation) {
    std::vector<std::string> output;
    
    EXPECT_TRUE(agg_op_->process(test_input_, output));
    EXPECT_EQ(output.size(), 1);
    EXPECT_EQ(output[0], "apple,banana,cherry");
}

TEST_F(AggregateOperatorTest, EmptyInput) {
    std::vector<std::string> empty_input;
    std::vector<std::string> output;
    
    EXPECT_TRUE(agg_op_->process(empty_input, output));
    EXPECT_TRUE(output.empty());
}

// SourceOperator 测试套件
class SourceOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        source_data_ = {"item1", "item2", "item3"};
        source_op_ = std::make_unique<SourceOperator>(source_data_);
    }

    std::vector<std::string> source_data_;
    std::unique_ptr<SourceOperator> source_op_;
};

TEST_F(SourceOperatorTest, DataGeneration) {
    std::vector<std::string> dummy_input;
    std::vector<std::string> output;
    
    // 读取所有数据
    for (size_t i = 0; i < source_data_.size(); ++i) {
        EXPECT_TRUE(source_op_->has_more_data());
        EXPECT_TRUE(source_op_->process(dummy_input, output));
        EXPECT_EQ(output.size(), 1);
        EXPECT_EQ(output[0], source_data_[i]);
    }
    
    // 数据耗尽后应该返回false
    EXPECT_FALSE(source_op_->has_more_data());
    EXPECT_FALSE(source_op_->process(dummy_input, output));
}

TEST_F(SourceOperatorTest, Reset) {
    std::vector<std::string> dummy_input;
    std::vector<std::string> output;
    
    // 读取一些数据
    source_op_->process(dummy_input, output);
    source_op_->process(dummy_input, output);
    
    // 重置并验证可以重新读取
    source_op_->reset();
    EXPECT_TRUE(source_op_->has_more_data());
    
    EXPECT_TRUE(source_op_->process(dummy_input, output));
    EXPECT_EQ(output[0], source_data_[0]);
}

// SinkOperator 测试套件
class SinkOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        sink_op_ = std::make_unique<SinkOperator>();
        test_input_ = {"data1", "data2", "data3"};
    }

    std::unique_ptr<SinkOperator> sink_op_;
    std::vector<std::string> test_input_;
};

TEST_F(SinkOperatorTest, DataCollection) {
    std::vector<std::string> output;
    
    EXPECT_TRUE(sink_op_->process(test_input_, output));
    EXPECT_TRUE(output.empty()); // Sink 不产生输出
    
    // 验证数据被收集
    const auto& collected = sink_op_->get_collected_data();
    EXPECT_EQ(collected.size(), test_input_.size());
    EXPECT_EQ(collected, test_input_);
}

TEST_F(SinkOperatorTest, MultipleBatches) {
    std::vector<std::string> output;
    std::vector<std::string> batch1 = {"a", "b"};
    std::vector<std::string> batch2 = {"c", "d"};
    
    sink_op_->process(batch1, output);
    sink_op_->process(batch2, output);
    
    const auto& collected = sink_op_->get_collected_data();
    EXPECT_EQ(collected.size(), 4);
    EXPECT_EQ(collected[0], "a");
    EXPECT_EQ(collected[1], "b");
    EXPECT_EQ(collected[2], "c");
    EXPECT_EQ(collected[3], "d");
}

// JoinOperator 测试套件
class JoinOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建键提取函数（假设数据格式为 "key:value"）
        auto key_extractor = [](const std::string& data) {
            size_t pos = data.find(':');
            return (pos != std::string::npos) ? data.substr(0, pos) : data;
        };
        
        join_op_ = std::make_unique<JoinOperator>(key_extractor, key_extractor);
        
        left_data_ = {"1:apple", "2:banana", "3:cherry"};
        right_data_ = {"1:red", "2:yellow", "4:purple"};
        
        join_op_->set_left_data(left_data_);
        join_op_->set_right_data(right_data_);
    }

    std::unique_ptr<JoinOperator> join_op_;
    std::vector<std::string> left_data_;
    std::vector<std::string> right_data_;
};

TEST_F(JoinOperatorTest, InnerJoin) {
    std::vector<std::string> dummy_input;
    std::vector<std::string> output;
    
    EXPECT_TRUE(join_op_->process(dummy_input, output));
    
    // 应该有两个匹配的连接结果
    EXPECT_EQ(output.size(), 2);
    EXPECT_THAT(output, testing::Contains("1:apple+1:red"));
    EXPECT_THAT(output, testing::Contains("2:banana+2:yellow"));
    EXPECT_THAT(output, testing::Not(testing::Contains("3:cherry")));
    EXPECT_THAT(output, testing::Not(testing::Contains("4:purple")));
}

// 操作符链测试
class OperatorChainTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 设置测试数据
        source_data_ = {"hello world", "test data", "a", "example text"};
        
        // 创建操作符链: Source -> Filter -> Map -> Sink
        source_op_ = std::make_unique<SourceOperator>(source_data_);
        
        // 过滤长度大于5的字符串
        auto length_filter = [](const std::string& s) { return s.length() > 5; };
        filter_op_ = std::make_unique<FilterOperator>(length_filter);
        
        // 转换为大写
        auto uppercase_map = [](const std::string& s) {
            std::string result = s;
            std::transform(result.begin(), result.end(), result.begin(), ::toupper);
            return result;
        };
        map_op_ = std::make_unique<MapOperator>(uppercase_map);
        
        sink_op_ = std::make_unique<SinkOperator>();
    }

    std::vector<std::string> source_data_;
    std::unique_ptr<SourceOperator> source_op_;
    std::unique_ptr<FilterOperator> filter_op_;
    std::unique_ptr<MapOperator> map_op_;
    std::unique_ptr<SinkOperator> sink_op_;
};

TEST_F(OperatorChainTest, FullPipeline) {
    std::vector<std::string> temp_output;
    std::vector<std::string> dummy_input;
    
    // 处理所有源数据
    while (source_op_->has_more_data()) {
        // Source -> 临时输出
        source_op_->process(dummy_input, temp_output);
        
        // Filter -> 临时输出
        std::vector<std::string> filtered_output;
        filter_op_->process(temp_output, filtered_output);
        
        // Map -> 临时输出
        std::vector<std::string> mapped_output;
        map_op_->process(filtered_output, mapped_output);
        
        // Sink
        sink_op_->process(mapped_output, temp_output);
    }
    
    // 验证最终结果
    const auto& final_result = sink_op_->get_collected_data();
    
    // 应该有3个结果（过滤掉了"a"）
    EXPECT_EQ(final_result.size(), 3);
    EXPECT_THAT(final_result, testing::Contains("HELLO WORLD"));
    EXPECT_THAT(final_result, testing::Contains("TEST DATA"));
    EXPECT_THAT(final_result, testing::Contains("EXAMPLE TEXT"));
    EXPECT_THAT(final_result, testing::Not(testing::Contains("A")));
}

// 性能测试
class OperatorPerformanceTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建大量测试数据
        large_dataset_.reserve(10000);
        for (int i = 0; i < 10000; ++i) {
            large_dataset_.push_back("item_" + std::to_string(i));
        }
    }

    std::vector<std::string> large_dataset_;
};

TEST_F(OperatorPerformanceTest, LargeDatasetProcessing) {
    // 创建操作符
    auto passthrough_map = [](const std::string& s) { return s; };
    MapOperator map_op(passthrough_map);
    
    auto accept_all = [](const std::string&) { return true; };
    FilterOperator filter_op(accept_all);
    
    SinkOperator sink_op;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    // 处理大数据集
    std::vector<std::string> temp_output;
    
    map_op.process(large_dataset_, temp_output);
    filter_op.process(temp_output, temp_output);
    sink_op.process(temp_output, temp_output);
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // 性能基准：10000个项目应该在100ms内处理完成
    EXPECT_LT(duration.count(), 100);
    EXPECT_EQ(sink_op.get_collected_data().size(), large_dataset_.size());
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}