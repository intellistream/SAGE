// Data (query) objects
// Created by Ruiyao Ma on 24-01-30

#pragma once
#include <iostream>
#include <fstream>
#include <vector>
#include <limits>
const float maxCharAsFloat = 1.0f / 255.0f;

// Data (query) objects
class Objects
{
public:
    // Parameters
    unsigned dim;                         // Data dimension
    unsigned num;                         // Data size
    unsigned type;                        // Distance metric type
    float *objects;                       // Data objects
    std::vector<std::vector<float>> vecs; // Data objects in vector format

    // Functions
    Objects(){};
    ~Objects(){};
    void loadData(char *file);                  // Load data
    void loadDataVec(char *file);               // Load data in vector format
    void loadDataVec(char *file, unsigned num); // Load data in vector format
    void loadDataVecB(char *file, size_t m);    // Load data in vector format for the first m vectors in .bvecs format
    void release();                             // Release data
};
