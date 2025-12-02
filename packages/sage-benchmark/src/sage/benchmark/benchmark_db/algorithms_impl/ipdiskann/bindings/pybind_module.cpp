#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include "index_wrapper.h"

namespace py = pybind11;

PYBIND11_MODULE(ipdiskann, m) {
    py::class_<MyIndexWrapper>(m, "Index")
        .def(py::init<>())
        .def("setup", &MyIndexWrapper::setup,
             py::arg("max_points"), py::arg("dim"),
             py::arg("R") = 64, py::arg("L") = 100, py::arg("num_threads") = 1)
        .def("build", [](MyIndexWrapper& self,
                     py::array_t<float, py::array::c_style | py::array::forcecast> data,
                     size_t num_points,
                     const std::vector<uint32_t>& tags) {
            if (data.ndim() != 2)
                 std::runtime_error("build() expects a 2D array");

            const float* raw_data = static_cast<const float*>(data.data());
            self.build(raw_data, num_points, tags);
        }, py::arg("data"), py::arg("num_points"), py::arg("tags"))
        .def("query", [](MyIndexWrapper& self,
                     py::array_t<float, py::array::c_style | py::array::forcecast> q,
                     size_t K) {
            if (q.ndim() != 1)
                throw std::runtime_error("query() expects a 1D array");
            std::vector<uint32_t> tags;
            std::vector<float> dists;
            self.query(q.data(), K, tags, dists);
            return py::make_tuple(tags, dists);
        }, py::arg("query"), py::arg("K"))
        .def("batch_query", [](MyIndexWrapper& self,
                              py::array_t<float> queries,
                              size_t K,
                              int num_threads = 1) {
            if (queries.ndim() != 2)
                throw std::runtime_error("batch_query() expects a 2D array");

            size_t num_queries = queries.shape(0);
            size_t dim = queries.shape(1);

            std::vector<std::vector<uint32_t>> all_tags;
            std::vector<std::vector<float>> all_dists;

            self.batch_query(queries.data(), num_queries, dim, K,
                           all_tags, all_dists, num_threads);

            py::array_t<uint32_t> result_tags = py::array_t<uint32_t>(
                py::buffer_info(
                    nullptr,
                    sizeof(uint32_t),
                    py::format_descriptor<uint32_t>::format(),
                    2,
                    {num_queries, K},
                    {sizeof(uint32_t) * K, sizeof(uint32_t)}
                )
            );

            py::array_t<float> result_dists = py::array_t<float>(
                py::buffer_info(
                    nullptr,
                    sizeof(float),
                    py::format_descriptor<float>::format(),
                    2,
                    {num_queries, K},
                    {sizeof(float) * K, sizeof(float)}
                )
            );

            auto tags_ptr = static_cast<uint32_t*>(result_tags.mutable_unchecked<2>().mutable_data(0, 0));
            auto dists_ptr = static_cast<float*>(result_dists.mutable_unchecked<2>().mutable_data(0, 0));

            for (size_t i = 0; i < num_queries; ++i) {
                std::copy(all_tags[i].begin(), all_tags[i].end(), tags_ptr + i * K);
                std::copy(all_dists[i].begin(), all_dists[i].end(), dists_ptr + i * K);
            }

            return py::make_tuple(result_tags, result_dists);
        }, py::arg("queries"), py::arg("K"), py::arg("num_threads") = 1)
        .def("insert", [](MyIndexWrapper& self,
                      py::array_t<float, py::array::c_style | py::array::forcecast> point,
                      uint32_t tag) {
            if (point.ndim() != 1)
                throw std::runtime_error("insert(): point must be 1D array");

            try {
                return self.insert_point(point.data(), tag);
            } catch (const std::exception& e) {
                throw std::runtime_error(std::string("[C++ insert exception] ") + e.what());
            } catch (...) {
                throw std::runtime_error("[C++] Unknown exception in insert_point");
            }
        })
        .def("remove", &MyIndexWrapper::remove)
        .def("insert_concurrent", [](MyIndexWrapper& self,
                        py::array_t<float, py::array::c_style | py::array::forcecast> X,
                        py::array_t<uint32_t, py::array::c_style | py::array::forcecast> tags,
                        int32_t thread_count = -1) {

        if (X.ndim() != 2)
            throw std::runtime_error("insert_concurrent(): X must be 2D array");
        if (tags.ndim() != 1)
            throw std::runtime_error("insert_concurrent(): tags must be 1D array");
        if (X.shape(0) != tags.shape(0))
            throw std::runtime_error("insert_concurrent(): number of points and tags must match");

        size_t num_points = X.shape(0);
        size_t dim = X.shape(1);

        try {
            auto results = self.insert_points_concurrent(
                X.data(),
                tags.data(),
                num_points,
                dim,
                thread_count
            );

            py::list py_results;
            for (bool result : results) {
                py_results.append(result);
            }
            return py_results;

        } catch (const std::exception& e) {
            throw std::runtime_error(std::string("[C++ concurrent insert exception] ") + e.what());
        } catch (...) {
            throw std::runtime_error("[C++] Unknown exception in insert_concurrent");
        }
    }, py::arg("X"), py::arg("tags"), py::arg("thread_count") = -1);
}
