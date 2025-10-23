/**
 * @file multimodal_demo.cpp
 * @brief Demonstration of the multimodal data fusion algorithm module
 *
 * This example shows how to use the modular multimodal data fusion system
 * with different fusion strategies that can be plugged in dynamically.
 */

#include "sage_db/multimodal_sage_db.h"
#include "sage_db/fusion_strategies.h"
#include <iostream>
#include <memory>
#include <random>

using namespace sage_db;

// Helper function to generate random embeddings for demo
Vector generate_random_embedding(size_t dimension, std::mt19937& gen) {
    std::uniform_real_distribution<float> dist(-1.0f, 1.0f);
    Vector embedding(dimension);
    for (size_t i = 0; i < dimension; ++i) {
        embedding[i] = dist(gen);
    }
    return embedding;
}

int main() {
    std::cout << "🎯 SAGE DB - Multimodal Data Fusion Demo\n";
    std::cout << "==========================================\n\n";

    try {
        // Initialize random generator
        std::mt19937 gen(42);

        // 1. Configure database
        DatabaseConfig base_config;
        base_config.dimension = 256;  // Base embedding dimension (will be fused to this size)
        base_config.index_type = IndexType::FLAT;
        base_config.metric = DistanceMetric::L2;

        // Create a text-image multimodal database using factory
        auto db = MultimodalSageDBFactory::create_text_image_db(base_config);

        std::cout << "✅ Created multimodal database with text-image configuration\n\n";

        // 2. Demonstrate different fusion strategies
        std::cout << "🔧 Available fusion strategies:\n";
        auto strategies = db->get_supported_fusion_strategies();
        for (auto strategy : strategies) {
            std::cout << "   - " << static_cast<int>(strategy) << "\n";
        }
        std::cout << "\n";

        // 3. Add multimodal data
        std::cout << "📥 Adding multimodal data samples...\n";

        for (int i = 0; i < 5; ++i) {
            MultimodalData data;

            // Create text modality
            ModalData text_data;
            text_data.type = ModalityType::TEXT;
            text_data.embedding = generate_random_embedding(128, gen);  // Text embedding
            text_data.metadata["content"] = "Sample text " + std::to_string(i);
            text_data.metadata["length"] = std::to_string(10 + i * 5);

            // Create image modality
            ModalData image_data;
            image_data.type = ModalityType::IMAGE;
            image_data.embedding = generate_random_embedding(128, gen);  // Image embedding
            image_data.metadata["filename"] = "image_" + std::to_string(i) + ".jpg";
            image_data.metadata["width"] = "1024";
            image_data.metadata["height"] = "768";

            // Combine modalities
            data.modalities[ModalityType::TEXT] = text_data;
            data.modalities[ModalityType::IMAGE] = image_data;
            data.global_metadata["sample_id"] = std::to_string(i);
            data.global_metadata["source"] = "demo";

            VectorId id = db->add_multimodal(data);
            std::cout << "   ✓ Added sample " << i << " with ID: " << id << "\n";
        }
        std::cout << "\n";

        // 4. Demonstrate dynamic fusion strategy switching
        std::cout << "🔄 Testing different fusion strategies...\n";

        // Test 1: Weighted Average Fusion
        FusionParams weighted_params;
        weighted_params.strategy = FusionStrategy::WEIGHTED_AVERAGE;
        weighted_params.modality_weights[ModalityType::TEXT] = 0.7f;
        weighted_params.modality_weights[ModalityType::IMAGE] = 0.3f;
        weighted_params.target_dimension = 256;  // 确保目标维度正确
        db->update_fusion_params(weighted_params);

        std::cout << "   📊 Using Weighted Average Fusion (Text: 0.7, Image: 0.3)\n";

        // Test 2: Concatenation Fusion
        FusionParams concat_params;
        concat_params.strategy = FusionStrategy::CONCATENATION;
        concat_params.target_dimension = 256;  // Combine 128+128 = 256

        // Register custom concatenation strategy if needed
        auto concat_strategy = FusionStrategyFactory::create_concatenation_fusion();
        db->register_fusion_strategy(FusionStrategy::CONCATENATION, concat_strategy);

        std::cout << "   🔗 Registered Concatenation Fusion Strategy\n";

        // 5. Perform multimodal search
        std::cout << "\n🔍 Performing multimodal search...\n";

        // Create query data
        std::unordered_map<ModalityType, ModalData> query_modalities;

        ModalData query_text;
        query_text.type = ModalityType::TEXT;
        query_text.embedding = generate_random_embedding(128, gen);
        query_modalities[ModalityType::TEXT] = query_text;

        ModalData query_image;
        query_image.type = ModalityType::IMAGE;
        query_image.embedding = generate_random_embedding(128, gen);
        query_modalities[ModalityType::IMAGE] = query_image;

        MultimodalSearchParams search_params;
        search_params.k = 3;
        search_params.include_metadata = true;
        search_params.target_modalities = {ModalityType::TEXT, ModalityType::IMAGE};
        search_params.query_fusion_params = weighted_params;

        auto results = db->search_multimodal(query_modalities, search_params);

        std::cout << "   📊 Found " << results.size() << " similar items:\n";
        for (size_t i = 0; i < results.size(); ++i) {
            const auto& result = results[i];
            std::cout << "   " << (i+1) << ". ID: " << result.id
                     << ", Score: " << result.score;
            if (result.metadata.count("sample_id")) {
                std::cout << ", Sample: " << result.metadata.at("sample_id");
            }
            std::cout << "\n";
        }

        // 6. Demonstrate modular design - switching fusion algorithms
        std::cout << "\n🔧 Demonstrating modular fusion algorithm switching...\n";

        // Switch to Attention-based fusion
        FusionParams attention_params;
        attention_params.strategy = FusionStrategy::ATTENTION_BASED;
        attention_params.target_dimension = 256;  // 确保目标维度正确

        auto attention_strategy = FusionStrategyFactory::create_attention_based_fusion();
        db->register_fusion_strategy(FusionStrategy::ATTENTION_BASED, attention_strategy);
        db->update_fusion_params(attention_params);

        std::cout << "   🎯 Switched to Attention-based Fusion\n";

        // Add more data with new fusion strategy
        MultimodalData new_data;

        ModalData text_modal;
        text_modal.type = ModalityType::TEXT;
        text_modal.embedding = generate_random_embedding(128, gen);
        text_modal.metadata["content"] = "attention_test";
        new_data.modalities[ModalityType::TEXT] = text_modal;

        ModalData image_modal;
        image_modal.type = ModalityType::IMAGE;
        image_modal.embedding = generate_random_embedding(128, gen);
        image_modal.metadata["filename"] = "attention_test.jpg";
        new_data.modalities[ModalityType::IMAGE] = image_modal;

        new_data.global_metadata["fusion_type"] = "attention";

        VectorId attention_id = db->add_multimodal(new_data);
        std::cout << "   ✓ Added data with attention fusion, ID: " << attention_id << "\n";

        // 7. Show database statistics
        std::cout << "\n📈 Database Statistics:\n";
        std::cout << "   - Supported modalities: " << db->get_supported_modalities().size() << "\n";
        std::cout << "   - Supported fusion strategies: " << db->get_supported_fusion_strategies().size() << "\n";
        std::cout << "   - Current fusion strategy: "
                  << static_cast<int>(db->get_fusion_params().strategy) << "\n";

        std::cout << "\n🎉 Demo completed successfully!\n";
        std::cout << "\n💡 Key Features Demonstrated:\n";
        std::cout << "   ✓ Modular fusion algorithm design - easily plug in new strategies\n";
        std::cout << "   ✓ Dynamic strategy switching at runtime\n";
        std::cout << "   ✓ Multiple modality support (text, image, audio, video)\n";
        std::cout << "   ✓ Configurable fusion parameters\n";
        std::cout << "   ✓ Factory pattern for specialized database configurations\n";
        std::cout << "   ✓ Comprehensive metadata support\n";

    } catch (const std::exception& e) {
        std::cerr << "❌ Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}