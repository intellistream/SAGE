#pragma once

#include "common.h"
#include <unordered_map>
#include <shared_mutex>
#include <functional>
#include <functional>

namespace sage_db {

class MetadataStore {
public:
    MetadataStore();
    ~MetadataStore() = default;

    // Basic operations
    void set_metadata(VectorId id, const Metadata& metadata);
    bool get_metadata(VectorId id, Metadata& metadata) const;
    bool has_metadata(VectorId id) const;
    bool remove_metadata(VectorId id);
    
    // Batch operations
    void set_batch_metadata(const std::vector<VectorId>& ids, 
                           const std::vector<Metadata>& metadata);
    std::vector<Metadata> get_batch_metadata(const std::vector<VectorId>& ids) const;
    
    // Search by metadata
    std::vector<VectorId> find_by_metadata(const std::string& key, 
                                          const MetadataValue& value) const;
    std::vector<VectorId> find_by_metadata_prefix(const std::string& key, 
                                                  const std::string& prefix) const;
    
    // Filtering
    std::vector<VectorId> filter_ids(const std::vector<VectorId>& ids,
                                    const std::function<bool(const Metadata&)>& filter) const;
    
    // Statistics
    size_t size() const;
    std::vector<std::string> get_all_keys() const;
    
    // Persistence
    void save(const std::string& filepath) const;
    void load(const std::string& filepath);
    
    // Clear all data
    void clear();
    
private:
    std::unordered_map<VectorId, Metadata> metadata_map_;
    mutable std::shared_mutex mutex_;
    
    // Helper methods
    void validate_metadata(const Metadata& metadata) const;
};

} // namespace sage_db
