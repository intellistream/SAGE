// Process
// Created by Ruiyao Ma on 24-07-06

#pragma once
#include "objects.h"
#include "gti.h"
#include "ground_truth.h"

// Build GTI
void build(GTI *&gti, unsigned capacity_up_i, unsigned capacity_up_l, unsigned m, Objects *data, float &time_index);

// Approximate k-NN search
void searchApproKnn(Objects *query, GTI *gti, unsigned k, unsigned l, char *res_file, char *gt_file, float time_index);

// Exact k-NN search
void searchExactKnn(Objects *query, GTI *gti, unsigned k, unsigned l, char *res_file, float time_index);

// Exact range query
void searchExactRange(Objects *query, GTI *gti, float r, char *res_file, float time_index);

// Update GTI
void update(Objects *data, GTI *&gti, Objects *query, char *res_file, char *gt_file, float time_index);
