#include <pybind11/pybind11.h>

#include "environment/sage_flow_environment.hpp"
#include "data_stream/data_stream.hpp"
#include "message/multimodal_message.hpp"

namespace py = pybind11;

/**
 * @brief Bindings for SageFlowEnvironment as "Environment".
 * Exposure rules: Only Environment and supporting EnvironmentConfig are exposed.
 * No engine, operator, or internal classes are bound here.
 */
void bind_environment(py::module& m) {
    // Bind EnvironmentConfig - supporting class for Environment
    py::class_<sage_flow::EnvironmentConfig>(m, "EnvironmentConfig")
        .def(py::init<>(), "Create default environment config")
        .def(py::init<std::string>(), "Create environment config with job name")
        .def_readwrite("job_name", &sage_flow::EnvironmentConfig::job_name_)
        .def_readwrite("memory_config", &sage_flow::EnvironmentConfig::memory_config_)
        .def_readwrite("properties", &sage_flow::EnvironmentConfig::properties_);

    // Bind SageFlowEnvironment as "Environment" - allowed exposure
    py::class_<sage_flow::SageFlowEnvironment>(m, "Environment")
        .def(py::init<std::string>(), "Create environment with job name")
        .def(py::init<sage_flow::EnvironmentConfig>(), "Create environment with config")
        .def("set_memory", &sage_flow::SageFlowEnvironment::set_memory, "Set memory configuration")
        .def("set_property", &sage_flow::SageFlowEnvironment::set_property, "Set environment property")
        .def("get_property", &sage_flow::SageFlowEnvironment::get_property, "Get environment property")
        .def("get_job_name", &sage_flow::SageFlowEnvironment::get_job_name, "Get job name")
        .def("create_datastream", [](sage_flow::SageFlowEnvironment& self) -> sage_flow::Stream {
            return self.create_datastream();
        }, "Create a new DataStream")
        .def("get_config", &sage_flow::SageFlowEnvironment::get_config, "Get environment configuration")
        .def("is_ready", &sage_flow::SageFlowEnvironment::is_ready, "Check if environment is ready")
        .def("get_status", &sage_flow::SageFlowEnvironment::get_status, "Get environment status information")
        .def("submit", &sage_flow::SageFlowEnvironment::submit, "Submit job for execution")
        .def("close", &sage_flow::SageFlowEnvironment::close, "Close environment and cleanup");
}