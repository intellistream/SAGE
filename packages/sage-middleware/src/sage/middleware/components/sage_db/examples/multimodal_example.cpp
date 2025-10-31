#include "sage_db/multimodal_sage_db.h"
#include "sage_db/fusion_strategies.h"
#include <iostream>
#include <vector>
#include <random>
#include <numeric>

using namespace sage_db;

// 简单的文本模态处理器示例
class SimpleTextProcessor : public ModalityProcessor {
public:
    Vector process(const std::vector<uint8_t>& raw_data) override {
        // 简单的文本嵌入：随机向量
        std::mt19937 gen(raw_data.size());
        std::normal_distribution<float> dist(0.0f, 1.0f);

        Vector embedding(768); // BERT维度
        for (float& val : embedding) {
            val = dist(gen);
        }

        return embedding;
    }

    bool validate(const std::vector<uint8_t>& raw_data) const override {
        return !raw_data.empty();
    }

    ModalityType get_type() const override {
        return ModalityType::TEXT;
    }
};

// 简单的图像模态处理器示例
class SimpleImageProcessor : public ModalityProcessor {
public:
    Vector process(const std::vector<uint8_t>& raw_data) override {
        // 简单的图像嵌入：随机向量
        std::mt19937 gen(raw_data.size() * 2);
        std::normal_distribution<float> dist(0.0f, 1.0f);

        Vector embedding(2048); // ResNet维度
        for (float& val : embedding) {
            val = dist(gen);
        }

        return embedding;
    }

    bool validate(const std::vector<uint8_t>& raw_data) const override {
        return raw_data.size() > 10; // 简单验证
    }

    ModalityType get_type() const override {
        return ModalityType::IMAGE;
    }
};

// 自定义融合策略示例
class CustomWeightedFusion : public FusionStrategyInterface {
public:
    Vector fuse(const std::unordered_map<ModalityType, Vector>& modal_embeddings,
               const FusionParams& params) override {

        // 获取目标维度
        uint32_t target_dim = params.target_dimension > 0 ? params.target_dimension : 512;
        Vector result(target_dim, 0.0f);

        float text_weight = 0.7f;
        float image_weight = 0.3f;

        auto text_it = modal_embeddings.find(ModalityType::TEXT);
        auto image_it = modal_embeddings.find(ModalityType::IMAGE);

        if (text_it != modal_embeddings.end()) {
            Vector aligned = sage_db::fusion_utils::align_dimension(text_it->second, target_dim);
            for (size_t i = 0; i < target_dim; ++i) {
                result[i] += text_weight * aligned[i];
            }
        }

        if (image_it != modal_embeddings.end()) {
            Vector aligned = sage_db::fusion_utils::align_dimension(image_it->second, target_dim);
            for (size_t i = 0; i < target_dim; ++i) {
                result[i] += image_weight * aligned[i];
            }
        }

        return result;
    }

    FusionStrategy get_strategy_type() const override {
        return FusionStrategy::CUSTOM;
    }
};

int main() {
    std::cout << "=== SAGE DB 多模态融合算法示例 ===" << std::endl;

    try {
        // 1. 创建数据库配置
        DatabaseConfig base_config;
        base_config.dimension = 512;
        base_config.index_type = IndexType::FLAT;

        // 创建多模态数据库
        auto db = MultimodalSageDBFactory::create_text_image_db(base_config);
        std::cout << "✓ 创建多模态数据库成功" << std::endl;

        // 2. 注册自定义模态处理器
        db->register_modality_processor(ModalityType::TEXT,
                                       std::make_shared<SimpleTextProcessor>());
        db->register_modality_processor(ModalityType::IMAGE,
                                       std::make_shared<SimpleImageProcessor>());
        std::cout << "✓ 注册模态处理器成功" << std::endl;

        // 3. 注册自定义融合策略
        db->register_fusion_strategy(FusionStrategy::CUSTOM,
                                     std::make_shared<CustomWeightedFusion>());
        std::cout << "✓ 注册自定义融合策略成功" << std::endl;

        // 4. 准备多模态数据
        std::vector<uint8_t> text_data = {'H', 'e', 'l', 'l', 'o', ' ', 'W', 'o', 'r', 'l', 'd'};
        std::vector<uint8_t> image_data(1000, 0xFF); // 模拟图像数据

        // 创建模态数据
        Vector text_embedding(768);
        std::iota(text_embedding.begin(), text_embedding.end(), 0.1f);

        Vector image_embedding(2048);
        std::iota(image_embedding.begin(), image_embedding.end(), 0.2f);

        ModalData text_modal(ModalityType::TEXT, text_embedding);
        text_modal.metadata["language"] = "en";
        text_modal.raw_data = text_data;

        ModalData image_modal(ModalityType::IMAGE, image_embedding);
        image_modal.metadata["format"] = "jpg";
        image_modal.raw_data = image_data;

        // 5. 添加多模态数据
        std::unordered_map<ModalityType, ModalData> modalities;
        modalities[ModalityType::TEXT] = text_modal;
        modalities[ModalityType::IMAGE] = image_modal;

        Metadata global_metadata;
        global_metadata["category"] = "example";
        global_metadata["timestamp"] = "2024-01-01";

        VectorId id = db->add_multimodal(modalities, global_metadata);
        std::cout << "✓ 添加多模态数据成功，ID: " << id << std::endl;

        // 6. 测试多模态查询
        std::unordered_map<ModalityType, ModalData> query_modalities;

        Vector query_text(768);
        std::fill(query_text.begin(), query_text.end(), 0.15f);
        query_modalities[ModalityType::TEXT] = ModalData(ModalityType::TEXT, query_text);

        MultimodalSearchParams search_params(5);
        auto results = db->search_multimodal(query_modalities, search_params);

        std::cout << "✓ 多模态查询成功，结果数量: " << results.size() << std::endl;
        for (size_t i = 0; i < results.size(); ++i) {
            std::cout << "  结果 " << (i+1) << ": ID=" << results[i].id
                     << ", Score=" << results[i].score << std::endl;
        }

        // 7. 测试不同的融合策略
        std::cout << "\n=== 测试不同融合策略 ===" << std::endl;

        std::vector<FusionStrategy> strategies = {
            FusionStrategy::CONCATENATION,
            FusionStrategy::WEIGHTED_AVERAGE,
            FusionStrategy::ATTENTION_BASED,
            FusionStrategy::TENSOR_FUSION
        };

        for (auto strategy : strategies) {
            FusionParams params;
            params.strategy = strategy;
            params.target_dimension = 512;

            db->update_fusion_params(params);

            VectorId test_id = db->add_multimodal(modalities, global_metadata);
            std::cout << "✓ 策略 " << static_cast<int>(strategy)
                     << " 测试成功，ID: " << test_id << std::endl;
        }

        // 8. 显示支持的模态和策略
        auto supported_modalities = db->get_supported_modalities();
        auto supported_strategies = db->get_supported_fusion_strategies();

        std::cout << "\n=== 系统信息 ===" << std::endl;
        std::cout << "支持的模态类型数量: " << supported_modalities.size() << std::endl;
        std::cout << "支持的融合策略数量: " << supported_strategies.size() << std::endl;

        std::cout << "\n✅ 所有测试通过！" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "❌ 错误: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
