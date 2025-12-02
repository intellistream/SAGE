// Copyright 2024-present the vsag project
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <limits>
#include <map>
#include <vector>

#include "fmt/format.h"
#include "iostream"
#include "vsag/dataset.h"
#include "vsag/vsag.h"

namespace py = pybind11;

using FloatArray = py::array_t<float, py::array::c_style | py::array::forcecast>;
using Int64Array = py::array_t<int64_t, py::array::c_style | py::array::forcecast>;

void
SetLoggerOff() {
    vsag::Options::Instance().logger()->SetLevel(vsag::Logger::Level::kOFF);
}

void
SetLoggerInfo() {
    vsag::Options::Instance().logger()->SetLevel(vsag::Logger::Level::kINFO);
}

void
SetLoggerDebug() {
    vsag::Options::Instance().logger()->SetLevel(vsag::Logger::Level::kDEBUG);
}

template <typename T>
static void
writeBinaryPOD(std::ostream& out, const T& podRef) {
    out.write((char*)&podRef, sizeof(T));
}

template <typename T>
static void
readBinaryPOD(std::istream& in, T& podRef) {
    in.read((char*)&podRef, sizeof(T));
}

struct SparseVectors {
    std::vector<vsag::SparseVector> sparse_vectors;
    uint32_t num_elements;
    uint32_t num_non_zeros;

    SparseVectors(uint32_t num_elements)
        : sparse_vectors(num_elements), num_elements(num_elements), num_non_zeros(0) {
    }
};

SparseVectors
BuildSparseVectorsFromCSR(py::array_t<uint32_t> index_pointers,
                          py::array_t<uint32_t> indices,
                          py::array_t<float> values) {
    auto buf_ptr = index_pointers.request();
    auto buf_idx = indices.request();
    auto buf_val = values.request();

    if (buf_ptr.ndim != 1 || buf_idx.ndim != 1 || buf_val.ndim != 1) {
        throw std::invalid_argument("all inputs must be 1-dimensional");
    }

    if (buf_ptr.shape[0] < 2) {
        throw std::invalid_argument("index_pointers length must be at least 2");
    }
    uint32_t num_elements = buf_ptr.shape[0] - 1;

    const uint32_t* ptr_data = index_pointers.data();
    const uint32_t* idx_data = indices.data();
    const float* val_data = values.data();

    uint32_t num_non_zeros = ptr_data[num_elements];

    if (static_cast<size_t>(num_non_zeros) != buf_idx.shape[0]) {
        throw std::invalid_argument(
            fmt::format("Size of 'indices'({}) must equal index_pointers[last]",
                        buf_idx.shape[0],
                        num_non_zeros));
    }
    if (static_cast<size_t>(num_non_zeros) != buf_val.shape[0]) {
        throw std::invalid_argument(
            fmt::format("Size of 'values'({}) must equal index_pointers[last]({})",
                        buf_val.shape[0],
                        num_non_zeros));
    }

    if (ptr_data[0] != 0) {
        throw std::invalid_argument("index_pointers[0] must be 0");
    }
    for (uint32_t i = 1; i <= num_elements; ++i) {
        if (ptr_data[i] < ptr_data[i - 1]) {
            throw std::invalid_argument(
                fmt::format("index_pointers[{}]({}) > index_pointers[{}]({})",
                            i - 1,
                            ptr_data[i - 1],
                            i,
                            ptr_data[i]));
        }
    }

    SparseVectors svs(num_elements);
    svs.num_non_zeros = num_non_zeros;

    for (uint32_t i = 0; i < num_elements; ++i) {
        uint32_t start = ptr_data[i];
        uint32_t end = ptr_data[i + 1];
        uint32_t len = end - start;

        svs.sparse_vectors[i].len_ = len;
        svs.sparse_vectors[i].ids_ = const_cast<uint32_t*>(idx_data + start);
        svs.sparse_vectors[i].vals_ = const_cast<float*>(val_data + start);
    }

    return svs;
}

class Index {
public:
    Index(std::string name, const std::string& parameters) {
        if (auto index = vsag::Factory::CreateIndex(name, parameters)) {
            index_ = index.value();
        } else {
            vsag::Error error_code = index.error();
            if (error_code.type == vsag::ErrorType::UNSUPPORTED_INDEX) {
                throw std::runtime_error("error type: UNSUPPORTED_INDEX");
            } else if (error_code.type == vsag::ErrorType::INVALID_ARGUMENT) {
                throw std::runtime_error("error type: invalid_parameter");
            } else {
                throw std::runtime_error("error type: unexpectedError");
            }
        }
    }

public:
    void
    Build(FloatArray vectors, Int64Array ids, size_t num_elements, size_t dim) {
        auto dataset = vsag::Dataset::Make();
        dataset->Owner(false)
            ->Dim(dim)
            ->NumElements(num_elements)
            ->Ids(ids.mutable_data())
            ->Float32Vectors(vectors.mutable_data());
        index_->Build(dataset);
    }

