//
// Created by tony on 12/04/24.
//
// Modified: Isolated PyTorch dependency from Python bindings
// - Removed torch/extension.h dependency
// - Added NumPy conversion layer for torch::Tensor

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <torch/torch.h>  // Still needed internally for LibAMM
#include <Utils/ConfigMap.hpp>
#include <Utils/IntelliLog.h>
#include <LibAMM.h>
#include <include/papi_config.h>
#if LibAMM_PAPI == 1
#include <Utils/ThreadPerfPAPI.hpp>
#endif

namespace py = pybind11;
using namespace INTELLI;
using namespace LibAMM;

// ============================================================================
// PyTorch <-> NumPy Conversion Layer
// This isolates PyTorch dependency from Python users
// ============================================================================

// Convert torch::Tensor to NumPy array (Python-facing)
py::array torch_to_numpy(const torch::Tensor& tensor) {
    // Ensure tensor is on CPU and contiguous
    auto cpu_tensor = tensor.cpu().contiguous();

    // Get tensor properties
    auto sizes = cpu_tensor.sizes();
    auto strides = cpu_tensor.strides();

    // Convert strides from elements to bytes
    std::vector<ssize_t> np_strides;
    for (auto s : strides) {
        np_strides.push_back(s * cpu_tensor.element_size());
    }

    std::vector<ssize_t> np_shape(sizes.begin(), sizes.end());

    // Determine NumPy dtype based on torch dtype
    py::dtype dtype;
    if (cpu_tensor.scalar_type() == torch::kFloat32) {
        dtype = py::dtype("float32");
    } else if (cpu_tensor.scalar_type() == torch::kFloat64) {
        dtype = py::dtype("float64");
    } else if (cpu_tensor.scalar_type() == torch::kInt32) {
        dtype = py::dtype("int32");
    } else if (cpu_tensor.scalar_type() == torch::kInt64) {
        dtype = py::dtype("int64");
    } else {
        throw std::runtime_error("Unsupported tensor dtype for NumPy conversion");
    }

    // Create NumPy array sharing the same memory (zero-copy when possible)
    // Note: We need to keep the tensor alive, so we make a copy for safety
    return py::array(dtype, np_shape, np_strides, cpu_tensor.data_ptr(), py::cast(cpu_tensor));
}

// Convert NumPy array to torch::Tensor (LibAMM-facing)
torch::Tensor numpy_to_torch(py::array array) {
    // Get NumPy array properties
    py::buffer_info info = array.request();

    // Determine torch dtype from NumPy dtype
    torch::ScalarType dtype;
    if (info.format == py::format_descriptor<float>::format()) {
        dtype = torch::kFloat32;
    } else if (info.format == py::format_descriptor<double>::format()) {
        dtype = torch::kFloat64;
    } else if (info.format == py::format_descriptor<int32_t>::format()) {
        dtype = torch::kInt32;
    } else if (info.format == py::format_descriptor<int64_t>::format()) {
        dtype = torch::kInt64;
    } else {
        throw std::runtime_error("Unsupported NumPy dtype for torch conversion");
    }

    // Convert shape
    std::vector<int64_t> shape(info.shape.begin(), info.shape.end());

    // Create torch tensor from data (creates a copy for safety)
    auto options = torch::TensorOptions().dtype(dtype);
    auto tensor = torch::from_blob(info.ptr, shape, options).clone();

    return tensor;
}
py::dict configMapToDict(const std::shared_ptr<ConfigMap> &cfg) {
  py::dict d;
  auto i64Map = cfg->getI64Map();
  auto u64Map = cfg->getU64Map();
  auto doubleMap = cfg->getDoubleMap();
  auto strMap = cfg->getStrMap();
  for (auto &iter : i64Map) {
    d[py::cast(iter.first)] = py::cast(iter.second);
  }
  for (auto &iter : u64Map) {
    d[py::cast(iter.first)] = py::cast(iter.second);
  }
  for (auto &iter : doubleMap) {
    d[py::cast(iter.first)] = py::cast(iter.second);
  }
  for (auto &iter : strMap) {
    d[py::cast(iter.first)] = py::cast(iter.second);
  }
  return d;
}

