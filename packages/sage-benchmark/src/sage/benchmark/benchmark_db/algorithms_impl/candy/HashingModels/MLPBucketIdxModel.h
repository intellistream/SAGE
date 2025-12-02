//
// Created by tony on 04/04/24.
//

#ifndef CANDY_INCLUDE_CANDY_HASHINGMODELS_MLPBKTINGMODEL_H_
#define CANDY_INCLUDE_CANDY_HASHINGMODELS_MLPBKTINGMODEL_H_
#include <torch/torch.h>
#include <iostream>
#include <Utils/ConfigMap.hpp>
#include <memory>
namespace CANDY {
/**
 * @ingroup  CANDY_lib_bottom_sub The support classes for index approaches
 * @{
 */
/***
 * @class MLPBucketIdxModel CANDY/HashingModels/MLPBucketIdxModel
 * @breif The hashing model using MLP
 */
class MLPBucketIdxModel {
 private:
// Define the LSH Projection model with two layers
  struct myMLP : torch::nn::Module {
    torch::nn::Linear inputLayer{nullptr};
    torch::nn::Linear outputLayer{nullptr};
    int64_t idxMax = 0;
    myMLP() {}
    ~myMLP() {}
    // Constructor with input_dim, hidden_dim, and output_dim
    void init(int64_t input_dim, int64_t hidden_dim, int64_t _idxMax) {
      // Initialize the input layer and register it
      inputLayer = register_module("inputLayer", torch::nn::Linear(input_dim, hidden_dim));
      // Initialize the output layer and register it
      outputLayer = register_module("outputLayer", torch::nn::Linear(hidden_dim, 1));

    }

    // Forward pass
    torch::Tensor forward(torch::Tensor x) {
      // Pass the input through the input layer followed by a ReLU activation
      x = torch::relu(inputLayer->forward(x));
      // Pass the result through the output layer
      auto tempRu = outputLayer->forward(x);
      return torch::sigmoid(tempRu);
    }
  };
  struct myMLP model;

  // Custom Loss Function, using spectral_hashing
  torch::Tensor custom_loss_function(torch::Tensor output1, torch::Tensor output2, torch::Tensor labels, double margin);
  int64_t cudaBuild = 0, hiddenLayerDim = 0, MLTrainBatchSize = 64, MLTrainEpochs = 10;
  double learningRate = 0.01, MLTrainMargin = 1.0;
 public:
  MLPBucketIdxModel() {}
  ~MLPBucketIdxModel() {}
  /**
   * @brief init the model class
   * @param inputDim the dimension of model ending input
   * @param outputDim the dimension of model ending output
   * @param extraConfig optional extra configs
   * @note accepted configurations
   * - cudaBuild whether or not use cuda to build model, I64, default 0
   * - learningRate the learning rate for training, Double, default 0.01
   * - hiddenLayerDim the dimension of hidden layer, I64, default the same as output layer
   * - MLTrainBatchSize the batch size of ML training, I64, default 64
   * - MLTrainMargin the margin value used in training, Double, default 2*0.1
   * - MLTrainEpochs the number of epochs in training, I64, default 10
   */
  virtual void init(int64_t inputDim, int64_t idxMax, INTELLI::ConfigMapPtr extraConfig);
  /**
   * @brief the training function
   * @param x1 an 2D tensor sized [n*d]
   * @param x2 an 2D tensor sized [n*d]
   * @param labels an 1D integer tensor sized n, indicating whether x1[i] is similar to x2[i]
   */
  virtual void trainModel(torch::Tensor &x1, torch::Tensor &x2, torch::Tensor &labels);
  /**
   * @brief the forward hashing function
   * @param input The input tensor
   * @return the output tensor for encoding
   */
  virtual torch::Tensor hash(torch::Tensor input);

};
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @typedef MLPBucketIdxModelPtr
 * @brief The class to describe a shared pointer to @ref  MLPBucketIdxModel
 */
typedef std::shared_ptr<class CANDY::MLPBucketIdxModel> MLPBucketIdxModelPtr;
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @def newMLPBucketIdxModel
 * @brief (Macro) To creat a new @ref MLPBucketIdxModel shared pointer.
 */
#define newMLPBucketIdxModel std::make_shared<CANDY::MLPBucketIdxModel>
/**
 * @}
 */
} // CANDY

#endif //CANDY_INCLUDE_CANDY_HASHINGMODELS_MLPHASHINGMODEL_H_
