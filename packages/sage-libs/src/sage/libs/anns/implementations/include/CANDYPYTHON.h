/*! \file CANDYPYTHON.h*/
/**
 * @warning I am just used to generate help documents of python API, do not include me in c++!!!
 */
#ifndef INCLUDE_CANDYPYTHON_H_
#define INCLUDE_CANDYPYTHON_H_

#include <CANDY.h>
#include <torch/torch.h>
using namespace std;
using namespace torch;
using namespace INTELLI;
namespace CANDY {

/**
 * @ingroup lib The main body and interfaces of library function
 * @{
 **/

/** @class Candy_Python CANDYPYTHON.h
* @brief  The python bounding functions
 * @ingroup
* @note
* - Please first run torch.ops.load_library("<the path of CANDY's library>")
* - In this simple bounding, we just access CANDY index class and its configuration by name tag, there is some c++ hash table in the backend to do this
* - Please add the prefix "torch.ops.CANDY." when calling the following fucntions, see also benchmark/pythonTest.py
*/
class Candy_Python {
 public:
  Candy_Python() {}
  ~Candy_Python() {}
/**
* @brief The c++ bindings to creat an index at backend
* @param name the name of this index
* @param type the type of this index, keep the same as that in CANDY::IndexTable
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_create(string name, string type) {
    CANDY::IndexTable it;
    auto idx = it.getIndex(type);
    if (idx == nullptr) {
      return torch::zeros({1, 1});
    }
    torchBounding_idxMap[name] = idx;
    torchBounding_cfgMap[name] = newConfigMap();
    return torch::zeros({1, 1}) + 1.0;
  }

/**
* @brief The c++ bindings to load the config map related to a specific index from file
* @param name the name of the index
 * @param fname the name of file
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_loadCfgFromFile(string name, string fname) {
    if ((torchBounding_cfgMap.count(name) == 1)) // have this index
    {
      torchBounding_cfgMap[name]->fromFile(fname);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to change the config map related to a specific index
* @param name the name of the index
 * @param key the key in the cfg
 * @param value the double value
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_editCfgDouble(string name, string key, double value) {
    if ((torchBounding_cfgMap.count(name) == 1)) // have this index
    {
      torchBounding_cfgMap[name]->edit(key, value);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to change the config map related to a specific index
* @param name the name of the index
 * @param key the key in the cfg
 * @param value the string value
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_editCfgStr(string name, string key, string value) {
    if ((torchBounding_cfgMap.count(name) == 1)) // have this index
    {
      torchBounding_cfgMap[name]->edit(key, value);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to change the config map related to a specific index
* @param name the name of the index
 * @param key the key in the cfg
 * @param value the I64 value
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_editCfgI64(string name, string key, int64_t value) {
    if ((torchBounding_cfgMap.count(name) == 1)) // have this index
    {
      torchBounding_cfgMap[name]->edit(key, value);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to init an index with its bounded config
* @param name the name of the index
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_init(string name) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      torchBounding_idxMap[name]->setConfig(torchBounding_cfgMap[name]);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to insert tensor to an index
* @param name the name of the index
 * @param t the tensor
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_insert(string name, torch::Tensor t) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      if (torchBounding_idxMap[name]->insertTensor(t)) { return torch::zeros({1, 1}) + 1.0; }
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to search tensor
* @param name the name of the index
 * @param t the tensor
 * @param k the NNS
* @return the list of result tensors
*/
  std::vector<torch::Tensor> index_search(string name, torch::Tensor t, int64_t k) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      auto tensors = torchBounding_idxMap[name]->searchTensor(t, k);
      { return tensors; }
    }
    std::vector<torch::Tensor> ru(1);
    ru[0] = torch::zeros({1, 1});
    return ru;
  }
/**
* @brief The c++ bindings to delete tensor to an index
* @param name the name of the index
 * @param t the tensor
 * @param k the NNS
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_delete(string name, torch::Tensor t, int64_t k) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      if (torchBounding_idxMap[name]->deleteTensor(t, k)) { return torch::zeros({1, 1}) + 1.0; }
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to revise tensor to an index
* @param name the name of the index
 * @param t the tensor to be revised
 * @param w the revison
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_revise(string name, torch::Tensor t, torch::Tensor &w) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      if (torchBounding_idxMap[name]->reviseTensor(t, w)) { return torch::zeros({1, 1}) + 1.0; }
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to return rawData
* @param name the name of the index
* @return tensor of rawData
*/
  torch::Tensor index_rawData(string name) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      return torchBounding_idxMap[name]->rawData();
    }
    return torch::zeros({1, 1});
  }
