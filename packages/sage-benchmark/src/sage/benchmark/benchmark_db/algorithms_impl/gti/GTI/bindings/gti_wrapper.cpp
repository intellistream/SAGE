#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>
#include "gti.h"
#include "objects.h"
#include "neighbor.h"
#include <vector>
#include <unordered_map>
#include <iomanip>

namespace py = pybind11;

class GTIWrapper {
private:
    GTI* gti;
    Objects* data;
    std::unordered_map<int, int> external_to_internal;  // external ID to internal ID
    std::vector<int> internal_to_external;  // internal ID to external ID
    std::vector<bool> deleted_flags;  // Mark deleted vectors

public:
    GTIWrapper() : gti(nullptr), data(nullptr) {}

    ~GTIWrapper() {
        if (gti) delete gti;
        if (data) delete data;
    }

    void setup(int max_pts, int ndim, int capacity_up_i, int capacity_up_l, int m) {
        if (gti) delete gti;
        if (data) delete data;

        gti = new GTI();
        data = new Objects();
        data->dim = ndim;
        data->num = 0;
        data->type = 0;
        data->vecs.reserve(max_pts);

        external_to_internal.clear();
        internal_to_external.clear();
        deleted_flags.clear();
    }

    void build(py::array_t<float> X, py::array_t<int> ids, int capacity_up_i, int capacity_up_l, int m) {
        auto buf_X = X.request();
        auto buf_ids = ids.request();

        if (buf_X.ndim != 2 || buf_ids.ndim != 1) {
            throw std::runtime_error("Input arrays must be 2D (X) and 1D (ids)");
        }

        int n = buf_X.shape[0];
        int dim = buf_X.shape[1];

        if (buf_ids.shape[0] != n) {
            throw std::runtime_error("Number of vectors and ids must match");
        }

        float* ptr_X = static_cast<float*>(buf_X.ptr);
        int* ptr_ids = static_cast<int*>(buf_ids.ptr);

        data->dim = dim;
        data->num = n;
        data->type = 0;
        data->vecs.clear();
        data->vecs.reserve(n);

        external_to_internal.clear();
        internal_to_external.clear();
        deleted_flags.clear();

        for (int i = 0; i < n; i++) {
            std::vector<float> vec(ptr_X + i * dim, ptr_X + (i + 1) * dim);
            data->vecs.push_back(vec);

            int external_id = ptr_ids[i];
            external_to_internal[external_id] = i;
            internal_to_external.push_back(external_id);
            deleted_flags.push_back(false);
        }

        gti->buildGTI(capacity_up_i, capacity_up_l, m, data);

    }

    void insert(py::array_t<float> X, py::array_t<int> ids) {
        auto buf_X = X.request();
        auto buf_ids = ids.request();

        if (buf_X.ndim != 2 || buf_ids.ndim != 1) {
            throw std::runtime_error("Input arrays must be 2D (X) and 1D (ids)");
        }

        int n = buf_X.shape[0];
        int dim = buf_X.shape[1];

        if (buf_ids.shape[0] != n) {
            throw std::runtime_error("Number of vectors and ids must match");
        }

        float* ptr_X = static_cast<float*>(buf_X.ptr);
        int* ptr_ids = static_cast<int*>(buf_ids.ptr);

        Objects* insert_data = new Objects();
        insert_data->dim = dim;
        insert_data->num = n;
        insert_data->type = 0;
        insert_data->vecs.clear();
        insert_data->vecs.reserve(n);

        int old_size = data->vecs.size();

        for (int i = 0; i < n; i++) {
            std::vector<float> vec(ptr_X + i * dim, ptr_X + (i + 1) * dim);
//            data->vecs.push_back(vec);
            insert_data->vecs.push_back(vec);

            int external_id = ptr_ids[i];
            int internal_index = old_size + i;

            external_to_internal[external_id] = internal_index;
            internal_to_external.push_back(external_id);
            deleted_flags.push_back(false);
        }


        gti->insertGTI(insert_data);

        delete insert_data;
    }

