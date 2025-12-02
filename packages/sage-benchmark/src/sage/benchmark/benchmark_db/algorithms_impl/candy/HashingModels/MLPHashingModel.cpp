//
// Created by tony on 04/04/24.
//

#include <HashingModels/MLPHashingModel.h>
#include <cmath>
namespace CANDY {
torch::Tensor MLPHashingModel::custom_loss_function(torch::Tensor output1,
                                                    torch::Tensor output2,
                                                    torch::Tensor labels,
                                                    double margin) {

  // Calculate pairwise distance

  /* torch::Tensor pairwise_dist = torch::pow(output1 - output2, 2);
   // Calculate loss for similar and dissimilar items
   torch::Tensor positive_loss = pairwise_dist * labels; // Loss for similar items
   torch::Tensor negative_loss = - torch::sqrt(pairwise_dist) * (1 - labels); // Loss for dissimilar items

   // Combine losses
   torch::Tensor loss = positive_loss.mean() + negative_loss.mean();*/
  float expectedMaxHit = output1.size(1);
  torch::Tensor pairwise_dist = torch::matmul(output1, output2.t());
  /**
   * @brief positive loss approximates 'subject to' part, could be better
   */
  torch::Tensor positive_loss = expectedMaxHit / 2 - pairwise_dist * labels;
  /**
   * @brief negative loss approximates the 'minimize xxx' part, could be better
   */
  torch::Tensor negative_loss = pairwise_dist * (1 - labels);
  output1 = output1.sum(1);
  output2 = output2.sum(1);
  /**
   * @brief sqaure loss further regulates the seperation behavior of buckets
   */
  auto sqaureLoss = torch::pow(output1 - output1.mean(), 2) + torch::pow(output2 - output2.mean(), 2);
  return torch::sigmoid(positive_loss.mean()) + torch::sigmoid(negative_loss.mean())
      + margin * torch::sigmoid(torch::sqrt(sqaureLoss).mean());
}
void MLPHashingModel::init(int64_t inputDim, int64_t outputDim, INTELLI::ConfigMapPtr extraConfig) {
  if (extraConfig != nullptr) {
    cudaBuild = extraConfig->tryI64("cudaBuild", 0, true);
    MLTrainBatchSize = extraConfig->tryI64("MLTrainBatchSize", 128, true);
    learningRate = extraConfig->tryDouble("learningRate", 0.1, true);
    MLTrainMargin = extraConfig->tryDouble("MLTrainMargin", 2.0, true);
    hiddenLayerDim = extraConfig->tryI64("hiddenLayerDim", outputDim, true);
    MLTrainEpochs = extraConfig->tryI64("MLTrainEpochs", 30, true);
  }
  model.init(inputDim, hiddenLayerDim, outputDim);
}
void MLPHashingModel::trainModel(torch::Tensor &x1, torch::Tensor &x2, torch::Tensor &labels) {
  // Instantiate the ADAM optimizer
  torch::optim::Adam
      optimizer(model.parameters(), torch::optim::AdamOptions(learningRate)); // The learning rate is set to 0.001
  // Device
  auto devTrain = torch::kCPU;
  auto devInference = torch::kCPU;
  if (cudaBuild) {
    devTrain = torch::kCUDA;
  }
  torch::Device device(devTrain); // or torch::kCPU
  torch::Device deviceInference(devInference); // or torch::kCPU
  int64_t num_micro_batches, micro_batch_size;
  if (MLTrainBatchSize > 1) {
    num_micro_batches = x1.size(0) / MLTrainBatchSize;
    micro_batch_size = MLTrainBatchSize;
  } else {
    num_micro_batches = 1;
    micro_batch_size = x1.size(0);
  }
  int64_t epochDiv = MLTrainEpochs / 10;
  int64_t maxIdx = x1.size(0);
  // Example training loop
  model.to(device);
  torch::manual_seed(999);
  for (int64_t epoch = 0; epoch != MLTrainEpochs; ++epoch) {
    model.train();
    torch::Tensor loss;
    double total_loss = 0.0;
    for (int64_t mb = 0; mb < num_micro_batches; ++mb) {
      // Calculate start and end indices for the current micro-batch
      int64_t start_idx = mb * micro_batch_size;
      int64_t end_idx = start_idx + micro_batch_size;
      if (end_idx > maxIdx) {
        end_idx = maxIdx;
      }
      // Slice the tensors to get the current micro-batch
      auto mb_x1 = x1.slice(/*dim=*/0, start_idx, end_idx).to(device);
      auto mb_x2 = x2.slice(/*dim=*/0, start_idx, end_idx).to(device);
      auto mb_labels = labels.slice(/*dim=*/0, start_idx, end_idx).to(device);
      // Forward pass for the current micro-batch
      auto output1 = model.forward(mb_x1);
      auto output2 = model.forward(mb_x2);
      // Compute loss for the current micro-batch
      auto loss = custom_loss_function(output1, output2, mb_labels, MLTrainMargin);
      // Backward pass
      optimizer.zero_grad(); // Zero gradients (do this once per batch, not per micro-batch)
      loss.backward(); // Accumulate gradients over all micro-batches
      total_loss += loss.item<double>();
    }
    if (epoch % epochDiv == 1) {
      std::cout << "Epoch [" << (epoch + 1) << "/" << MLTrainEpochs << "], Loss: " << (total_loss / num_micro_batches)
                << std::endl;
    }
    // Optimization step (after processing all micro-batches)
    optimizer.step();
  }
  model.to(deviceInference);
}

void MLPHashingModel::fineTuneModel(torch::Tensor &x1,
                                    torch::Tensor &x2,
                                    torch::Tensor &labels,
                                    int64_t epochs,
                                    double lr) {
  // Instantiate the ADAM optimizer
  torch::optim::Adam
      optimizer(model.parameters(), torch::optim::AdamOptions(lr)); // The learning rate is set to 0.001
  // Device
  auto devTrain = torch::kCPU;
  auto devInference = torch::kCPU;
  if (cudaBuild) {
    devTrain = torch::kCUDA;
  }
  torch::Device device(devTrain); // or torch::kCPU
  torch::Device deviceInference(devInference); // or torch::kCPU
  int64_t num_micro_batches, micro_batch_size;
  if (MLTrainBatchSize > 1) {
    num_micro_batches = x1.size(0) / MLTrainBatchSize;
    micro_batch_size = MLTrainBatchSize;
  } else {
    num_micro_batches = 1;
    micro_batch_size = x1.size(0);
  }
  int64_t epochDiv = MLTrainEpochs / 10;
  int64_t maxIdx = x1.size(0);
  // Example training loop
  model.to(device);
  torch::manual_seed(999);
  for (int64_t epoch = 0; epoch != epochs; ++epoch) {
    model.train();
    torch::Tensor loss;
    double total_loss = 0.0;
    for (int64_t mb = 0; mb < num_micro_batches; ++mb) {
      // Calculate start and end indices for the current micro-batch
      int64_t start_idx = mb * micro_batch_size;
      int64_t end_idx = start_idx + micro_batch_size;
      if (end_idx > maxIdx) {
        end_idx = maxIdx;
      }
      // Slice the tensors to get the current micro-batch
      auto mb_x1 = x1.slice(/*dim=*/0, start_idx, end_idx).to(device);
      auto mb_x2 = x2.slice(/*dim=*/0, start_idx, end_idx).to(device);
      auto mb_labels = labels.slice(/*dim=*/0, start_idx, end_idx).to(device);
      // Forward pass for the current micro-batch
      auto output1 = model.forward(mb_x1);
      auto output2 = model.forward(mb_x2);
      // Compute loss for the current micro-batch
      auto loss = custom_loss_function(output1, output2, mb_labels, MLTrainMargin);
      // Backward pass
      optimizer.zero_grad(); // Zero gradients (do this once per batch, not per micro-batch)
      loss.backward(); // Accumulate gradients over all micro-batches
      total_loss += loss.item<double>();
    }
    if (epoch % epochDiv == 1) {
      std::cout << "Epoch [" << (epoch + 1) << "/" << MLTrainEpochs << "], Loss: " << (total_loss / num_micro_batches)
                << std::endl;
    }
    // Optimization step (after processing all micro-batches)
    optimizer.step();
  }
  model.to(deviceInference);
}
torch::Tensor MLPHashingModel::hash(torch::Tensor input) {
  return model.forward(input);
}
} // CANDY
