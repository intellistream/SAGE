#include "sage_db/metadata_store.h"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <mutex>
#include <set>

namespace sage_db {

MetadataStore::MetadataStore() = default;

void MetadataStore::set_metadata(VectorId id, const Metadata& metadata) {
    validate_metadata(metadata);
    std::unique_lock<std::shared_mutex> lock(mutex_);
    metadata_map_[id] = metadata;
}

bool MetadataStore::get_metadata(VectorId id, Metadata& metadata) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    auto it = metadata_map_.find(id);
    if (it != metadata_map_.end()) {
        metadata = it->second;
        return true;
    }
    return false;
}

bool MetadataStore::has_metadata(VectorId id) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    return metadata_map_.find(id) != metadata_map_.end();
}

bool MetadataStore::remove_metadata(VectorId id) {
    std::unique_lock<std::shared_mutex> lock(mutex_);
    return metadata_map_.erase(id) > 0;
}

void MetadataStore::set_batch_metadata(const std::vector<VectorId>& ids, 
                                      const std::vector<Metadata>& metadata) {
    if (ids.size() != metadata.size()) {
        throw SageDBException("IDs and metadata vectors must have the same size");
    }
    
    for (const auto& meta : metadata) {
        validate_metadata(meta);
    }
    
    std::unique_lock<std::shared_mutex> lock(mutex_);
    for (size_t i = 0; i < ids.size(); ++i) {
        metadata_map_[ids[i]] = metadata[i];
    }
}

std::vector<Metadata> MetadataStore::get_batch_metadata(const std::vector<VectorId>& ids) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    std::vector<Metadata> result;
    result.reserve(ids.size());
    
    for (VectorId id : ids) {
        auto it = metadata_map_.find(id);
        if (it != metadata_map_.end()) {
            result.push_back(it->second);
        } else {
            result.push_back(Metadata{}); // Empty metadata for missing IDs
        }
    }
    
    return result;
}

std::vector<VectorId> MetadataStore::find_by_metadata(const std::string& key, 
                                                     const MetadataValue& value) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    std::vector<VectorId> result;
    
    for (const auto& pair : metadata_map_) {
        auto it = pair.second.find(key);
        if (it != pair.second.end() && it->second == value) {
            result.push_back(pair.first);
        }
    }
    
    return result;
}

std::vector<VectorId> MetadataStore::find_by_metadata_prefix(const std::string& key, 
                                                            const std::string& prefix) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    std::vector<VectorId> result;
    
    for (const auto& pair : metadata_map_) {
        auto it = pair.second.find(key);
        if (it != pair.second.end() && 
            it->second.substr(0, prefix.length()) == prefix) {
            result.push_back(pair.first);
        }
    }
    
    return result;
}

std::vector<VectorId> MetadataStore::filter_ids(const std::vector<VectorId>& ids,
                                               const std::function<bool(const Metadata&)>& filter) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    std::vector<VectorId> result;
    
    for (VectorId id : ids) {
        auto it = metadata_map_.find(id);
        if (it != metadata_map_.end() && filter(it->second)) {
            result.push_back(id);
        }
    }
    
    return result;
}

size_t MetadataStore::size() const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    return metadata_map_.size();
}

std::vector<std::string> MetadataStore::get_all_keys() const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    std::set<std::string> keys_set;
    
    for (const auto& pair : metadata_map_) {
        for (const auto& meta_pair : pair.second) {
            keys_set.insert(meta_pair.first);
        }
    }
    
    return std::vector<std::string>(keys_set.begin(), keys_set.end());
}

void MetadataStore::save(const std::string& filepath) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    std::ofstream file(filepath);
    
    if (!file.is_open()) {
        throw SageDBException("Cannot open file for writing: " + filepath);
    }
    
    // Simple JSON-like format
    file << "{\n";
    bool first = true;
    for (const auto& pair : metadata_map_) {
        if (!first) file << ",\n";
        first = false;

        file << "  \"" << pair.first << "\": {\n";
        bool first_meta = true;
        for (const auto& meta_pair : pair.second) {
            if (!first_meta) file << ",\n";
            first_meta = false;
            file << "    \"" << meta_pair.first << "\": \"" << meta_pair.second << "\"";
        }
        file << "\n  }";
    }
    file << "\n}\n";
}

void MetadataStore::load(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        throw SageDBException("Cannot open file for reading: " + filepath);
    }

    std::unique_lock<std::shared_mutex> lock(mutex_);
    metadata_map_.clear();

    std::string line;
    VectorId current_id = 0;
    bool in_metadata = false;

    while (std::getline(file, line)) {
        // Remove leading and trailing whitespace
        line.erase(0, line.find_first_not_of(" \t"));
        line.erase(line.find_last_not_of(" \t") + 1);

        // Skip empty lines and standalone braces
        if (line.empty() || line == "{" || line == "}") {
            continue;
        }

        // Remove trailing comma
        if (line.back() == ',') {
            line.pop_back();
        }

        // Parse vector ID line (format: "123": {)
        if (line.find("\"") == 0 && line.find("\": {") != std::string::npos) {
            size_t start = 1;
            size_t end = line.find("\"", start);
            if (start < end) {
                current_id = std::stoull(line.substr(start, end - start));
                in_metadata = true;
                metadata_map_[current_id] = Metadata{};
            }
        }
        // Check for metadata section end
        else if (line == "}") {
            in_metadata = false;
        }
        // Parse metadata key-value pairs (format: "key": "value")
        else if (in_metadata && line.find("\"") == 0 && line.find("\": \"") != std::string::npos) {
            // Extract key
            size_t key_start = 1;
            size_t key_end = line.find("\"", key_start);
            if (key_start >= key_end) continue;

            std::string key = line.substr(key_start, key_end - key_start);

            // Extract value
            size_t value_marker_pos = line.find("\": \"", key_end);
            if (value_marker_pos == std::string::npos) continue;

            size_t value_start = value_marker_pos + 4; // Skip ": "
            size_t value_end = line.find("\"", value_start);
            if (value_start >= value_end) continue;

            std::string value = line.substr(value_start, value_end - value_start);

            metadata_map_[current_id][key] = value;
        }
    }
}

void MetadataStore::clear() {
    std::unique_lock<std::shared_mutex> lock(mutex_);
    metadata_map_.clear();
}

void MetadataStore::validate_metadata(const Metadata& metadata) const {
    // Check for reasonable metadata size
    if (metadata.size() > 1000) {
        throw SageDBException("Too many metadata fields (max 1000)");
    }
    
    for (const auto& pair : metadata) {
        if (pair.first.empty()) {
            throw SageDBException("Metadata key cannot be empty");
        }
        if (pair.first.length() > 256) {
            throw SageDBException("Metadata key too long (max 256 characters)");
        }
        if (pair.second.length() > 10000) {
            throw SageDBException("Metadata value too long (max 10000 characters)");
        }
    }
}

} // namespace sage_db
