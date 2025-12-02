# GTI: Graph-Based Tree Index with Logarithm Updates for Nearest Neighbor Search in High-Dimensional Spaces

## Introduction

GTI is a novel, lightweight, and dynamic graph-based tree index for high-dimensional nearest
neighbor search (NNS). GTI constructs a tree index built across the entire dataset and employs a
lightweight graph index at the level 1 of the tree to significantly reduce graph construction costs.
It also features effective data insertion and deletion algorithms that enable logarithmic real-time
updates. Additionally, we have developed an effective NNS algorithm for GTI, which not only achieves
approximate search performance on par with SOTA graph-based methods but also supports exact NNS.

## Development

We implement our index in C++ using g++. We use CMake to compile and build the project.

The code for this project is located in the "GTI" directory. The files in the "GTI" directory are
organized as follows.

- include: It includes header files of GTI.

- src: It includes source files of GTI.

- extern_libraries: It contains the external library (modified HNSW) files required by GTI. The
  original paper link and code repository of HNSW are https://doi.org/10.1109/TPAMI.2018.2889473 and
  https://github.com/kakao/n2, respectively.

  Note that the third-party library (GTI/extern_libraries/n2/third_party) can be found through the
  code repository of HNSW.

- CMakeLists.txt

The steps for building the project are as follows:

```shell
cd GTI/extern_libraries/n2
mkdir build
make shared_lib

cd GTI
mkdir bin
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j
```

The compiled executable file "GTI" is located in the "GTI/bin" directory.

## Usage

### Index Construction and Approximate $k$NNS (A$k$NNS)

Build GTI index based on the input data, and utilize GTI for A$k$NNS.

```shell
GTI/bin/GTI [data_path] [query_path] [operation_type = 0] [ground_truth_path] [search_para1] [search_para2] [result_path]
```

The meanings of the parameters are as follows.

- **data_path**, The dataset file.
- **query_path**, The file of queries.
- **operation_type**, Type of operation, with 0 for A$k$NNS.
- **ground_truth_path**, The ground truth file.
- **search_para1**, Parameter for the size of the candidate set.
- **search_para2**, Representing '$k$' in A$k$NNS.
- **result_path**, Result file directory.

Here is a specific example for GTI index construction and A$k$NNS.

```shell
cd GTI
bin/GTI ../Datasets/bigann_example_base.fvecs ../Datasets/bigann_example_query.fvecs 0 ../Datasets/bigann_example_groundtruth.ivecs 60 10 ../Datasets/
```

### Index Updating

Build and then update GTI index.

Specifically, we perform update operations including inserting and removing objects. Meanwhile, we
intersperse query operations (A$k$NNS) within the updates. This approach simulates real-world
dynamic scenarios, where updates and user queries may occur concurrently.

Note that we just give a update example in the code.

```shell
GTI/bin/GTI [data_path] [query_path] [operation_type = 3] [ground_truth_path] [result_path]
```

The meanings of the parameters are as follows.

- **data_path**, The dataset file.
- **query_path**, The file of queries.
- **operation_type**, Type of operation, with 3 for updates.
- **ground_truth_path**, The ground truth file.
- **result_path**, Result file directory.

Here is a specific example for GTI updating.

```shell
cd GTI
bin/GTI ../Datasets/bigann_example_base.fvecs ../Datasets/bigann_example_query.fvecs 3 ../Datasets/bigann_example_groundtruth.ivecs ../Datasets/
```

### Exact $k$NNS

Build GTI index based on the input data, and utilize GTI for exact $k$NNS.

```shell
GTI/bin/GTI [data_path] [query_path] [operation_type = 1] [search_para1] [search_para2] [result_path]
```

The meanings of the parameters are as follows.

- **data_path**, The dataset file.
- **query_path**, The file of queries.
- **operation_type**, Type of operation, with 1 for exact $k$NNS.
- **search_para1**, Parameter for the size of the candidate set.
- **search_para2**, Representing '$k$' in exact $k$NNS.
- **result_path**, Result file directory.

Here is a specific example for exact $k$NNS.

```shell
cd GTI
bin/GTI ../Datasets/bigann_example_base.fvecs ../Datasets/bigann_example_query.fvecs 1 60 10 ../Datasets/
```

