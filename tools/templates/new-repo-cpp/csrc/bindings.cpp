// csrc/bindings.cpp — pybind11 entry point for my_pkg C++ extension
//
// Expose C++ classes / functions to Python here.
// Keep this file thin: delegate to submodules for each logical group.
//
// Example:
//   void bind_core(pybind11::module_& m);
//   void bind_algo(pybind11::module_& m);
//   PYBIND11_MODULE(_my_pkg_ext, m) { bind_core(m); bind_algo(m); }

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// ---------------------------------------------------------------------------
// Forward declarations (implemented in other .cpp files)
// ---------------------------------------------------------------------------
// void bind_core(py::module_& m);

// ---------------------------------------------------------------------------
// Module definition
// ---------------------------------------------------------------------------
PYBIND11_MODULE(_my_pkg_ext, m) {
    m.doc() = "my_pkg C++ extension — replace with real description";

    // bind_core(m);

    // Minimal smoke-test symbol
    m.def("version", []() { return "0.1.0"; }, "Return extension version string");
}
