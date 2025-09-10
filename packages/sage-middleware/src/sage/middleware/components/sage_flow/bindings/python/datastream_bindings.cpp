/**
 * @file datastream_bindings.cpp
 * @brief Python bindings for DataStream (Stream<MultiModalMessage>)
 *
 * This file provides Python bindings for the DataStream class only.
 * Exposure rules: Only DataStream is exposed with fluent API methods.
 * No engine, operator, or internal classes are bound here.
 */

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>

#include <functional>
#include <memory>
#include <vector>
#include <string>

#include "../include/data_stream/data_stream.hpp"

namespace py = pybind11;

// Forward declaration
void bind_multimodal_message(py::module& m);

// Helper functions for Python to std::function conversion with GIL and error handling
std::function<std::shared_ptr<sage_flow::MultiModalMessage>(const std::shared_ptr<sage_flow::MultiModalMessage>&)> make_map_function(py::function f) {
    return [f = std::move(f)](const std::shared_ptr<sage_flow::MultiModalMessage>& input) -> std::shared_ptr<sage_flow::MultiModalMessage> {
        try {
            py::gil_scoped_acquire acquire;
            auto py_result = f(input);
            sage_flow::MultiModalMessage msg = py_result.cast<sage_flow::MultiModalMessage>();
            auto shared_msg = std::make_shared<sage_flow::MultiModalMessage>(msg.getUid(), msg.getContentType(), msg.getContent(), msg.getEmbeddings());
            return shared_msg;
        } catch (const py::error_already_set& e) {
            py::print("Error in map function: ", e.what());
            return input; // Return input on error for fluent
        }
    };
}

std::function<bool(const std::shared_ptr<sage_flow::MultiModalMessage>&)> make_filter_function(py::function f) {
    return [f = std::move(f)](const std::shared_ptr<sage_flow::MultiModalMessage>& input) -> bool {
        try {
            py::gil_scoped_acquire acquire;
            return f(input).cast<bool>();
        } catch (const py::error_already_set& e) {
            py::print("Error in filter function: ", e.what());
            return true; // Keep input on error
        }
    };
}

std::function<void(const sage_flow::MultiModalMessage&)> make_sink_function(py::function f) {
    return [f = std::move(f)](const sage_flow::MultiModalMessage& input) {
        try {
            py::gil_scoped_acquire acquire;
            f(input);
        } catch (const py::error_already_set& e) {
            py::print("Error in sink function: ", e.what());
        }
    };
}

void bind_datastream(py::module& m) {
    py::class_<sage_flow::Stream>(m, "DataStream")
        .def_static("from_vector", [](const py::list& py_list) -> sage_flow::Stream {
            std::vector<sage_flow::MultiModalMessage> vec;
            for (auto item : py_list) {
                vec.emplace_back(item.cast<sage_flow::MultiModalMessage>());
            }
            return sage_flow::Stream::from_vector(vec);
        }, py::arg("data"), "Create DataStream from list of MultiModalMessage")
        .def("map", [](sage_flow::Stream& self, py::function f) -> sage_flow::Stream {
            auto std_f = make_map_function(f);
            return self.map(std_f);
        }, py::arg("func"), "Apply map transformation using Python function")
        .def("filter", [](sage_flow::Stream& self, py::function f) -> sage_flow::Stream {
            auto std_f = make_filter_function(f);
            return self.filter(std_f);
        }, py::arg("func"), "Apply filter using Python function")
        .def("source", &sage_flow::Stream::source, "Add source operator")
        .def("sink", [](sage_flow::Stream& self, py::function f) {
            auto std_f = make_sink_function(f);
            self.sink(std_f);
        }, py::arg("func"), "Add sink using Python function")
        .def("execute", &sage_flow::Stream::execute, "Execute the stream")
        .def("collect", [](sage_flow::Stream& self) -> py::list {
            // Placeholder for collect - return empty list
            py::list result;
            return result;
        }, "Collect results as list (placeholder)");
}

// Main module - call all binds
PYBIND11_MODULE(sageflow, m) {
    m.doc() = "SAGE Flow Python bindings - main module";

    bind_multimodal_message(m);
    bind_datastream(m);
    // Other bind functions called from their respective files via CMake inclusion
}
