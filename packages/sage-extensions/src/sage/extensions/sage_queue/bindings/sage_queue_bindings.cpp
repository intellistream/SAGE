#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "ring_buffer.h"

namespace py = pybind11;

PYBIND11_MODULE(sage_queue_bindings, m) {
    m.doc() = "SAGE Queue - High-performance memory-mapped queue";
    
    // Add version info
    m.attr("__version__") = "1.0.0";
    
    // TODO: Add actual bindings here when ring_buffer.h has C++ classes
    // For now, this is a placeholder that can be extended
    
    m.def("get_version", []() {
        return "1.0.0";
    }, "Get the version of sage_queue");
}