    void
    Add(FloatArray vectors, Int64Array ids, size_t num_elements, size_t dim) {
        auto dataset = vsag::Dataset::Make();
        dataset->Owner(false)
            ->Dim(dim)
            ->NumElements(num_elements)
            ->Ids(ids.mutable_data())
            ->Float32Vectors(vectors.mutable_data());
        auto add_result = index_->Add(dataset);
        if (!add_result.has_value()) {
            throw std::runtime_error(fmt::format("failed to add vectors: {}",
                                                 add_result.error().message));
        }
        if (!add_result.value().empty()) {
            throw std::runtime_error(
                fmt::format("{} ids failed to insert", add_result.value().size()));
        }
    }

    void
    Remove(Int64Array ids) {
        auto buf = ids.request();
        if (buf.ndim != 1) {
            throw std::invalid_argument("ids must be a 1-dimensional array");
        }
        auto* data = ids.mutable_data();
        for (py::ssize_t i = 0; i < buf.shape[0]; ++i) {
            auto remove_res = index_->Remove(data[i]);
            if (!remove_res.has_value()) {
                throw std::runtime_error(
                    fmt::format("failed to remove id {}: {}", data[i], remove_res.error().message));
            }
        }
    }

    void
    SparseBuild(py::array_t<uint32_t> index_pointers,
                py::array_t<uint32_t> indices,
                py::array_t<float> values,
                py::array_t<int64_t> ids) {
        auto batch = BuildSparseVectorsFromCSR(index_pointers, indices, values);

        auto buf_id = ids.request();
        if (buf_id.ndim != 1) {
            throw std::invalid_argument("all inputs must be 1-dimensional");
        }
        if (batch.num_elements != buf_id.shape[0]) {
            throw std::invalid_argument(
                fmt::format("Length of 'ids'({}) must match number of vectors({})",
                            buf_id.shape[0],
                            batch.num_elements));
        }

        auto dataset = vsag::Dataset::Make();
        dataset->Owner(false)
            ->NumElements(batch.num_elements)
            ->Ids(ids.data())
            ->SparseVectors(batch.sparse_vectors.data());

        index_->Build(dataset);
    }

    py::object
    KnnSearch(FloatArray vectors, size_t k, std::string& parameters) {
        auto buf = vectors.request();
        if (buf.ndim != 1 && buf.ndim != 2) {
            throw std::invalid_argument("vector must be 1d or 2d array");
        }

        size_t data_num = 1;
        size_t dim = static_cast<size_t>(buf.shape[0]);
        if (buf.ndim == 2) {
            data_num = static_cast<size_t>(buf.shape[0]);
            dim = static_cast<size_t>(buf.shape[1]);
        }

        auto query = vsag::Dataset::Make();
        query->NumElements(static_cast<int64_t>(data_num))
            ->Dim(static_cast<int64_t>(dim))
            ->Float32Vectors(static_cast<float*>(buf.ptr))
            ->Owner(false);

        py::array_t<int64_t> ids;
        py::array_t<float> dists;
        if (data_num == 1) {
            ids = py::array_t<int64_t>(k);
            dists = py::array_t<float>(k);
        } else {
            std::vector<py::ssize_t> shape = {
                static_cast<py::ssize_t>(data_num), static_cast<py::ssize_t>(k)};
            ids = py::array_t<int64_t>(shape);
            dists = py::array_t<float>(shape);
        }

        auto* ids_ptr = ids.mutable_data();
        auto* dists_ptr = dists.mutable_data();
        std::fill(ids_ptr, ids_ptr + static_cast<py::ssize_t>(data_num * k), int64_t{-1});
        std::fill(dists_ptr,
              dists_ptr + static_cast<py::ssize_t>(data_num * k),
                  std::numeric_limits<float>::infinity());

        if (auto result = index_->KnnSearch(query, k, parameters); result.has_value()) {
            auto dataset = result.value();
            auto vsag_ids = dataset->GetIds();
            auto vsag_distances = dataset->GetDistances();
            auto available_k = std::min(static_cast<size_t>(dataset->GetDim()), k);
            auto available_queries =
                std::min(static_cast<size_t>(dataset->GetNumElements()), data_num);

            for (size_t qi = 0; qi < available_queries; ++qi) {
                for (size_t kj = 0; kj < available_k; ++kj) {
                    size_t src_idx = qi * static_cast<size_t>(dataset->GetDim()) + kj;
                    size_t dst_idx = qi * k + kj;
                    ids_ptr[dst_idx] = vsag_ids[src_idx];
                    dists_ptr[dst_idx] = vsag_distances[src_idx];
                }
            }
        } else {
            throw std::runtime_error(result.error().message);
        }

        return py::make_tuple(ids, dists);
    }

