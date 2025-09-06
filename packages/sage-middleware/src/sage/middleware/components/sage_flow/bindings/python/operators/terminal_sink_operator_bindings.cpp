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

  // TerminalSinkOperator class binding with modern process signature
  py::class_<sage_flow::TerminalSinkOperator, sage_flow::BaseOperator<sage_flow::MultiModalMessage, bool>>(
      m, "TerminalSinkOperator")
      .def(py::init<std::function<void(const sage_flow::MultiModalMessage&)>>(),
           "Create terminal sink operator with sink function")
      .def("process", [](sage_flow::TerminalSinkOperator& op, py::list input_list) -> py::object {
          std::vector<std::shared_ptr<sage_flow::MultiModalMessage>> input;
          for (auto item : input_list) {
              input.push_back(item.cast<std::shared_ptr<sage_flow::MultiModalMessage>>());
          }
          auto result = op.process(input);
          if (result) {
              return py::cast(result.value());
          }
          return py::none();
      }, py::arg("in"), "Process input batch and send to terminal", py::return_value_policy::automatic)
      .def("open", &sage_flow::TerminalSinkOperator::open,
           "Open terminal sink operator")
      .def("close", &sage_flow::TerminalSinkOperator::close,
           "Close terminal sink operator");

  // Factory function binding
  m.def("CreateTerminalSink", &sage_flow::CreateTerminalSink,
        "Create terminal sink operator with sink function",
        py::arg("sink_func"));
}
