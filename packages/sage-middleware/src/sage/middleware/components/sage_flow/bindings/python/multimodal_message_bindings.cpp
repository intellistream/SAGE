/**
 * @file multimodal_message_bindings.cpp
 * @brief Python bindings for MultiModalMessage class
 *
 * This file provides Python bindings for the MultiModalMessage class only.
 * Exposure rules: Only MultiModalMessage is exposed with specified init, getters/setters, and repr.
 * No internal classes or operators are bound here.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <string>
#include <vector>
#include <pybind11/functional.h>

#include "../include/message/multimodal_message.hpp"
#include "../include/message/content_type.hpp"

namespace py = pybind11;

void bind_multimodal_message(py::module& m) {
    py::class_<sage_flow::MultiModalMessage>(m, "MultiModalMessage")
        .def(py::init([](const std::string& sage_uid, sage_flow::ContentType content_type, const std::string& variant, const std::vector<double>& embeddings) {
            sage_flow::MultiModalMessage msg(sage_uid, content_type, std::string(variant));
            msg.setEmbeddings(embeddings);
            return msg;
        }), py::arg("uid"), py::arg("content_type"), py::arg("variant"), py::arg("embeddings"),
             "Create a new MultiModalMessage with uid, content_type, variant (content as string), and embeddings")
        .def_property_readonly("uid", &sage_flow::MultiModalMessage::getSageUid, "Unique identifier (string)")
        .def_property("content_type", &sage_flow::MultiModalMessage::getContentType, &sage_flow::MultiModalMessage::setContentType, "Content type")
        .def_property("variant",
                      [](const sage_flow::MultiModalMessage& self) -> std::string {
                          return self.getContentAsString();
                      },
                      [](sage_flow::MultiModalMessage& self, const std::string& var) {
                          self.set_content_as_string(var);
                      },
                      "Get or set variant (content as string)")
        .def_property("embeddings",
                      [](const sage_flow::MultiModalMessage& self) -> py::list {
                          const auto& vec = self.getEmbeddings();
                          py::list result;
                          for (double val : vec) {
                              result.append(val);
                          }
                          return result;
                      },
                      [](sage_flow::MultiModalMessage& self, const py::list& py_list) {
                          std::vector<double> vec;
                          for (auto item : py_list) {
                              vec.push_back(item.cast<double>());
                          }
                          self.setEmbeddings(vec);
                      },
                      "Get or set embeddings as list of doubles")
        .def("__repr__", [](const sage_flow::MultiModalMessage& self) -> std::string {
            const auto& emb = self.getEmbeddings();
            std::string repr = "MultiModalMessage(uid='" + self.getSageUid() + "', embeddings=[";
            for (size_t i = 0; i < emb.size(); ++i) {
                repr += std::to_string(emb[i]);
                if (i < emb.size() - 1) repr += ", ";
            }
            repr += "])";
            return repr;
        });

    // Cast support for vector<double> from embeddings
    m.def("get_embeddings_vector", [](const sage_flow::MultiModalMessage& msg) -> std::vector<double> {
        return msg.getEmbeddings();
    });
}