    void remove(py::array_t<int> ids) {
        auto buf_ids = ids.request();

        if (buf_ids.ndim != 1) {
            throw std::runtime_error("IDs array must be 1D");
        }

        int n = buf_ids.shape[0];
        int* ptr_ids = static_cast<int*>(buf_ids.ptr);

        Objects* delete_data = new Objects();
        delete_data->dim = data->dim;
        delete_data->num = 0;
        delete_data->type = 0;
        delete_data->vecs.clear();

        for (int i = 0; i < n; i++) {
            int external_id = ptr_ids[i];
            auto it = external_to_internal.find(external_id);
            if (it != external_to_internal.end()) {
                int internal_index = it->second;
                if (internal_index < data->vecs.size() && !deleted_flags[internal_index]) {
                    delete_data->vecs.push_back(data->vecs[internal_index]);
                    deleted_flags[internal_index] = true;
                    delete_data->num++;
                }
            }
        }

//        for (int i = 0; i < delete_data->num; ++i) {
//            std::cout << "Original: ";
//            for (float val : data->vecs[external_to_internal[ptr_ids[i]]]) {
//                std::cout << std::fixed << std::setprecision(4) << val << " ";
//            }
//            std::cout << "\nCopied:   ";
//            for (float val : delete_data->vecs[i]) {
//                std::cout << std::fixed << std::setprecision(4) << val << " ";
//            }
//            std::cout << "\n----\n";
//        }

        if (delete_data->num > 0) {
            gti->deleteGTI(delete_data);
        }

        delete delete_data;
    }

    std::pair<py::array_t<int>, py::array_t<float>> query(py::array_t<float> X, int k, int L, bool debug = false) {
        auto buf_X = X.request();

        if (buf_X.ndim != 2) {
            throw std::runtime_error("Query array must be 2D");
        }

        int n = buf_X.shape[0];
        int dim = buf_X.shape[1];
        float* ptr_X = static_cast<float*>(buf_X.ptr);

        auto results = py::array_t<int>({n, k});
        auto distances = py::array_t<float>({n, k});
        auto buf_results = results.request();
        auto buf_distances = distances.request();
        int* ptr_results = static_cast<int*>(buf_results.ptr);
        float* ptr_distances = static_cast<float*>(buf_distances.ptr);

        for (int i = 0; i < n; i++) {
            std::vector<Neighbor> query_results;
            float* query_vec = ptr_X + i * dim;

            gti->search(query_vec, L, k, query_results);

            for (int j = 0; j < k && j < query_results.size(); j++) {
                int internal_id = query_results[j].id;
                int external_id = -1;

                if (internal_id >= 0 && internal_id < internal_to_external.size() &&
                    !deleted_flags[internal_id]) {
                    external_id = internal_to_external[internal_id];
                }

                ptr_results[i * k + j] = external_id;
                ptr_distances[i * k + j] = query_results[j].dis;
            }

            for (int j = query_results.size(); j < k; j++) {
                ptr_results[i * k + j] = -1;
                ptr_distances[i * k + j] = std::numeric_limits<float>::max();
            }
        }

        return std::make_pair(results, distances);
    }

    int size() const {
        return data ? data->num : 0;
    }

    void debug_info() {
        std::cout << "Data size: " << (data ? data->num : 0) << std::endl;
        std::cout << "Vectors size: " << (data ? data->vecs.size() : 0) << std::endl;
        std::cout << "External to internal mapping size: " << external_to_internal.size() << std::endl;
        std::cout << "Internal to external mapping size: " << internal_to_external.size() << std::endl;

        for (int i = 0; i < std::min(10, (int)internal_to_external.size()); i++) {
            std::cout << "internal[" << i << "] -> external[" << internal_to_external[i] << "]" << std::endl;
        }
    }
};

PYBIND11_MODULE(gti_wrapper, m) {
    m.doc() = "GTI Python wrapper";

    py::class_<GTIWrapper>(m, "GTIWrapper")
        .def(py::init<>())
        .def("setup", &GTIWrapper::setup)
        .def("build", &GTIWrapper::build)
        .def("insert", &GTIWrapper::insert)
        .def("remove", &GTIWrapper::remove)
        .def("query", &GTIWrapper::query, py::arg("X"), py::arg("k"), py::arg("L"), py::arg("debug") = false)
        .def("size", &GTIWrapper::size)
        .def("debug_info", &GTIWrapper::debug_info);
}