Additionally, due to nature of its hybrid tree-graph structure, GTI naturally supports exact range
queries.

```shell
GTI/bin/GTI [data_path] [query_path] [operation_type = 2] [search_para] [result_path]
```

The meanings of the parameters are as follows.

- **data_path**, The dataset file.
- **query_path**, The file of queries.
- **operation_type**, Type of operation, with 2 for exact range queries.
- **search_para**, Representing the radius in exact range queries.
- **result_path**, Result file directory.

Here is a specific example for exact range queries.

```shell
cd GTI
bin/GTI ../Datasets/bigann_example_base.fvecs ../Datasets/bigann_example_query.fvecs 2 400 ../Datasets/
```

## Baselines

| __Algorithm__ | __Paper__                                                                                                | __Year__ |
| ------------- | -------------------------------------------------------------------------------------------------------- | -------- |
| M-tree        | M-tree: An Efficient Access Method for Similarity Search in Metric Spaces                                | 1997     |
| MVPT          | Distance-Based Indexing for High-Dimensional Metric Spaces                                               | 1997     |
| HNSW          | Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs | 2020     |
| NSG           | Fast Approximate Nearest Neighbor Search With The Navigating Spreading-out Graph                         | 2019     |
| LSH-APG       | Towards Efficient Index Construction and Approximate Nearest Neighbor Search in High-Dimensional Spaces  | 2023     |
| ELPIS         | Elpis: Graph-Based Similarity Search for Scalable Data Science                                           | 2023     |

- We choose two well-established and efficient tree-based methods for exact NNS and range query
  according to the Chen et al.'s survey in CSUR 2022, including dynamic index M-tree and static
  index MVPT. The source codes for M-tree and MVPT are available at
  [The M-tree Project](http://www-db.deis.unibo.it/Mtree/) and
  [SISAP Metric Space Library](https://www.sisap.org/), respectively.
- We choose two SOTA graph-based methods for ANNS according to the Wang et al.'s survey in VLDB
  2021, including HNSW and NSG, where the advanced [MNG](https://doi.org/10.1145/3588908) (PACMMOD
  2023\) update strategy is applied to both methods. The source codes for HNSW and NSG are available
  at https://github.com/kakao/n2 and https://github.com/ZJULearning/nsg, respectively.
- We choose two recent hybrid methods for ANNS, including the dynamic hash-graph combination method
  LSH-APG, and the static tree-graph combination method ELPIS. The source codes for LSH-APG and
  ELPIS are available at https://github.com/Jacyhust/LSH-APG and
  http://www.mi.parisdescartes.fr/~themisp/elpis, respectively.

## Datasets

Each dataset can be obtained from the following links.

| Dataset | Cardinality | Dim. | Type  | Link                                                               |
| ------- | ----------- | ---- | ----- | ------------------------------------------------------------------ |
| Deep    | 1,000,000   | 256  | Image | https://www.cse.cuhk.edu.hk/systems/hash/gqr/dataset/deep1M.tar.gz |
| Msong   | 992,272     | 420  | Audio | http://www.ifs.tuwien.ac.at/mir/msd/                               |
| Gist    | 1,000,000   | 960  | Image | http://corpus-texmex.irisa.fr/                                     |
| Color   | 5,000,000   | 282  | Image | http://cophir.isti.cnr.it                                          |
| Turing  | 100,000,000 | 100  | Text  | https://big-ann-benchmarks.com/neurips21.html                      |
| Bigann  | 100,000,000 | 128  | Image | http://corpus-texmex.irisa.fr/                                     |

The dataset and query files are stored in .fvecs format (base type is float), and the data or query
vectors are stored in raw little endian. Each vector takes 4+d\*4 bytes for .fvecs, of which the
first 4 bytes are used to store the dimension d of the vector, and the following 4 bytes for each
are used to store the values of each dimension.

The groundtruth file is stored in .ivecs format (base type is int). The groundtruth files contain,
for each query, the identifiers (vector number, starting at 0) of its k nearest neighbors, ordered
by increasing (squared euclidean) distance.

The example of dataset file is located in "Datasets".