/**
*
* @brief The c++ bindings to creat an index at backend
* @param name the name of the index
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_reset(string name) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      torchBounding_idxMap[name]->reset();
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
  /**
*
* @brief The c++ bindings to start HPC features
* @param name the name of the index
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_startHPC(string name) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      torchBounding_idxMap[name]->startHPC();
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
*
* @brief The c++ bindings to end HPC features
* @param name the name of the index
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_endHPC(string name) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      torchBounding_idxMap[name]->endHPC();
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }

/**
* @brief The c++ bindings to save a tensor into file
 * @param A the tensor
* @param name the name of the index
* @return tensor 1x1, [1] for success
*/
  torch::Tensor tensorToFile(torch::Tensor A, std::string fname) {
    if (IntelliTensorOP::tensorToFile(&A, fname)) {
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to load a tensor from file
* @param name the name of the index
* @return the tensor result
*/
  torch::Tensor tensorFromFile(std::string fname) {
    torch::Tensor A;
    if (IntelliTensorOP::tensorFromFile(&A, fname)) {
      return A;
    }
    return torch::zeros({1, 1});
  }

/**
* @brief The c++ bindings to set the frozen level of online updating internal state
* @param name the name of the index
 * @param frozenLv the level of frozen, 0 means freeze any online update in internal state
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_setFrozenLevel(string name, int64_t frozenLV) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      torchBounding_idxMap[name]->setFrozenLevel(frozenLV);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }

/**
*
* @brief The c++ bindings to offlineBuild
* @param name the name of the index
 * @param t the tensor
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_offlineBuild(string name, torch::Tensor t) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      if (torchBounding_idxMap[name]->offlineBuild(t)) { return torch::zeros({1, 1}) + 1.0; }
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to load initial tensor
*  @note This is majorly an offline function, and may be different from @ref index_insert for some indexes
* @param name the name of the index
 * @param t the tensor
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_loadInitial(string name, torch::Tensor t) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      if (torchBounding_idxMap[name]->loadInitialTensor(t)) { return torch::zeros({1, 1}) + 1.0; }
    }
    return torch::zeros({1, 1});
  }
/**
*
* @brief The c++ bindings to wait pending operations features
* @param name the name of the index
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_waitPending(string name) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      torchBounding_idxMap[name]->waitPendingOperations();
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }

/**
*
* @brief The c++ bindings to creat an dataLoader at backend
* @param name the name of this dataLoader
* @param type the type of this dataLoader, keep the same as that in CANDY::IndexTable
* @return tensor 1x1, [1] for success
*/
  torch::Tensor dataLoader_create(string name, string type) {
    CANDY::DataLoaderTable it;
    auto idx = it.findDataLoader(type);
    if (idx == nullptr) {
      return torch::zeros({1, 1});
    }
    torchBounding_dataLoaderMap[name] = idx;
    torchBounding_cfgDlMap[name] = newConfigMap();
    return torch::zeros({1, 1}) + 1.0;
  }
/**
* @brief The c++ bindings to change the config map related to a specific dataLoader
* @param name the name of the dataLoader
 * @param key the key in the cfg
 * @param value the double value
* @return tensor 1x1, [1] for success
*/
  torch::Tensor dataLoader_editCfgDouble(string name, string key, double value) {
    if ((torchBounding_cfgDlMap.count(name) == 1)) // have this dataLoader
    {
      torchBounding_cfgDlMap[name]->edit(key, value);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }

/**
* @brief The c++ bindings to change the config map related to a specific dataLoader
* @param name the name of the dataLoader
 * @param key the key in the cfg
 * @param value the float value
* @return tensor 1x1, [1] for success
*/
  torch::Tensor dataLoader_editCfgFloat(string name, string key, float value) {
    if ((torchBounding_cfgDlMap.count(name) == 1)) // have this dataLoader
    {
      double v2 = value;
      torchBounding_cfgDlMap[name]->edit(key, v2);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to change the config map related to a specific dataLoader
* @param name the name of the dataLoader
 * @param key the key in the cfg
 * @param value the string value
* @return tensor 1x1, [1] for success
*/
  torch::Tensor dataLoader_editCfgStr(string name, string key, string value) {
    if ((torchBounding_cfgDlMap.count(name) == 1)) // have this dataLoader
    {
      torchBounding_cfgDlMap[name]->edit(key, value);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to change the config map related to a specific dataLoader
* @param name the name of the dataLoader
 * @param key the key in the cfg
 * @param value the I64 value
* @return tensor 1x1, [1] for success
*/
  torch::Tensor dataLoader_editCfgI64(string name, string key, int64_t value) {
    if ((torchBounding_cfgDlMap.count(name) == 1)) // have this dataLoader
    {
      torchBounding_cfgDlMap[name]->edit(key, value);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to init an dataLoader with its bounded config
* @param name the name of the dataLoader
* @return tensor 1x1, [1] for success
*/
  torch::Tensor dataLoader_init(string name) {
    if ((torchBounding_dataLoaderMap.count(name) == 1)) // have this dataLoader
    {
      torchBounding_dataLoaderMap[name]->setConfig(torchBounding_cfgDlMap[name]);
      return torch::zeros({1, 1}) + 1.0;
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to get data tensor from the specified data loader
* @param name the name of the dataLoader
 * @param t the tensor
* @return tensor 1x1, [1] for success
*/
  torch::Tensor dataLoader_getData(string name) {
    if ((torchBounding_dataLoaderMap.count(name) == 1)) // have this dataLoader
    {
      return torchBounding_dataLoaderMap[name]->getData();
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to get query tensor from the specified data loader
* @param name the name of the dataLoader
* @return the first result tensor
*/
  torch::Tensor dataLoader_getQuery(string name) {
    if ((torchBounding_dataLoaderMap.count(name) == 1)) // have this dataLoader
    {
      return torchBounding_dataLoaderMap[name]->getQuery();
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to load tensor from fvecs file
* @param name the name of file
* return the result tensor
*/
  torch::Tensor tensorFromFVECS(string name) {
    return CANDY::FVECSDataLoader::tensorFromFVECS(name);
  }
/**
* @brief The c++ bindings to load tensor from HDF5 file
* @param name the name of file
* @param attr the attribute
* return the result tensor
*/
  torch::Tensor tensorFromHDF5(string name, string attr) {
#if CANDY_HDF5 == 1
    return CANDY::HDF5DataLoader::tensorFromHDF5(name, attr);
#else
    return torch::zeros({1, 1});
#endif
  }
/**
* @brief The c++ bindings to load initial tensor along with string objects
* @param name the name of the index
 * @param t the tensor
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_loadInitialString(string name, torch::Tensor t, std::vector<std::string> s) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      if (torchBounding_idxMap[name]->loadInitialStringObject(t, s)) { return torch::zeros({1, 1}) + 1.0; }
    }
    return torch::zeros({1, 1});
  }
/**
* @brief The c++ bindings to insert tensor to an index with its binded strings
* @param name the name of the index
 * @param t the tensor
 * @param s the vector of string, List[str] in python
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_insertString(string name, torch::Tensor t, std::vector<std::string> s) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      if (torchBounding_idxMap[name]->insertStringObject(t, s)) { return torch::zeros({1, 1}) + 1.0; }
    }
    return torch::zeros({1, 1});
  }

/**
* @brief The c++ bindings to delete tensor to an index and its string object
* @param name the name of the index
 * @param t the tensor
 * @param k the NNS
* @return tensor 1x1, [1] for success
*/
  torch::Tensor index_deleteString(string name, torch::Tensor t, int64_t k) {
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      if (torchBounding_idxMap[name]->deleteStringObject(t, k)) { return torch::zeros({1, 1}) + 1.0; }
    }
    return torch::zeros({1, 1});
  }

/**
* @brief The c++ bindings to search binded string of given tensor
* @param name the name of the index
 * @param t the tensor
 * @param k the NNS
* @return List[List[str]], for each rows
*/
  std::vector<std::vector<std::string>> index_searchString(string name, torch::Tensor &q, int64_t k) {

    assert(k > 0);
    assert(q.size(1));
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      auto rut = torchBounding_idxMap[name]->searchStringObject(q, k);
      { return rut; }
    }
    std::vector<std::vector<std::string>> ru(1);
    ru[0] = std::vector<std::string>(0);
    return ru;
  }
/**
* @brief The c++ bindings to search tensor and binded string of given tensor
* @param name the name of the index
 * @param t the tensor
 * @param k the NNS
* @return [List[Tensor],List[List[str]]], for each rows
*/
  std::tuple<std::vector<torch::Tensor>,
             std::vector<std::vector<std::string>>> index_searchTensorAndStringList(string name,
                                                                                    torch::Tensor &q,
                                                                                    int64_t k) {

    assert(k > 0);
    assert(q.size(1));
    if ((torchBounding_idxMap.count(name) == 1)) // have this index
    {
      auto ru = torchBounding_idxMap[name]->searchTensorAndStringObject(q, k);
      { return ru; }
    }
    auto ruT = CANDY_index_searchTensorList(name, q, k);
    auto ruS = CANDY_index_searchStringList(name, q, k);
    std::tuple<std::vector<torch::Tensor>, std::vector<std::vector<std::string>>> ru(ruT, ruS);
    return ru;
  }

};

}

/**
* @}
*/

#endif //INCLUDE_CANDYPYTHON_H_
