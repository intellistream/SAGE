/**
 * @file map_function_bindings.cpp
 * @brief Python bindings for MapFunction<MultiModalMessage,MultiModalMessage,std::function>
 *
 * This file provides Python bindings for the MapFunction class only.
 * Exposure rules: Only MapFunction is exposed with __init__ and execute.
 * No internal classes are bound here.
 */

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>

#include <functional>
#include <memory>

#include "function/map_function.hpp"
#include "message/multimodal_message.hpp"

namespace py = pybind11;

void bind_map_function(py::module& m) {
    using MapFunc = std::function<void(std::unique_ptr<sage_flow::MultiModalMessage>&)>;
    using MapFunction = sage_flow::MapFunction;

    // Bind Response first
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

    py::class_<MapFunction>(m, "MapFunction")
        .def(py::init<std::string>(), py::arg("name"))
        .def(py::init<std::string, MapFunc>(), py::arg("name"), py::arg("map_func"))
        .def("setMapFunc", &MapFunction::setMapFunc, py::arg("map_func"))
        .def("execute", [](MapFunction& self, py::object py_response) -> py::object {
            // Convert py_response to Response
            sage_flow::Response response;
            // Placeholder for conversion
            return py::cast(self.execute(response));
        }, py::arg("response"))
        .def(py::init([](const std::string& name, py::function py_func) {
            MapFunc map_f = [py_func = std::move(py_func)](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
                try {
                    py::gil_scoped_acquire acquire;
                    py::object py_msg = py::cast(msg.get());
                    py_func(py_msg);
                } catch (const py::error_already_set& e) {
                    py::print("Error in map function: ", e.what());
                }
            };
            return new MapFunction(name, std::move(map_f));
        }), py::arg("name"), py::arg("py_func"), "Create MapFunction from Python function");
}