// Ground truth
// Created by Ruiyao Ma on 24-03-08

#pragma once
#include <iostream>
#include <fstream>
#include <algorithm>
#include <queue>
#include "neighbor.h"

// Ground truth
class GroundTruth
{
public:
    unsigned dim;                              // Dimension
    unsigned num;                              // Size
    std::vector<std::vector<int>> objects_int; // Objects

    GroundTruth(){};
    ~GroundTruth(){};
    void loadGT(char *file);                  // Load ground truth
    float getRecall(NN &results, unsigned k); // Compute recall
};
