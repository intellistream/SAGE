#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <pybind11/functional.h>
#include "sage_db/sage_db.h"

namespace py = pybind11;
using namespace sage_db;

PYBIND11_MODULE(_sage_db, m) {
    m.doc() = "SAGE Database - High-performance vector database with FAISS backend";

    // Exceptions
    py::register_exception<SageDBException>(m, "SageDBException");

    // Enums
    py::enum_<IndexType>(m, "IndexType")
        .value("FLAT", IndexType::FLAT)
        .value("IVF_FLAT", IndexType::IVF_FLAT)
        .value("IVF_PQ", IndexType::IVF_PQ)
        .value("HNSW", IndexType::HNSW)
        .value("AUTO", IndexType::AUTO);

    py::enum_<DistanceMetric>(m, "DistanceMetric")
        .value("L2", DistanceMetric::L2)
        .value("INNER_PRODUCT", DistanceMetric::INNER_PRODUCT)
        .value("COSINE", DistanceMetric::COSINE);

    // QueryResult
    py::class_<QueryResult>(m, "QueryResult")
        .def(py::init<VectorId, Score, const Metadata&>(),
             py::arg("id"), py::arg("score"), py::arg("metadata") = Metadata{})
        .def_readwrite("id", &QueryResult::id)
        .def_readwrite("score", &QueryResult::score)
        .def_readwrite("metadata", &QueryResult::metadata)
        .def("__repr__", [](const QueryResult& r) {
            return "QueryResult(id=" + std::to_string(r.id) +
                   ", score=" + std::to_string(r.score) + ")";
        });

    // SearchParams
    py::class_<SearchParams>(m, "SearchParams")
        .def(py::init<>())
        .def(py::init<uint32_t>(), py::arg("k"))
        .def_readwrite("k", &SearchParams::k)
        .def_readwrite("nprobe", &SearchParams::nprobe)
        .def_readwrite("radius", &SearchParams::radius)
        .def_readwrite("include_metadata", &SearchParams::include_metadata);

    // DatabaseConfig
    py::class_<DatabaseConfig>(m, "DatabaseConfig")
        .def(py::init<>())
        .def(py::init<Dimension>(), py::arg("dimension"))
        .def_readwrite("index_type", &DatabaseConfig::index_type)
        .def_readwrite("metric", &DatabaseConfig::metric)
        .def_readwrite("dimension", &DatabaseConfig::dimension)
        .def_readwrite("nlist", &DatabaseConfig::nlist)
        .def_readwrite("m", &DatabaseConfig::m)
        .def_readwrite("nbits", &DatabaseConfig::nbits)
        .def_readwrite("M", &DatabaseConfig::M)
        .def_readwrite("efConstruction", &DatabaseConfig::efConstruction);

    // VectorStore
    py::class_<VectorStore>(m, "VectorStore")
        .def(py::init<const DatabaseConfig&>())
        .def("add_vector", &VectorStore::add_vector)
        .def("add_vectors", &VectorStore::add_vectors)
        .def("search", &VectorStore::search)
        .def("build_index", &VectorStore::build_index)
        .def("train_index", &VectorStore::train_index)
        .def("is_trained", &VectorStore::is_trained)
        .def("size", &VectorStore::size)
        .def("dimension", &VectorStore::dimension)
        .def("index_type", &VectorStore::index_type)
        .def("save", &VectorStore::save)
        .def("load", &VectorStore::load)
        .def("config", &VectorStore::config, py::return_value_policy::reference_internal);

    // MetadataStore
    py::class_<MetadataStore>(m, "MetadataStore")
        .def(py::init<>())
        .def("set_metadata", &MetadataStore::set_metadata)
        .def("get_metadata", [](const MetadataStore& store, VectorId id) {
            Metadata metadata;
            bool found = store.get_metadata(id, metadata);
            return found ? py::cast(metadata) : py::none();
        })
        .def("has_metadata", &MetadataStore::has_metadata)
        .def("remove_metadata", &MetadataStore::remove_metadata)
        .def("set_batch_metadata", &MetadataStore::set_batch_metadata)
        .def("get_batch_metadata", &MetadataStore::get_batch_metadata)
        .def("find_by_metadata", &MetadataStore::find_by_metadata)
        .def("find_by_metadata_prefix", &MetadataStore::find_by_metadata_prefix)
        .def("filter_ids", &MetadataStore::filter_ids)
        .def("size", &MetadataStore::size)
        .def("get_all_keys", &MetadataStore::get_all_keys)
        .def("save", &MetadataStore::save)
        .def("load", &MetadataStore::load)
        .def("clear", &MetadataStore::clear);

    // QueryEngine::SearchStats
    py::class_<QueryEngine::SearchStats>(m, "SearchStats")
        .def_readwrite("total_candidates", &QueryEngine::SearchStats::total_candidates)
        .def_readwrite("filtered_candidates", &QueryEngine::SearchStats::filtered_candidates)
        .def_readwrite("final_results", &QueryEngine::SearchStats::final_results)
        .def_readwrite("search_time_ms", &QueryEngine::SearchStats::search_time_ms)
        .def_readwrite("filter_time_ms", &QueryEngine::SearchStats::filter_time_ms)
        .def_readwrite("total_time_ms", &QueryEngine::SearchStats::total_time_ms);

    // QueryEngine
    py::class_<QueryEngine>(m, "QueryEngine")
        .def("search", &QueryEngine::search)
        .def("filtered_search", &QueryEngine::filtered_search)
        .def("search_with_metadata", &QueryEngine::search_with_metadata)
        .def("batch_search", &QueryEngine::batch_search)
        .def("batch_filtered_search", &QueryEngine::batch_filtered_search)
        .def("hybrid_search", &QueryEngine::hybrid_search,
             py::arg("query"), py::arg("params"), py::arg("text_query") = "",
             py::arg("vector_weight") = 0.7f, py::arg("text_weight") = 0.3f)
        .def("range_search", &QueryEngine::range_search,
             py::arg("query"), py::arg("radius"), py::arg("params") = SearchParams())
        .def("search_with_rerank", &QueryEngine::search_with_rerank,
             py::arg("query"), py::arg("params"), py::arg("rerank_fn"), py::arg("rerank_k") = 100)
        .def("get_last_search_stats", &QueryEngine::get_last_search_stats);

    // SageDB (main class)
    py::class_<SageDB>(m, "SageDB")
        .def(py::init<const DatabaseConfig&>())
        // 便捷构造函数
        .def(py::init([](Dimension dimension, IndexType index_type, DistanceMetric metric) {
            DatabaseConfig config;
            config.dimension = dimension;
            config.index_type = index_type;
            config.metric = metric;
            return std::make_unique<SageDB>(config);
        }), py::arg("dimension"), py::arg("index_type") = IndexType::AUTO, py::arg("metric") = DistanceMetric::L2)
        // Vector operations with GIL release for better multi-threading
        .def("add", [](SageDB& self, const Vector& vector, const Metadata& metadata) -> VectorId {
            // Release GIL during C++ computation
            py::gil_scoped_release release;
            VectorId id = self.add(vector, metadata);
            py::gil_scoped_acquire acquire;
            return id;
        }, py::arg("vector"), py::arg("metadata") = Metadata{},
           "Add a single vector with optional metadata. Thread-safe with GIL released.")

        .def("add_batch", [](SageDB& self, const std::vector<Vector>& vectors,
                            const std::vector<Metadata>& metadata) -> std::vector<VectorId> {
            // Release GIL for batch operations
            py::gil_scoped_release release;
            auto ids = self.add_batch(vectors, metadata);
            py::gil_scoped_acquire acquire;
            return ids;
        }, py::arg("vectors"), py::arg("metadata") = std::vector<Metadata>{},
           "Batch add vectors. GIL released for true parallelism.")

        .def("remove", [](SageDB& self, VectorId id) -> bool {
            py::gil_scoped_release release;
            bool result = self.remove(id);
            py::gil_scoped_acquire acquire;
            return result;
        })

        .def("update", [](SageDB& self, VectorId id, const Vector& vector,
                         const Metadata& metadata) -> bool {
            py::gil_scoped_release release;
            bool result = self.update(id, vector, metadata);
            py::gil_scoped_acquire acquire;
            return result;
        }, py::arg("id"), py::arg("vector"), py::arg("metadata") = Metadata{})

        // Search operations - GIL released for maximum parallelism
        .def("search", [](const SageDB& self, const Vector& query, uint32_t k,
                         bool include_metadata) -> std::vector<QueryResult> {
            // Release GIL - this is the key for multi-threaded search performance!
            py::gil_scoped_release release;
            auto results = self.search(query, k, include_metadata);
            py::gil_scoped_acquire acquire;
            return results;
        }, py::arg("query"), py::arg("k") = 10, py::arg("include_metadata") = true,
           R"pbdoc(
               Search for k nearest neighbors.

               This operation releases the GIL, allowing multiple Python threads
               to search concurrently with true parallelism. Performance scales
               linearly with the number of CPU cores.

               Args:
                   query: Query vector
                   k: Number of nearest neighbors to return
                   include_metadata: Whether to include metadata in results

               Returns:
                   List of QueryResult objects sorted by distance
           )pbdoc")

        .def("search", [](const SageDB& self, const Vector& query,
                         const SearchParams& params) -> std::vector<QueryResult> {
            py::gil_scoped_release release;
            auto results = self.search(query, params);
            py::gil_scoped_acquire acquire;
            return results;
        })

        .def("filtered_search", [](const SageDB& self, const Vector& query,
                                   const SearchParams& params,
                                   std::function<bool(const Metadata&)> filter) -> std::vector<QueryResult> {
            py::gil_scoped_release release;
            auto results = self.filtered_search(query, params, filter);
            py::gil_scoped_acquire acquire;
            return results;
        })

        .def("batch_search", [](const SageDB& self, const std::vector<Vector>& queries,
                               const SearchParams& params) -> std::vector<std::vector<QueryResult>> {
            // Batch search with GIL released - highest performance operation!
            py::gil_scoped_release release;
            auto results = self.batch_search(queries, params);
            py::gil_scoped_acquire acquire;
            return results;
        }, R"pbdoc(
               Batch search for maximum throughput.

               Processes multiple queries with GIL released. This is the highest
               performance search method - use it when you have multiple queries.

               Args:
                   queries: List of query vectors
                   params: Search parameters

               Returns:
                   List of result lists, one per query
           )pbdoc")

        // Index management operations with GIL release
        .def("build_index", [](SageDB& self) {
            py::gil_scoped_release release;
            self.build_index();
            py::gil_scoped_acquire acquire;
        }, "Build/rebuild the search index. GIL released during index construction.")

        .def("train_index", [](SageDB& self, const std::vector<Vector>& training_data) {
            py::gil_scoped_release release;
            self.train_index(training_data);
            py::gil_scoped_acquire acquire;
        }, py::arg("training_data") = std::vector<Vector>{},
           "Train the index (for algorithms that require training). GIL released.")

        .def("is_trained", &SageDB::is_trained)
        .def("set_metadata", &SageDB::set_metadata)
        .def("get_metadata", [](const SageDB& db, VectorId id) {
            Metadata metadata;
            bool found = db.get_metadata(id, metadata);
            return found ? py::cast(metadata) : py::none();
        })
        .def("find_by_metadata", &SageDB::find_by_metadata)
        .def("save", &SageDB::save)
        .def("load", &SageDB::load)
        .def("size", &SageDB::size)
        .def("dimension", &SageDB::dimension)
        .def("index_type", &SageDB::index_type)
        .def("config", &SageDB::config, py::return_value_policy::reference_internal)
        .def("query_engine", py::overload_cast<>(&SageDB::query_engine),
             py::return_value_policy::reference_internal)
        .def("vector_store", py::overload_cast<>(&SageDB::vector_store),
             py::return_value_policy::reference_internal)
        .def("metadata_store", py::overload_cast<>(&SageDB::metadata_store),
             py::return_value_policy::reference_internal);

    // Factory functions
    m.def("create_database", py::overload_cast<Dimension, IndexType, DistanceMetric>(&create_database),
          py::arg("dimension"), py::arg("index_type") = IndexType::AUTO,
          py::arg("metric") = DistanceMetric::L2,
          "Create a new SageDB instance with basic configuration");

    m.def("create_database", py::overload_cast<const DatabaseConfig&>(&create_database),
          py::arg("config"), "Create a new SageDB instance with custom configuration");

    // Utility functions
    m.def("index_type_to_string", &index_type_to_string);
    m.def("string_to_index_type", &string_to_index_type);
    m.def("distance_metric_to_string", &distance_metric_to_string);
    m.def("string_to_distance_metric", &string_to_distance_metric);

    // NumPy array support with GIL release
    m.def("add_numpy", [](SageDB& db, py::array_t<float> vectors, py::list metadata_list = py::list()) {
        py::buffer_info buf = vectors.request();

        if (buf.ndim != 2) {
            throw std::runtime_error("Input array must be 2-dimensional");
        }

        size_t num_vectors = buf.shape[0];
        size_t dimension = buf.shape[1];

        if (dimension != db.dimension()) {
            throw std::runtime_error("Vector dimension mismatch");
        }

        // Prepare data while holding GIL
        std::vector<Vector> vec_list;
        vec_list.reserve(num_vectors);

        float* ptr = static_cast<float*>(buf.ptr);
        for (size_t i = 0; i < num_vectors; ++i) {
            Vector vec(dimension);
            for (size_t j = 0; j < dimension; ++j) {
                vec[j] = ptr[i * dimension + j];
            }
            vec_list.push_back(vec);
        }

        std::vector<Metadata> meta_list;
        if (py::len(metadata_list) > 0) {
            if (py::len(metadata_list) != num_vectors) {
                throw std::runtime_error("Metadata list size must match number of vectors");
            }
            meta_list.reserve(num_vectors);
            for (auto item : metadata_list) {
                meta_list.push_back(item.cast<Metadata>());
            }
        }

        // Release GIL for batch insertion
        py::gil_scoped_release release;
        auto ids = db.add_batch(vec_list, meta_list);
        py::gil_scoped_acquire acquire;

        return ids;
    }, py::arg("db"), py::arg("vectors"), py::arg("metadata") = py::list(),
       "Add vectors from NumPy array. GIL released during insertion for parallelism.");

    m.def("search_numpy", [](const SageDB& db, py::array_t<float> query, const SearchParams& params) {
        py::buffer_info buf = query.request();

        if (buf.ndim != 1 || buf.shape[0] != db.dimension()) {
            throw std::runtime_error("Query vector dimension mismatch");
        }

        // Prepare query vector while holding GIL
        Vector query_vec(buf.shape[0]);
        float* ptr = static_cast<float*>(buf.ptr);
        for (size_t i = 0; i < buf.shape[0]; ++i) {
            query_vec[i] = ptr[i];
        }

        // Release GIL for search
        py::gil_scoped_release release;
        auto results = db.search(query_vec, params);
        py::gil_scoped_acquire acquire;

        return results;
    }, py::arg("db"), py::arg("query"), py::arg("params") = SearchParams(),
       "Search with NumPy query vector. GIL released for true multi-threaded search.");
}
