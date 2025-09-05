#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "operator/terminal_sink_operator.hpp"

namespace py = pybind11;

void BindTerminalSinkOperator(py::module& m) {
  // SinkFunction typedef binding
  m.def(
      "SinkFunction",
      [](const std::function<void(const sage_flow::MultiModalMessage&)>& func) {
        return func;
      },
      "Create a sink function for terminal output");

  // TerminalSinkOperator class binding
  py::class_<sage_flow::TerminalSinkOperator, sage_flow::BaseOperator>(
      m, "TerminalSinkOperator")
      .def(py::init<std::function<void(const sage_flow::MultiModalMessage&)>>(),
           "Create terminal sink operator with sink function")
      .def("process", &sage_flow::TerminalSinkOperator::process,
           "Process input record and send to terminal")
      .def("open", &sage_flow::TerminalSinkOperator::open,
           "Open terminal sink operator")
      .def("close", &sage_flow::TerminalSinkOperator::close,
           "Close terminal sink operator");

  // Factory function binding
  m.def("CreateTerminalSink", &sage_flow::CreateTerminalSink,
        "Create terminal sink operator with sink function",
        py::arg("sink_func"));
}
