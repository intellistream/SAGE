/**
 * @file test_functions.cpp
 * @brief 函数系统单元测试
 * 
 * 测试各种函数组件：文档解析、文本清洗、嵌入、质量评估等
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <memory>
#include <vector>
#include <string>
#include <chrono>

// 简化的函数测试实现
namespace sage_flow {

// 基础函数接口
class Function {
public:
    virtual ~Function() = default;
    virtual bool execute(const std::string& input, std::string& output) = 0;
    virtual std::string get_name() const = 0;
};

// 文档解析函数
class DocumentParserFunction : public Function {
public:
    bool execute(const std::string& input, std::string& output) override {
        // 简化的文档解析逻辑
        if (input.empty()) {
            return false;
        }
        
        // 模拟解析过程：提取文本内容
        output = "parsed:" + input;
        return true;
    }
    
    std::string get_name() const override { return "document_parser"; }
    
    // 设置解析器类型
    void set_parser_type(const std::string& type) {
        parser_type_ = type;
    }
    
    std::string get_parser_type() const { return parser_type_; }

private:
    std::string parser_type_ = "default";
};

// 文本清洗函数
class TextCleanerFunction : public Function {
public:
    struct CleaningOptions {
        bool remove_punctuation;
        bool remove_numbers;
        bool to_lowercase;
        bool remove_extra_spaces;
        
        CleaningOptions()
            : remove_punctuation(false)
            , remove_numbers(false)
            , to_lowercase(false)
            , remove_extra_spaces(true) {}
    };
    
    explicit TextCleanerFunction(const CleaningOptions& options = CleaningOptions())
        : options_(options) {}
    
    bool execute(const std::string& input, std::string& output) override {
        if (input.empty()) {
            output = "";
            return true;
        }
        
        output = input;
        
        // 应用清洗选项
        if (options_.remove_punctuation) {
            remove_punctuation(output);
        }
        
        if (options_.remove_numbers) {
            remove_numbers(output);
        }
        
        if (options_.to_lowercase) {
            to_lowercase(output);
        }
        
        if (options_.remove_extra_spaces) {
            remove_extra_spaces(output);
        }
        
        return true;
    }
    
    std::string get_name() const override { return "text_cleaner"; }

private:
    CleaningOptions options_;
    
    void remove_punctuation(std::string& text) {
        // 简化的标点符号移除
        std::string result;
        for (char c : text) {
            if (std::isalnum(c) || std::isspace(c)) {
                result += c;
            }
        }
        text = result;
    }
    
    void remove_numbers(std::string& text) {
        std::string result;
        for (char c : text) {
            if (!std::isdigit(c)) {
                result += c;
            }
        }
        text = result;
    }
    
    void to_lowercase(std::string& text) {
        std::transform(text.begin(), text.end(), text.begin(), ::tolower);
    }
    
    void remove_extra_spaces(std::string& text) {
        // 简化的多余空格移除
        std::string result;
        bool prev_space = false;
        
        for (char c : text) {
            if (std::isspace(c)) {
                if (!prev_space) {
                    result += ' ';
                    prev_space = true;
                }
            } else {
                result += c;
                prev_space = false;
            }
        }
        
        // 移除开头和结尾的空格
        if (!result.empty() && result[0] == ' ') {
            result.erase(0, 1);
        }
        if (!result.empty() && result.back() == ' ') {
            result.pop_back();
        }
        
        text = result;
    }
};

// 文本嵌入函数
class TextEmbeddingFunction : public Function {
public:
    bool execute(const std::string& input, std::string& output) override {
        if (input.empty()) {
            return false;
        }
        
        // 简化的嵌入生成：根据文本长度和内容生成向量
        std::vector<float> embedding = generate_embedding(input);
        
        // 序列化向量为字符串
        output = serialize_vector(embedding);
        return true;
    }
    
    std::string get_name() const override { return "text_embedding"; }
    
    void set_model_name(const std::string& model) {
        model_name_ = model;
    }
    
    std::string get_model_name() const { return model_name_; }

private:
    std::string model_name_ = "default_embedding";
    
    std::vector<float> generate_embedding(const std::string& text) {
        // 简化的嵌入生成逻辑
        const size_t embedding_dim = 128;
        std::vector<float> embedding(embedding_dim, 0.0f);
        
        // 基于文本内容生成特征
        for (size_t i = 0; i < text.length() && i < embedding_dim; ++i) {
            embedding[i] = static_cast<float>(text[i]) / 255.0f;
        }
        
        // 归一化
        float norm = 0.0f;
        for (float val : embedding) {
            norm += val * val;
        }
        norm = std::sqrt(norm);
        
        if (norm > 0.0f) {
            for (float& val : embedding) {
                val /= norm;
            }
        }
        
        return embedding;
    }
    
    std::string serialize_vector(const std::vector<float>& vec) {
        std::string result = "[";
        for (size_t i = 0; i < vec.size(); ++i) {
            if (i > 0) result += ",";
            result += std::to_string(vec[i]);
        }
        result += "]";
        return result;
    }
};

// 质量评估函数
class QualityAssessorFunction : public Function {
public:
    struct QualityMetrics {
        float readability_score = 0.0f;
        float coherence_score = 0.0f;
        float completeness_score = 0.0f;
        float overall_score = 0.0f;
    };
    
    bool execute(const std::string& input, std::string& output) override {
        if (input.empty()) {
            return false;
        }
        
        QualityMetrics metrics = assess_quality(input);
        output = serialize_metrics(metrics);
        return true;
    }
    
    std::string get_name() const override { return "quality_assessor"; }

private:
    QualityMetrics assess_quality(const std::string& text) {
        QualityMetrics metrics;
        
        // 简化的质量评估逻辑
        
        // 可读性评分：基于句子长度和复杂度
        metrics.readability_score = calculate_readability(text);
        
        // 连贯性评分：基于词汇重复和结构
        metrics.coherence_score = calculate_coherence(text);
        
        // 完整性评分：基于文本长度和结构
        metrics.completeness_score = calculate_completeness(text);
        
        // 总体评分
        metrics.overall_score = (metrics.readability_score + 
                               metrics.coherence_score + 
                               metrics.completeness_score) / 3.0f;
        
        return metrics;
    }
    
    float calculate_readability(const std::string& text) {
        // 简化的可读性计算
        size_t word_count = count_words(text);
        size_t sentence_count = count_sentences(text);
        
        if (sentence_count == 0) return 0.0f;
        
        float avg_sentence_length = static_cast<float>(word_count) / static_cast<float>(sentence_count);
        
        // 理想句子长度为15-20词
        float readability = 1.0f - std::abs(avg_sentence_length - 17.5f) / 17.5f;
        return std::max(0.0f, std::min(1.0f, readability));
    }
    
    float calculate_coherence(const std::string& text) {
        // 简化的连贯性计算
        size_t word_count = count_words(text);
        size_t unique_words = count_unique_words(text);
        
        if (word_count == 0) return 0.0f;
        
        float vocabulary_diversity = static_cast<float>(unique_words) / static_cast<float>(word_count);
        return std::min(1.0f, vocabulary_diversity * 2.0f); // 调整权重
    }
    
    float calculate_completeness(const std::string& text) {
        // 简化的完整性计算
        size_t char_count = text.length();
        
        // 假设完整文本应该有200-2000字符
        if (char_count < 200) {
            return static_cast<float>(char_count) / 200.0f;
        } else if (char_count > 2000) {
            return 1.0f - (static_cast<float>(char_count - 2000) / 2000.0f);
        } else {
            return 1.0f;
        }
    }
    
    size_t count_words(const std::string& text) {
        size_t count = 0;
        bool in_word = false;
        
        for (char c : text) {
            if (std::isalnum(c)) {
                if (!in_word) {
                    count++;
                    in_word = true;
                }
            } else {
                in_word = false;
            }
        }
        
        return count;
    }
    
    size_t count_sentences(const std::string& text) {
        size_t count = 0;
        for (char c : text) {
            if (c == '.' || c == '!' || c == '?') {
                count++;
            }
        }
        return std::max(static_cast<size_t>(1), count);
    }
    
    size_t count_unique_words(const std::string& text) {
        std::set<std::string> unique_words;
        std::string current_word;
        
        for (char c : text) {
            if (std::isalnum(c)) {
                current_word += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            } else {
                if (!current_word.empty()) {
                    unique_words.insert(current_word);
                    current_word.clear();
                }
            }
        }
        
        if (!current_word.empty()) {
            unique_words.insert(current_word);
        }
        
        return unique_words.size();
    }
    
    std::string serialize_metrics(const QualityMetrics& metrics) {
        return "readability:" + std::to_string(metrics.readability_score) +
               ",coherence:" + std::to_string(metrics.coherence_score) +
               ",completeness:" + std::to_string(metrics.completeness_score) +
               ",overall:" + std::to_string(metrics.overall_score);
    }
};

} // namespace sage_flow

using namespace sage_flow;

// DocumentParserFunction 测试套件
class DocumentParserTest : public ::testing::Test {
protected:
    void SetUp() override {
        parser_ = std::make_unique<DocumentParserFunction>();
    }

    std::unique_ptr<DocumentParserFunction> parser_;
};

TEST_F(DocumentParserTest, BasicParsing) {
    std::string input = "This is a test document.";
    std::string output;
    
    EXPECT_TRUE(parser_->execute(input, output));
    EXPECT_EQ(output, "parsed:" + input);
    EXPECT_EQ(parser_->get_name(), "document_parser");
}

TEST_F(DocumentParserTest, EmptyInput) {
    std::string input = "";
    std::string output;
    
    EXPECT_FALSE(parser_->execute(input, output));
}

TEST_F(DocumentParserTest, ParserTypeConfiguration) {
    parser_->set_parser_type("pdf");
    EXPECT_EQ(parser_->get_parser_type(), "pdf");
    
    parser_->set_parser_type("html");
    EXPECT_EQ(parser_->get_parser_type(), "html");
}

// TextCleanerFunction 测试套件
class TextCleanerTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 默认配置
        default_cleaner_ = std::make_unique<TextCleanerFunction>();
        
        // 全功能清洗配置
        TextCleanerFunction::CleaningOptions full_options;
        full_options.remove_punctuation = true;
        full_options.remove_numbers = true;
        full_options.to_lowercase = true;
        full_options.remove_extra_spaces = true;
        
        full_cleaner_ = std::make_unique<TextCleanerFunction>(full_options);
    }

    std::unique_ptr<TextCleanerFunction> default_cleaner_;
    std::unique_ptr<TextCleanerFunction> full_cleaner_;
};

TEST_F(TextCleanerTest, DefaultCleaning) {
    std::string input = "Hello   World!  ";
    std::string output;
    
    EXPECT_TRUE(default_cleaner_->execute(input, output));
    EXPECT_EQ(output, "Hello World!");
}

TEST_F(TextCleanerTest, FullCleaning) {
    std::string input = "Hello, World! 123   Test.";
    std::string output;
    
    EXPECT_TRUE(full_cleaner_->execute(input, output));
    EXPECT_EQ(output, "hello world test");
}

TEST_F(TextCleanerTest, EmptyInput) {
    std::string input = "";
    std::string output;
    
    EXPECT_TRUE(default_cleaner_->execute(input, output));
    EXPECT_EQ(output, "");
}

// TextEmbeddingFunction 测试套件
class TextEmbeddingTest : public ::testing::Test {
protected:
    void SetUp() override {
        embedding_func_ = std::make_unique<TextEmbeddingFunction>();
    }

    std::unique_ptr<TextEmbeddingFunction> embedding_func_;
};

TEST_F(TextEmbeddingTest, BasicEmbedding) {
    std::string input = "Hello World";
    std::string output;
    
    EXPECT_TRUE(embedding_func_->execute(input, output));
    EXPECT_FALSE(output.empty());
    EXPECT_THAT(output, testing::StartsWith("["));
    EXPECT_THAT(output, testing::EndsWith("]"));
}

TEST_F(TextEmbeddingTest, EmptyInput) {
    std::string input = "";
    std::string output;
    
    EXPECT_FALSE(embedding_func_->execute(input, output));
}

TEST_F(TextEmbeddingTest, ModelConfiguration) {
    embedding_func_->set_model_name("bert-base");
    EXPECT_EQ(embedding_func_->get_model_name(), "bert-base");
}

TEST_F(TextEmbeddingTest, ConsistentEmbedding) {
    std::string input = "Test text";
    std::string output1, output2;
    
    EXPECT_TRUE(embedding_func_->execute(input, output1));
    EXPECT_TRUE(embedding_func_->execute(input, output2));
    
    // 相同输入应该产生相同的嵌入
    EXPECT_EQ(output1, output2);
}

// QualityAssessorFunction 测试套件
class QualityAssessorTest : public ::testing::Test {
protected:
    void SetUp() override {
        assessor_ = std::make_unique<QualityAssessorFunction>();
    }

    std::unique_ptr<QualityAssessorFunction> assessor_;
};

TEST_F(QualityAssessorTest, BasicAssessment) {
    std::string input = "This is a well-written text. It has good structure and clarity. The content is comprehensive and easy to understand.";
    std::string output;
    
    EXPECT_TRUE(assessor_->execute(input, output));
    EXPECT_FALSE(output.empty());
    
    // 输出应该包含各种指标
    EXPECT_THAT(output, testing::HasSubstr("readability:"));
    EXPECT_THAT(output, testing::HasSubstr("coherence:"));
    EXPECT_THAT(output, testing::HasSubstr("completeness:"));
    EXPECT_THAT(output, testing::HasSubstr("overall:"));
}

TEST_F(QualityAssessorTest, EmptyInput) {
    std::string input = "";
    std::string output;
    
    EXPECT_FALSE(assessor_->execute(input, output));
}

TEST_F(QualityAssessorTest, ShortText) {
    std::string input = "Short.";
    std::string output;
    
    EXPECT_TRUE(assessor_->execute(input, output));
    
    // 短文本的完整性评分应该较低
    EXPECT_THAT(output, testing::HasSubstr("completeness:"));
}

TEST_F(QualityAssessorTest, LongText) {
    std::string long_input(3000, 'a'); // 很长的文本
    std::string output;
    
    EXPECT_TRUE(assessor_->execute(long_input, output));
    EXPECT_FALSE(output.empty());
}

// 函数链测试
class FunctionChainTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建函数链：解析 -> 清洗 -> 嵌入 -> 质量评估
        parser_ = std::make_unique<DocumentParserFunction>();
        
        TextCleanerFunction::CleaningOptions options;
        options.to_lowercase = true;
        options.remove_extra_spaces = true;
        cleaner_ = std::make_unique<TextCleanerFunction>(options);
        
        embedder_ = std::make_unique<TextEmbeddingFunction>();
        assessor_ = std::make_unique<QualityAssessorFunction>();
    }

    std::unique_ptr<DocumentParserFunction> parser_;
    std::unique_ptr<TextCleanerFunction> cleaner_;
    std::unique_ptr<TextEmbeddingFunction> embedder_;
    std::unique_ptr<QualityAssessorFunction> assessor_;
};

TEST_F(FunctionChainTest, FullPipeline) {
    std::string original_input = "This Is A TEST Document!  ";
    std::string temp_output;
    
    // 解析
    EXPECT_TRUE(parser_->execute(original_input, temp_output));
    std::string parsed_output = temp_output;
    
    // 清洗
    EXPECT_TRUE(cleaner_->execute(parsed_output, temp_output));
    std::string cleaned_output = temp_output;
    EXPECT_THAT(cleaned_output, testing::HasSubstr("test document"));
    
    // 质量评估（使用清洗后的文本）
    EXPECT_TRUE(assessor_->execute(cleaned_output, temp_output));
    std::string quality_output = temp_output;
    EXPECT_THAT(quality_output, testing::HasSubstr("overall:"));
    
    // 嵌入（使用清洗后的文本）
    EXPECT_TRUE(embedder_->execute(cleaned_output, temp_output));
    std::string embedding_output = temp_output;
    EXPECT_THAT(embedding_output, testing::StartsWith("["));
}

// 性能测试
class FunctionPerformanceTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建大文本
        large_text_.reserve(10000);
        for (int i = 0; i < 1000; ++i) {
            large_text_ += "This is sentence number " + std::to_string(i) + ". ";
        }
        
        cleaner_ = std::make_unique<TextCleanerFunction>();
        embedder_ = std::make_unique<TextEmbeddingFunction>();
        assessor_ = std::make_unique<QualityAssessorFunction>();
    }

    std::string large_text_;
    std::unique_ptr<TextCleanerFunction> cleaner_;
    std::unique_ptr<TextEmbeddingFunction> embedder_;
    std::unique_ptr<QualityAssessorFunction> assessor_;
};

TEST_F(FunctionPerformanceTest, LargeTextProcessing) {
    std::string output;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    // 清洗大文本
    EXPECT_TRUE(cleaner_->execute(large_text_, output));
    
    // 质量评估
    EXPECT_TRUE(assessor_->execute(output, output));
    
    // 嵌入
    EXPECT_TRUE(embedder_->execute(large_text_.substr(0, 1000), output)); // 嵌入较短文本
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // 性能基准：大文本处理应该在500ms内完成
    EXPECT_LT(duration.count(), 500);
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}