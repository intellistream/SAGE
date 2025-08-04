#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <pybind11/functional.h>
#include "../include/simple_boost_queue.h"

namespace py = pybind11;

PYBIND11_MODULE(sage_queue_bindings, m) {
    m.doc() = "SAGE Queue - High-performance memory-mapped queue with Boost IPC";
    
    // Add version info
    m.attr("__version__") = "1.0.0";
    
    // Bind RingBufferStats structure
    py::class_<RingBufferStats>(m, "RingBufferStats")
        .def_readonly("buffer_size", &RingBufferStats::buffer_size)
        .def_readonly("available_read", &RingBufferStats::available_read)
        .def_readonly("available_write", &RingBufferStats::available_write)
        .def_readonly("readers", &RingBufferStats::readers)
        .def_readonly("writers", &RingBufferStats::writers)
        .def_readonly("ref_count", &RingBufferStats::ref_count)
        .def_readonly("total_bytes_written", &RingBufferStats::total_bytes_written)
        .def_readonly("total_bytes_read", &RingBufferStats::total_bytes_read)
        .def_readonly("utilization", &RingBufferStats::utilization);
    
    // Bind RingBufferRef structure
    py::class_<RingBufferRef>(m, "RingBufferRef")
        .def_property_readonly("name", [](const RingBufferRef& ref) {
            return std::string(ref.name);
        })
        .def_readonly("size", &RingBufferRef::size)
        .def_readonly("auto_cleanup", &RingBufferRef::auto_cleanup)
        .def_readonly("creator_pid", &RingBufferRef::creator_pid);
    
    // Bind SimpleBoostQueue class
    py::class_<SimpleBoostQueue>(m, "SimpleBoostQueue")
        .def(py::init<const std::string&, uint32_t>(), 
             py::arg("name"), py::arg("size"),
             "Create a new shared memory queue")
        .def("put", [](SimpleBoostQueue& queue, const py::bytes& data, double timeout_sec) {
            std::string str_data = data;
            return queue.put(str_data.c_str(), str_data.size(), timeout_sec);
        }, py::arg("data"), py::arg("timeout_sec") = -1.0,
           "Put data into the queue")
        .def("get", [](SimpleBoostQueue& queue, double timeout_sec) -> py::object {
            char buffer[65536]; // 64KB buffer
            uint32_t buffer_size = sizeof(buffer);
            if (queue.get(buffer, &buffer_size, timeout_sec)) {
                return py::bytes(buffer, buffer_size);
            }
            return py::none();
        }, py::arg("timeout_sec") = -1.0,
           "Get data from the queue")
        .def("peek", [](SimpleBoostQueue& queue) -> py::object {
            char buffer[65536]; // 64KB buffer  
            uint32_t buffer_size = sizeof(buffer);
            if (queue.peek(buffer, &buffer_size)) {
                return py::bytes(buffer, buffer_size);
            }
            return py::none();
        }, "Peek at data in the queue without removing it")
        .def("is_empty", &SimpleBoostQueue::is_empty)
        .def("is_full", &SimpleBoostQueue::is_full)
        .def("available_read", &SimpleBoostQueue::available_read)
        .def("available_write", &SimpleBoostQueue::available_write)
        .def("size_limit", &SimpleBoostQueue::size_limit)
        .def("close", &SimpleBoostQueue::close)
        .def("get_stats", &SimpleBoostQueue::get_stats)
        .def_readonly("name", &SimpleBoostQueue::name)
        .def_readonly("ref_count", &SimpleBoostQueue::ref_count)
        .def_readonly("total_bytes_written", &SimpleBoostQueue::total_bytes_written)
        .def_readonly("total_bytes_read", &SimpleBoostQueue::total_bytes_read);
    
    // Bind C interface functions for backward compatibility
    m.def("ring_buffer_create", &ring_buffer_create, 
          py::arg("size"), py::return_value_policy::take_ownership,
          "Create a ring buffer with given size");
    
    m.def("ring_buffer_create_named", &ring_buffer_create_named,
          py::arg("name"), py::arg("size"), py::return_value_policy::take_ownership,
          "Create a named ring buffer");
    
    m.def("ring_buffer_open", &ring_buffer_open,
          py::arg("name"), py::return_value_policy::take_ownership,
          "Open an existing named ring buffer");
    
    m.def("ring_buffer_destroy", &ring_buffer_destroy,
          py::arg("rb"), "Destroy a ring buffer");
    
    m.def("ring_buffer_destroy_named", &ring_buffer_destroy_named,
          py::arg("name"), "Destroy a named ring buffer");
    
    m.def("ring_buffer_put", [](RingBufferStruct* rb, const py::bytes& data, double timeout_sec) {
        std::string str_data = data;
        return ring_buffer_put(rb, str_data.c_str(), str_data.size(), timeout_sec);
    }, py::arg("rb"), py::arg("data"), py::arg("timeout_sec"),
       "Put data into ring buffer");
    
    m.def("ring_buffer_get", [](RingBufferStruct* rb, double timeout_sec) -> py::object {
        char buffer[65536];
        uint32_t buffer_size = sizeof(buffer);
        int result = ring_buffer_get(rb, buffer, &buffer_size, timeout_sec);
        if (result == 1) {
            return py::bytes(buffer, buffer_size);
        }
        return py::none();
    }, py::arg("rb"), py::arg("timeout_sec"),
       "Get data from ring buffer");
    
    // Additional utility functions
    m.def("ring_buffer_is_empty", &ring_buffer_is_empty);
    m.def("ring_buffer_is_full", &ring_buffer_is_full);
    m.def("ring_buffer_available_read", &ring_buffer_available_read);
    m.def("ring_buffer_available_write", &ring_buffer_available_write);
    m.def("ring_buffer_size_limit", &ring_buffer_size_limit);
    m.def("ring_buffer_close", &ring_buffer_close);
    m.def("ring_buffer_get_stats", &ring_buffer_get_stats);
    
    m.def("get_version", []() {
        return "1.0.0";
    }, "Get the version of sage_queue");
}