// Function to convert Python dictionary to ConfigMap
std::shared_ptr<ConfigMap> dictToConfigMap(const py::dict &dict) {
  auto cfg = std::make_shared<ConfigMap>();
  for (auto item : dict) {
    auto key = py::str(item.first);
    auto value = item.second;
    // Check if the type is int
    if (py::isinstance<py::int_>(value)) {
      int64_t val = value.cast<int64_t>();
      cfg->edit(key, val);
      cfg->edit(key, (uint64_t) val);
     // std::cout << "Key: " << key.cast<std::string>() << " has an int value." << std::endl;
    }
      // Check if the type is float
    else if (py::isinstance<py::float_>(value)) {
      double val = value.cast<float>();
      cfg->edit(key, val);
    }
      // Check if the type is string
    else if (py::isinstance<py::str>(value)) {
      std::string val = py::str(value);
      cfg->edit(key, val);
    }
      // Add more type checks as needed
    else {
      std::cout << "Key: " << key.cast<std::string>() << " has a value of another type." << std::endl;
    }
  }
  return cfg;
}
AbstractCPPAlgoPtr createAMM(std::string nameTag) {
  CPPAlgoTable tab;
  auto ru = tab.findCppAlgo(nameTag);
  if (ru == nullptr) {
    INTELLI_ERROR("No algo named " + nameTag + ", return flat");
    nameTag = "mm";
    return tab.findCppAlgo(nameTag);
  }
  return ru;
}
AbstractMatrixLoaderPtr createMatrixLoader(std::string nameTag) {
  MatrixLoaderTable dt;
  auto ru = dt.findMatrixLoader(nameTag);
  if (ru == nullptr) {
    INTELLI_ERROR("No algo named " + nameTag + ", return flat");
    nameTag = "random";
    return dt.findMatrixLoader(nameTag);
  }
  return ru;
}

// ============================================================================
// Python-facing Wrapper Classes (NumPy interface)
// These classes wrap the torch::Tensor-based LibAMM classes
// ============================================================================

/**
 * @brief Wrapper for AbstractCPPAlgo that uses NumPy arrays instead of torch::Tensor
 */
class CPPAlgoWrapper {
private:
    AbstractCPPAlgoPtr algo_;

public:
    CPPAlgoWrapper(AbstractCPPAlgoPtr algo) : algo_(algo) {}

    void setConfig(INTELLI::ConfigMapPtr cfg) {
        algo_->setConfig(cfg);
    }

    // NumPy interface - converts between NumPy and torch::Tensor
    py::array amm(py::array A, py::array B, uint64_t sketchSize) {
        // Convert NumPy to torch::Tensor
        torch::Tensor torchA = numpy_to_torch(A);
        torch::Tensor torchB = numpy_to_torch(B);

        // Call the actual LibAMM algorithm
        torch::Tensor result = algo_->amm(torchA, torchB, sketchSize);

        // Convert result back to NumPy
        return torch_to_numpy(result);
    }

    INTELLI::ConfigMapPtr getBreakDown() {
        return algo_->getBreakDown();
    }
};

/**
 * @brief Wrapper for AbstractMatrixLoader that uses NumPy arrays
 */
class MatrixLoaderWrapper {
private:
    AbstractMatrixLoaderPtr loader_;

public:
    MatrixLoaderWrapper(AbstractMatrixLoaderPtr loader) : loader_(loader) {}

    void setConfig(INTELLI::ConfigMapPtr cfg) {
        loader_->setConfig(cfg);
    }

    // NumPy interface
    py::array getA() {
        torch::Tensor torchA = loader_->getA();
        return torch_to_numpy(torchA);
    }

    py::array getB() {
        torch::Tensor torchB = loader_->getB();
        return torch_to_numpy(torchB);
    }
};

// Factory functions that return wrappers
std::shared_ptr<CPPAlgoWrapper> createAMMWrapper(std::string nameTag) {
    AbstractCPPAlgoPtr algo = createAMM(nameTag);
    return std::make_shared<CPPAlgoWrapper>(algo);
}

std::shared_ptr<MatrixLoaderWrapper> createMatrixLoaderWrapper(std::string nameTag) {
    AbstractMatrixLoaderPtr loader = createMatrixLoader(nameTag);
    return std::make_shared<MatrixLoaderWrapper>(loader);
}


