// MGT node
// Created by Ruiyao Ma on 24-02-23

#pragma once
#include <iostream>
#include <math.h>
#include <eigen3/Eigen/Dense>

class Distance
{
public:
    Distance(){};
    ~Distance(){};

    float getDis(float *a, float *b, unsigned type, unsigned dim);  // Compute distance
    float getDisP(float *a, float *b, unsigned type, unsigned dim); // Conpute distance in parallel
};
