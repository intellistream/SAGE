/**
 * @file filter_function_bindings.cpp
 * @brief Python bindings for FilterFunction
 *
 * This file provides Python bindings for the FilterFunction class only.
 * Exposure rules: Only FilterFunction is exposed with __init__ and execute.
 * No internal classes are bound here.
 */

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>

#include <functional>
#include <memory>

#include "function/filter_function.hpp"
#include "message/multimodal_message.hpp"
#include "function/function_response.hpp"

namespace py = pybind11;

void bind_filter_function(py::module& m) {
    using FilterFunc = std::function<bool(const sage_flow::MultiModalMessage&)>;
    using FilterFunction = sage_flow::FilterFunction;

    // Bind Response if not already
    py::class_<sage_flow::Response>(m, "Response")
        .def(py::init<>())
        .def("addMessage", [](sage_flow::Response& self, std::shared_ptr<sage_flow::MultiModalMessage> message) {
            self.addMessage(message);
        })
        .def("getMessages", [](const sage_flow::Response& self) -> py::list {
            py::list result;
            for (const auto& msg : self.getMessages()) {
                result.append(py::cast(msg));
            }
            return result;
        })
        .def("isEmpty", &sage_flow::Response::isEmpty)
        .def("clear", &sage_flow::Response::clear)
        .def("size", &sage_flow::Response::size);

    py::class_<FilterFunction>(m, "FilterFunction")
        .def(py::init<std::string>(), py::arg("name"))
        .def(py::init<std::string, FilterFunc>(), py::arg("name"), py::arg("filter_func"))
        .def("setFilterFunc", &FilterFunction::setFilterFunc, py::arg("filter_func"))
        .def("execute", [](FilterFunction& self, sage_flow::Response& response) -> sage_flow::Response {
            return self.execute(response);
        }, py::arg("response"))
        .def(py::init([](const std::string& name, py::function py_func) {
            FilterFunc filter_f = [py_func = std::move(py_func)](const sage_flow::MultiModalMessage& msg) -> bool {
                try {
                    py::gil_scoped_acquire acquire;
                    py::object py_msg = py::cast(msg);
                    return py_func(py_msg).cast<bool>();
                } catch (const py::error_already_set& e) {
                    py::print("Error in filter function: ", e.what());
                    return true; // Keep on error
                }
            };
            return new FilterFunction(name, std::move(filter_f));
        }), py::arg("name"), py::arg("py_func"), "Create FilterFunction from Python function");
}