//
// Created by tony on 12/04/24.
//
#include <gflags/gflags.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <torch/extension.h>
#include <torch/torch.h>
#include <Utils/ConfigMap.hpp>
#include <Utils/IntelliLog.h>
#include <Utils/SPSCQueue.hpp>
#include <AbstractIndex.h>


#include <IndexTable.h>
#include <papi_config.h>
#if CANDY_PAPI == 1
#include <Utils/ThreadPerfPAPI.hpp>
#endif
//#if CANDY_DiskANN == 1
#include "defaults.h"
#include "distance.h"
#include <DiskANN/python/include/dynamic_memory_index.h>
#include <DiskANN/python/include/builder.h>
//#endif
#include <faiss/index_factory.h>
#include <faiss/IndexHNSWOptimized.h>


#include<puck/pyapi_wrapper/py_api_wrapper.h>

namespace py = pybind11;
using namespace INTELLI;
using namespace pybind11::literals;
using namespace CANDY;
torch::Tensor add_tensors(torch::Tensor a, torch::Tensor b) {
  return a + b;
}
py::dict configMapToDict(const std::shared_ptr<ConfigMap> &cfg) {
  py::dict d;
  auto i64Map = cfg->getI64Map();
  auto doubleMap = cfg->getDoubleMap();
  auto strMap = cfg->getStrMap();
  for (auto &iter : i64Map) {
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
      //std::cout << "Key: " << key.cast<std::string>() << " has an int value." << std::endl;
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
//AbstractIndexPtr createIndex(std::string nameTag) {
//  IndexTable tab;
//  auto ru = tab.getIndex(nameTag);
//  if (ru == nullptr) {
//    INTELLI_ERROR("No index named " + nameTag + ", return flat");
//    nameTag = "flat";
//    return tab.getIndex(nameTag);
//  }
//  return ru;
//}

AbstractIndexPtr createIndex(std::string nameTag, int64_t dim) {
    IndexTable tab;
    auto ru = tab.getIndex(nameTag);
    if (ru == nullptr) {
        INTELLI_ERROR("No index named " + nameTag + ", return flat");
        nameTag = "flat";
        return tab.getIndex(nameTag);
    }
    std::cout << "Found index with name: " << nameTag << std::endl;
    ConfigMapPtr cfg = newConfigMap();
    cfg->edit("vecDim", dim);
    ru->setConfig(cfg);

    return ru;
}

//AbstractDataLoaderPtr creatDataLoader(std::string nameTag) {
//  DataLoaderTable dt;
//  auto ru = dt.findDataLoader(nameTag);
//  if (ru == nullptr) {
//    INTELLI_ERROR("No index named " + nameTag + ", return flat");
//    nameTag = "random";
//    return dt.findDataLoader(nameTag);
//  }
//  return ru;
//}
static bool existRow(torch::Tensor base, torch::Tensor row) {
  for (int64_t i = 0; i < base.size(0); i++) {
    auto tensor1 = base[i].contiguous();
    auto tensor2 = row.contiguous();
    //std::cout<<"base: "<<tensor1<<std::endl;
    //std::cout<<"query: "<<tensor2<<std::endl;
    if (torch::equal(tensor1, tensor2)) {
      return true;
    }
  }
  return false;
}
double recallOfTensorList(std::vector<torch::Tensor> groundTruth, std::vector<torch::Tensor> prob) {
  int64_t truePositives = 0;
  int64_t falseNegatives = 0;
  for (size_t i = 0; i < prob.size(); i++) {
    auto gdI = groundTruth[i];
    auto probI = prob[i];
    for (int64_t j = 0; j < probI.size(0); j++) {
      if (existRow(gdI, probI[j])) {
        truePositives++;
      } else {
        falseNegatives++;
      }
    }
  }
  double recall = static_cast<double>(truePositives) / (truePositives + falseNegatives);
  return recall;
}


template <class DT>
class NumpyIdxPair{
public:
    NumpyIdxPair(){};
    ~NumpyIdxPair(){};
    std::vector<int64_t> idx;
    py::array_t<DT> vectors;
    NumpyIdxPair(const py::array_t<DT> _vectors, const std::vector<int64_t> _idx){
        idx=_idx;
        vectors = _vectors;
    }
};

using NumpyIdxPairInt8 = NumpyIdxPair<int8_t>;
using NumpyIdxPairFloat = NumpyIdxPair<float>;

using NumpyIdxQueueInt8 = SPSCQueue<NumpyIdxPairInt8>;
using NumpyIdxQueueFloat = SPSCQueue<NumpyIdxPairFloat>;

template<class DT>
class SPSCWrapperNumpy{
public:
    SPSCWrapperNumpy(size_t capacity){
        queue = new SPSCQueue<NumpyIdxPair<DT>>(capacity);
    }
    SPSCQueue<NumpyIdxPair<DT>>* queue;
    void push(NumpyIdxPair<DT> &obj){
        queue->push(obj);
    }
    bool try_push(NumpyIdxPair<DT> &obj){
        return queue->try_push(obj);
    }
    NumpyIdxPair<DT> front(){

        auto temp = NumpyIdxPair<DT>(queue->front()->vectors, queue->front()->idx);
        return temp;
    }
    void pop(){
        queue->pop();
    }
    size_t capacity(){
        return queue->capacity();
    }
    size_t size(){
        return queue->size();
    }
    bool empty(){
        return queue->empty();
    }
};

class SPSCWrapperIdx{
public:
    SPSCWrapperIdx(size_t capacity){
        queue = new SPSCQueue<int64_t>(capacity);
    }
    SPSCQueue<int64_t>* queue;
    void push(int64_t &obj){
        queue->push(obj);
    }
    bool try_push(int64_t &obj){
        return queue->try_push(obj);
    }
    int64_t front(){

        auto temp = *(queue->front());
        return temp;
    }
    void pop(){
        queue->pop();
    }
    size_t capacity(){
        return queue->capacity();
    }
    size_t size(){
        return queue->size();
    }
    bool empty(){
        return queue->empty();
    }

};



//#if CANDY_DiskANN == 1
struct Variant
{
  std::string disk_builder_name;
  std::string memory_builder_name;
  std::string dynamic_memory_index_name;
  std::string static_memory_index_name;
  std::string static_disk_index_name;
};
const Variant FloatVariant{"build_disk_float_index", "build_memory_float_index", "DynamicMemoryFloatIndex",
                           "StaticMemoryFloatIndex", "StaticDiskFloatIndex"};

const Variant UInt8Variant{"build_disk_uint8_index", "build_memory_uint8_index", "DynamicMemoryUInt8Index",
                           "StaticMemoryUInt8Index", "StaticDiskUInt8Index"};

const Variant Int8Variant{"build_disk_int8_index", "build_memory_int8_index", "DynamicMemoryInt8Index",
                          "StaticMemoryInt8Index", "StaticDiskInt8Index"};

template <typename T> inline void add_variant(py::module_ &m, const Variant &variant)
{


    m.def(variant.memory_builder_name.c_str(), &diskannpy::build_memory_index<T>, "distance_metric"_a,
          "data_file_path"_a, "index_output_path"_a, "graph_degree"_a, "complexity"_a, "alpha"_a, "num_threads"_a,
          "use_pq_build"_a, "num_pq_bytes"_a, "use_opq"_a, "filter_complexity"_a = 0, "use_tags"_a = false);
    py::class_<diskannpy::DynamicMemoryIndex<T>>(m, variant.dynamic_memory_index_name.c_str())
        .def(py::init<const diskann::AlgoType ,const diskann::Metric, const size_t, const size_t, const uint32_t, const uint32_t, const bool,
                      const uint32_t, const float, const uint32_t, const uint32_t, const uint32_t, const uint32_t,
                      const uint32_t, const bool>(),
             "algo_type"_a,"distance_metric"_a, "dimensions"_a, "max_vectors"_a, "complexity"_a, "graph_degree"_a,
             "saturate_graph"_a = diskann::defaults::SATURATE_GRAPH,
             "max_occlusion_size"_a = diskann::defaults::MAX_OCCLUSION_SIZE, "alpha"_a = diskann::defaults::ALPHA,
             "num_threads"_a = diskann::defaults::NUM_THREADS,
             "filter_complexity"_a = diskann::defaults::FILTER_LIST_SIZE,
             "num_frozen_points"_a = diskann::defaults::NUM_FROZEN_POINTS_DYNAMIC, "initial_search_complexity"_a = 0,
             "search_threads"_a = 0, "concurrent_consolidation"_a = true)
        .def("search", &diskannpy::DynamicMemoryIndex<T>::search, "query"_a, "knn"_a, "complexity"_a)
        .def("load", &diskannpy::DynamicMemoryIndex<T>::load, "index_path"_a)
        .def("batch_search", &diskannpy::DynamicMemoryIndex<T>::batch_search, "queries"_a, "num_queries"_a, "knn"_a,
             "complexity"_a, "num_threads"_a)
        .def("batch_insert", &diskannpy::DynamicMemoryIndex<T>::batch_insert, "vectors"_a, "ids"_a, "num_inserts"_a,
             "num_threads"_a)
        .def("save", &diskannpy::DynamicMemoryIndex<T>::save, "save_path"_a = "", "compact_before_save"_a = false)
        .def("insert", &diskannpy::DynamicMemoryIndex<T>::insert, "vector"_a, "id"_a)
        .def("mark_deleted", &diskannpy::DynamicMemoryIndex<T>::mark_deleted, "id"_a)
        .def("consolidate_delete", &diskannpy::DynamicMemoryIndex<T>::consolidate_delete);

}
//#endif
#define COMPILED_TIME (__DATE__ " " __TIME__)
PYBIND11_MODULE(PyCANDYAlgo, m) {
  /**
   * @brief export the configmap class
   */
  m.attr("__version__") = "0.1.2";  // Set the version of the module
  m.attr("__compiled_time__") = COMPILED_TIME;  // Set the compile time of the module
  m.doc() = "This is top module - PyCANDYAlgo.";
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
  m.def("configMapToDict", &configMapToDict, "A function that converts ConfigMap to Python dictionary");
  m.def("dictToConfigMap", &dictToConfigMap, "A function that converts  Python dictionary to ConfigMap");
  /***
   * @brief abstract index
   */
  py::class_<AbstractIndex, std::shared_ptr<AbstractIndex>>(m, "AbstractIndex")
      .def(py::init<>())
      .def("setTier", &AbstractIndex::setTier)
      .def("reset", &AbstractIndex::reset, py::call_guard<py::gil_scoped_release>())
      .def("setConfigClass", &AbstractIndex::setConfigClass, py::call_guard<py::gil_scoped_release>())
      .def("setConfig", &AbstractIndex::setConfig, py::call_guard<py::gil_scoped_release>())
      .def("startHPC", &AbstractIndex::startHPC)
      .def("insertTensor", &AbstractIndex::insertTensor)
      .def("insertTensorWithIds", &AbstractIndex::insertTensorWithIds)
      .def("loadInitialTensor", &AbstractIndex::loadInitialTensor)
      .def("loadInitialTensorWithIds", &AbstractIndex::loadInitialTensorWithIds)
      .def("deleteTensor", &AbstractIndex::deleteTensor)
      .def("deleteIndex", &AbstractIndex::deleteIndex)
      .def("reviseTensor", &AbstractIndex::reviseTensor)
      .def("searchIndex", &AbstractIndex::searchIndex)
      .def("searchIndexParam", &AbstractIndex::searchIndexParam)
      .def("rawData", &AbstractIndex::rawData)
      .def("ccInsertAndSearchTensor", &AbstractIndex::ccInsertAndSearchTensor)
      .def("searchTensor", &AbstractIndex::searchTensor)
      .def("endHPC", &AbstractIndex::endHPC)
      .def("setFrozenLevel", &AbstractIndex::setFrozenLevel)
      .def("offlineBuild", &AbstractIndex::offlineBuild)
      .def("waitPendingOperations", &AbstractIndex::waitPendingOperations)
      .def("loadInitialStringObject", &AbstractIndex::loadInitialStringObject)
      .def("loadInitialU64Object", &AbstractIndex::loadInitialU64Object)
      .def("insertStringObject", &AbstractIndex::insertStringObject)
      .def("insertU64Object", &AbstractIndex::insertU64Object)
      .def("deleteStringObject", &AbstractIndex::deleteStringObject)
      .def("deleteU64Object", &AbstractIndex::deleteU64Object)
      .def("searchStringObject", &AbstractIndex::searchStringObject)
      .def("searchU64Object", &AbstractIndex::searchU64Object)
      .def("searchTensorAndStringObject", &AbstractIndex::searchTensorAndStringObject)
      .def("loadInitialTensorAndQueryDistribution", &AbstractIndex::loadInitialTensorAndQueryDistribution)
      .def("resetIndexStatistics", &AbstractIndex::resetIndexStatistics)
      .def("getIndexStatistics", &AbstractIndex::getIndexStatistics);
  m.def("createIndex", &createIndex, "A function to create new index by name tag");

  m.def("add_tensors", &add_tensors, "A function that adds two tensors");


  m.def("recallOfTensorList", &recallOfTensorList, "calculate the recall");

  /// faiss index APIs only
  py::class_<faiss::Index,std::shared_ptr<faiss::Index>>(m, "IndexFAISS")
         // .def(py::init<>())
          .def("add",&faiss::Index::add_arrays)
          .def("search",&faiss::Index::search_arrays)
          .def("train",&faiss::Index::train_arrays)
          .def("add_with_ids", &faiss::Index::add_arrays_with_ids)
        .def_readwrite("verbose", &faiss::Index::verbose);

  m.def("index_factory_ip", &faiss::index_factory_IP, "Create custom index from faiss with IP");

  m.def("index_factory_l2", &faiss::index_factory_L2, "Create custom index from faiss with L2");

  /// Metric type enum for faiss (needed before IndexHNSW classes)
  py::enum_<faiss::MetricType>(m, "MetricType")
      .value("METRIC_L2", faiss::METRIC_L2)
      .value("METRIC_INNER_PRODUCT", faiss::METRIC_INNER_PRODUCT)
      .export_values();

  /// IndexHNSWFlatOptimized - HNSW index with Flat storage and Gorder optimization
  /// This is the main class to use for HNSW with Gorder reordering
  py::class_<faiss::IndexHNSWFlatOptimized, std::shared_ptr<faiss::IndexHNSWFlatOptimized>>(m, "IndexHNSWFlatOptimized")
      .def(py::init<int, int, faiss::MetricType>(),
           py::arg("d"), py::arg("M") = 32, py::arg("metric") = faiss::METRIC_L2,
           "Create HNSW index with Flat storage.\n"
           "Args:\n"
           "  d: vector dimension\n"
           "  M: number of neighbors per node (default 32)\n"
           "  metric: distance metric (METRIC_L2 or METRIC_INNER_PRODUCT)")
      .def("add", &faiss::IndexHNSWFlatOptimized::add_arrays,
           "Add vectors to the index")
      .def("search", &faiss::IndexHNSWFlatOptimized::search_arrays,
           py::arg("n"), py::arg("x"), py::arg("k"), py::arg("ef_search"),
           "Search k nearest neighbors with given efSearch parameter")
      .def("train", &faiss::IndexHNSWFlatOptimized::train_arrays,
           "Train the index (no-op for Flat storage)")
      .def("reset", &faiss::IndexHNSWFlatOptimized::reset,
           "Remove all vectors from the index")
      .def("reorder_gorder", &faiss::IndexHNSWFlatOptimized::reorder_gorder,
           py::arg("window") = 5,
           "Reorder the HNSW graph using Gorder algorithm for better cache locality.\n"
           "Args:\n"
           "  window: sliding window size for Gorder algorithm (default 5)")
      .def_readwrite("verbose", &faiss::IndexHNSWFlatOptimized::verbose)
      .def_readonly("ntotal", &faiss::IndexHNSWFlatOptimized::ntotal,
           "Total number of vectors in the index")
      .def_readonly("d", &faiss::IndexHNSWFlatOptimized::d,
           "Vector dimension");





#if CANDY_PAPI == 1
  py::class_<INTELLI::ThreadPerfPAPI, std::shared_ptr<INTELLI::ThreadPerfPAPI>>(m, "PAPIPerf")
      .def(py::init<>())
      .def("initEventsByCfg", &INTELLI::ThreadPerfPAPI::initEventsByCfg)
      .def("start", &INTELLI::ThreadPerfPAPI::start)
      .def("end", &INTELLI::ThreadPerfPAPI::end)
      .def("resultToConfigMap", &INTELLI::ThreadPerfPAPI::resultToConfigMap);
#endif


  auto m_puck = m.def_submodule("puck", "Puck Interface from Baidu.");
  py::class_<py_puck_api::PySearcher, std::shared_ptr<py_puck_api::PySearcher>>(m_puck, "PuckSearcher")
    .def(py::init<>())
    .def("init", &py_puck_api::PySearcher::init)
    .def("show",&py_puck_api::PySearcher::show)
    .def("build",&py_puck_api::PySearcher::build)
    .def("search",&py_puck_api::PySearcher::search)
    .def("batch_add",&py_puck_api::PySearcher::batch_add)
    .def("batch_delete",&py_puck_api::PySearcher::batch_delete);

    m_puck.def("update_gflag", &py_puck_api::update_gflag, "A function to update gflag");


    auto m_utils = m.def_submodule("utils", "Utility Classes from CANDY.");
    py::class_<NumpyIdxPair<float>,std::shared_ptr<NumpyIdxPair<float>>>(m_utils,"NumpyIdxPair")
            .def(py::init<>())
            .def(py::init<py::array_t<float, py::array::c_style | py::array::forcecast>, std::vector<int64_t>>())
            .def_readwrite("vectors", &NumpyIdxPair<float>::vectors)
            .def_readwrite("idx", &NumpyIdxPair<float>::idx);

    py::class_<SPSCWrapperNumpy<float>, std::shared_ptr<SPSCWrapperNumpy<float>>>(m_utils, "NumpyIdxQueue")
        .def(py::init<const size_t>())
        .def("push", &SPSCWrapperNumpy<float>::push)
        .def("try_push", &SPSCWrapperNumpy<float>::try_push)
        .def("front", &SPSCWrapperNumpy<float>::front)
        .def("empty", &SPSCWrapperNumpy<float>::empty)
        .def("size", &SPSCWrapperNumpy<float>::size)
        .def("capacity", &SPSCWrapperNumpy<float>::capacity)
        .def("pop", &SPSCWrapperNumpy<float>::pop);
    py::class_<SPSCWrapperIdx, std::shared_ptr<SPSCWrapperIdx>>(m_utils, "IdxQueue")
            .def(py::init<const size_t>())
            .def("push", &SPSCWrapperIdx::push)
            .def("try_push", &SPSCWrapperIdx::try_push)
            .def("front", &SPSCWrapperIdx::front)
            .def("empty", &SPSCWrapperIdx::empty)
            .def("size", &SPSCWrapperIdx::size)
            .def("capacity", &SPSCWrapperIdx::capacity)
            .def("pop", &SPSCWrapperIdx::pop);


  auto m_diskann = m.def_submodule("diskannpy","diskann interface from microsoft.");
  m_diskann.def("add_tensors", &add_tensors, "A function that adds two tensors");


//#if CANDY_DiskANN == 1
  py::module_ default_values = m_diskann.def_submodule(
        "defaults",
        "A collection of the default values used for common diskann operations. `GRAPH_DEGREE` and `COMPLEXITY` are not"
        " set as defaults, but some semi-reasonable default values are selected for your convenience. We urge you to "
        "investigate their meaning and adjust them for your use cases.");

  default_values.attr("ALPHA") = diskann::defaults::ALPHA;
  default_values.attr("NUM_THREADS") = diskann::defaults::NUM_THREADS;
  default_values.attr("MAX_OCCLUSION_SIZE") = diskann::defaults::MAX_OCCLUSION_SIZE;
  default_values.attr("FILTER_COMPLEXITY") = diskann::defaults::FILTER_LIST_SIZE;
  default_values.attr("NUM_FROZEN_POINTS_STATIC") = diskann::defaults::NUM_FROZEN_POINTS_STATIC;
  default_values.attr("NUM_FROZEN_POINTS_DYNAMIC") = diskann::defaults::NUM_FROZEN_POINTS_DYNAMIC;
  default_values.attr("SATURATE_GRAPH") = diskann::defaults::SATURATE_GRAPH;
  default_values.attr("GRAPH_DEGREE") = diskann::defaults::MAX_DEGREE;
  default_values.attr("COMPLEXITY") = diskann::defaults::BUILD_LIST_SIZE;
  default_values.attr("PQ_DISK_BYTES") = (uint32_t)0;
  default_values.attr("USE_PQ_BUILD") = false;
  default_values.attr("NUM_PQ_BYTES") = (uint32_t)0;
  default_values.attr("USE_OPQ") = false;
  add_variant<float>(m_diskann, FloatVariant);
  add_variant<uint8_t>(m_diskann, UInt8Variant);
  add_variant<int8_t>(m_diskann, Int8Variant);

  py::enum_<diskann::Metric>(m_diskann, "Metric")
        .value("L2", diskann::Metric::L2)
        .value("INNER_PRODUCT", diskann::Metric::INNER_PRODUCT)
        .value("COSINE", diskann::Metric::COSINE)
        .export_values();
  py::enum_<diskann::AlgoType>(m_diskann, "AlgoType")
        .value("DISKANN", diskann::AlgoType::DISKANN)
        .value("CUFE", diskann::AlgoType::CUFE)
        .value("PYANNS", diskann::AlgoType::PYANNS)
        .export_values();
  m_diskann.attr("defaults") = default_values;
  m.attr("diskannpy") = m_diskann;
//#endif




}
