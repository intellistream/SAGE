/**
 * @file index_function_bindings.cpp
 * @brief Python bindings for BruteForceIndex as IndexFunction
 *
 * This file provides Python bindings for the BruteForceIndex class only.
 * Exposure rules: Only IndexFunction (BruteForceIndex) is exposed with add_vector and search_kNN.
 * No internal classes or operators are bound here.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <memory>
#include <vector>
#include <utility>

#include "index/brute_force_index.hpp"
#include "memory/memory_pool.hpp"

namespace py = pybind11;

void bind_index_function(py::module& m) {
    py::class_<sage_flow::BruteForceIndex>(m, "IndexFunction")
        .def(py::init<>(), "Create default BruteForceIndex")
        .def("add_vector", [](sage_flow::BruteForceIndex& self, py::list py_list) -> int {
            std::vector<double> vec;
            for (auto item : py_list) {
                vec.push_back(item.cast<double>());
            }
            return self.add_vector(vec);
        }, py::arg("vector"), "Add vector as list of doubles")
        .def("search_kNN", [](const sage_flow::BruteForceIndex& self, py::list py_query, int k) -> py::dict {
            std::vector<double> query;
            for (auto item : py_query) {
                query.push_back(item.cast<double>());
            }
            auto results = self.search_kNN(query, k);
            py::dict dict;
            for (const auto& p : results) {
                dict[py::cast(p.first)] = p.second;
            }
            return dict;
        }, py::arg("query"), py::arg("k"), "Search kNN, return dict of index:distance");
}