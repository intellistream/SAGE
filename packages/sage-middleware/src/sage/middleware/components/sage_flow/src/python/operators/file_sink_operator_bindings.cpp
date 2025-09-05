#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "operator/file_sink_operator.hpp"

namespace py = pybind11;

void BindFileSinkOperator(py::module& m) {
  // FileFormat enum binding
  py::enum_<sage_flow::FileFormat>(m, "FileFormat")
      .value("TEXT", sage_flow::FileFormat::TEXT)
      .value("JSON", sage_flow::FileFormat::JSON)
      .value("CSV", sage_flow::FileFormat::CSV);

  // FileSinkConfig struct binding
  py::class_<sage_flow::FileSinkConfig>(m, "FileSinkConfig")
      .def(py::init<>())
      .def_readwrite("format", &sage_flow::FileSinkConfig::format_)
      .def_readwrite("append_mode", &sage_flow::FileSinkConfig::append_mode_)
      .def_readwrite("batch_size", &sage_flow::FileSinkConfig::batch_size_)
      .def_readwrite("header", &sage_flow::FileSinkConfig::header_);

  // FileSinkOperator class binding
  py::class_<sage_flow::FileSinkOperator, sage_flow::BaseOperator>(
      m, "FileSinkOperator")
      .def(py::init<std::string, sage_flow::FileSinkConfig>(),
           "Create file sink operator with path and config")
      .def("process", &sage_flow::FileSinkOperator::process,
           "Process input record and write to file")
      .def("open", &sage_flow::FileSinkOperator::open,
           "Open file sink operator")
      .def("close", &sage_flow::FileSinkOperator::close,
           "Close file sink operator")
      .def("get_message_count", &sage_flow::FileSinkOperator::getMessageCount,
           "Get total number of messages written to file");

  // Factory function binding
  m.def("CreateFileSink", &sage_flow::CreateFileSink,
        "Create file sink operator with path, format, and append mode",
        py::arg("file_path"), py::arg("format") = sage_flow::FileFormat::TEXT,
        py::arg("append_mode") = false);
}