    py::tuple
    SparseKnnSearch(py::array_t<uint32_t> index_pointers,
                    py::array_t<uint32_t> indices,
                    py::array_t<float> values,
                    uint32_t k,
                    const std::string& parameters) {
        auto batch = BuildSparseVectorsFromCSR(index_pointers, indices, values);

        std::vector<uint32_t> shape{batch.num_elements, k};
        auto res_ids = py::array_t<int64_t>(shape);
        auto res_dists = py::array_t<float>(shape);

        auto ids_view = res_ids.mutable_unchecked<2>();
        auto dists_view = res_dists.mutable_unchecked<2>();

        for (uint32_t i = 0; i < batch.num_elements; ++i) {
            auto query = vsag::Dataset::Make();
            query->Owner(false)->NumElements(1)->SparseVectors(batch.sparse_vectors.data() + i);

            auto result = index_->KnnSearch(query, k, parameters);
            if (result.has_value()) {
                for (uint32_t j = 0; j < k; ++j) {
                    if (j < result.value()->GetDim()) {
                        ids_view(i, j) = result.value()->GetIds()[j];
                        dists_view(i, j) = result.value()->GetDistances()[j];
                    }
                }
            }
        }

        return py::make_tuple(res_ids, res_dists);
    }

    py::object
    RangeSearch(py::array_t<float> point, float threshold, std::string& parameters) {
        auto query = vsag::Dataset::Make();
        size_t data_num = 1;
        query->NumElements(data_num)
            ->Dim(point.size())
            ->Float32Vectors(point.mutable_data())
            ->Owner(false);

        py::array_t<int64_t> labels;
        py::array_t<float> dists;
        if (auto result = index_->RangeSearch(query, threshold, parameters); result.has_value()) {
            auto ids = result.value()->GetIds();
            auto distances = result.value()->GetDistances();
            auto k = result.value()->GetDim();
            labels.resize({k});
            dists.resize({k});
            auto labels_data = labels.mutable_data();
            auto dists_data = dists.mutable_data();
            for (uint32_t i = 0; i < data_num * k; ++i) {
                labels_data[i] = ids[i];
                dists_data[i] = distances[i];
            }
        }

        return py::make_tuple(labels, dists);
    }

    void
    Save(const std::string& filename) {
        std::ofstream file(filename, std::ios::binary);
        index_->Serialize(file);
        file.close();
    }

    void
    Load(const std::string& filename) {
        std::ifstream file(filename, std::ios::binary);

        index_->Deserialize(file);
        file.close();
    }

private:
    std::shared_ptr<vsag::Index> index_;
};

PYBIND11_MODULE(_pyvsag, m) {
    m.def("set_logger_off", &SetLoggerOff, "SetLoggerOff");
    m.def("set_logger_info", &SetLoggerInfo, "SetLoggerInfo");
    m.def("set_logger_debug", &SetLoggerDebug, "SetLoggerDebug");
    py::class_<Index>(m, "Index")
        .def(py::init<std::string, std::string&>(), py::arg("name"), py::arg("parameters"))
           .def("build",
               &Index::Build,
               py::arg("vectors"),
               py::arg("ids"),
               py::arg("num_elements"),
               py::arg("dim"))
           .def("add",
               &Index::Add,
               py::arg("vectors"),
               py::arg("ids"),
               py::arg("num_elements"),
               py::arg("dim"))
        .def("build",
             &Index::SparseBuild,
             py::arg("index_pointers"),
             py::arg("indices"),
             py::arg("values"),
             py::arg("ids"))
        .def(
            "knn_search", &Index::KnnSearch, py::arg("vector"), py::arg("k"), py::arg("parameters"))
           .def("remove", &Index::Remove, py::arg("ids"))
        .def("knn_search",
             &Index::SparseKnnSearch,
             py::arg("index_pointers"),
             py::arg("indices"),
             py::arg("values"),
             py::arg("k"),
             py::arg("parameters"))
        .def("range_search",
             &Index::RangeSearch,
             py::arg("vector"),
             py::arg("threshold"),
             py::arg("parameters"))
        .def("save", &Index::Save, py::arg("filename"))
        .def("load", &Index::Load, py::arg("filename"));
}