PYBIND11_MODULE(PyAMM, m) {
  /**
   * @brief Export the PyAMM module
   *
   * This module provides a NumPy-based interface to LibAMM, completely
   * isolating PyTorch dependency from Python users. All tensor operations
   * use NumPy arrays at the Python level, while LibAMM internally uses
   * PyTorch for computation.
   */
  m.attr("__version__") = "0.2.0";  // Incremented for dependency isolation
  m.doc() = "SAGE AMM Library: Approximate Matrix Multiplication Library (NumPy interface)";

  // ConfigMap class (no changes needed - already pure C++)
  py::class_<INTELLI::ConfigMap, std::shared_ptr<INTELLI::ConfigMap>>(m, "ConfigMap")
      .def(py::init<>())
      .def("edit", py::overload_cast<const std::string &, int64_t>(&INTELLI::ConfigMap::edit))
      .def("edit", py::overload_cast<const std::string &, double>(&INTELLI::ConfigMap::edit))
      .def("edit", py::overload_cast<const std::string &, std::string>(&INTELLI::ConfigMap::edit))
      .def("toString", &INTELLI::ConfigMap::toString,
           py::arg("separator") = "\t",
           py::arg("newLine") = "\n")
      .def("toFile", &ConfigMap::toFile,
           py::arg("fname"),
           py::arg("separator") = ",",
           py::arg("newLine") = "\n")
      .def("fromFile", &ConfigMap::fromFile,
           py::arg("fname"),
           py::arg("separator") = ",",
           py::arg("newLine") = "\n");

  // Utility functions
  m.def("configMapToDict", &configMapToDict, "Convert ConfigMap to Python dictionary");
  m.def("dictToConfigMap", &dictToConfigMap, "Convert Python dictionary to ConfigMap");

  // NumPy-based wrapper classes (NEW - replaces torch::Tensor interface)
  py::class_<CPPAlgoWrapper, std::shared_ptr<CPPAlgoWrapper>>(m, "CPPAlgo",
      "Approximate Matrix Multiplication algorithm (uses NumPy arrays)")
      .def("setConfig", &CPPAlgoWrapper::setConfig,
           "Set algorithm configuration")
      .def("amm", &CPPAlgoWrapper::amm,
           py::arg("A"), py::arg("B"), py::arg("sketchSize"),
           "Perform approximate matrix multiplication: C ≈ A @ B\n\n"
           "Args:\n"
           "    A (numpy.ndarray): Left matrix\n"
           "    B (numpy.ndarray): Right matrix\n"
           "    sketchSize (int): Sketch dimension\n\n"
           "Returns:\n"
           "    numpy.ndarray: Approximated result matrix")
      .def("getBreakDown", &CPPAlgoWrapper::getBreakDown,
           "Get performance breakdown");

  py::class_<MatrixLoaderWrapper, std::shared_ptr<MatrixLoaderWrapper>>(m, "MatrixLoader",
      "Matrix data loader (uses NumPy arrays)")
      .def("setConfig", &MatrixLoaderWrapper::setConfig,
           "Set loader configuration")
      .def("getA", &MatrixLoaderWrapper::getA,
           "Get matrix A as NumPy array")
      .def("getB", &MatrixLoaderWrapper::getB,
           "Get matrix B as NumPy array");

  // Factory functions (use wrappers instead of raw pointers)
  m.def("createAMM", &createAMMWrapper,
        py::arg("nameTag"),
        "Create an AMM algorithm by name\n\n"
        "Available algorithms:\n"
        "  - 'mm': Standard matrix multiplication\n"
        "  - 'crs': Column Row Sampling\n"
        "  - 'crsV2': CRS Version 2\n"
        "  - 'weighted-cr': Weighted Column Row\n"
        "  - 'bcrs': Block CRS\n"
        "  - ... and many more (see CPPAlgoTable)\n\n"
        "Returns:\n"
        "    CPPAlgo: Algorithm instance");

  m.def("createMatrixLoader", &createMatrixLoaderWrapper,
        py::arg("nameTag"),
        "Create a matrix loader by name\n\n"
        "Available loaders:\n"
        "  - 'random': Random matrices\n"
        "  - 'gaussian': Gaussian distribution\n"
        "  - 'sparse': Sparse matrices\n"
        "  - ... and many more (see MatrixLoaderTable)\n\n"
        "Returns:\n"
        "    MatrixLoader: Loader instance");

#if LibAMM_PAPI == 1
  // PAPI performance monitoring (no changes needed)
  py::class_<INTELLI::ThreadPerfPAPI, std::shared_ptr<INTELLI::ThreadPerfPAPI>>(m, "PAPIPerf")
      .def(py::init<>())
      .def("initEventsByCfg", &INTELLI::ThreadPerfPAPI::initEventsByCfg)
      .def("start", &INTELLI::ThreadPerfPAPI::start)
      .def("end", &INTELLI::ThreadPerfPAPI::end)
      .def("resultToConfigMap", &INTELLI::ThreadPerfPAPI::resultToConfigMap);
#endif
}
