// GTI main file
// Created by Ruiyao Ma on 24-01-26

#include <chrono>
#include <string>
#include "process.h"

int main(int argc, char **argv)
{
    char *data_file = argv[1];                   // Data file
    char *query_file = argv[2];                  // Query file
    unsigned process_type = std::stoul(argv[3]); // Process type
    char *gt_file;                               // Ground truth file
    unsigned capacity_up_i = 64;                 // Upper node capacity for internal node
    unsigned capacity_up_l = 2;                  // Upper node capacity for leaf node
    int m = 16;                                  // Graph parameters
    unsigned l;                                  // L for k-NN serach
    unsigned k;                                  // k for k-NN serach
    float r;                                     // Radius for range search
    char *res_file;                              // Result file
    unsigned type = 0;                           // Distance metric type; 0 for L2-distance

    // Load data file
    std::cout << "========== Load data file ==========" << std::endl;
    Objects *data = new Objects();
    data->loadDataVec(data_file);
    data->type = type;
    std::cout << "Data dimension: " << data->dim << std::endl;
    std::cout << "Data size: " << data->num << std::endl;
    std::cout << "Distance metric type: " << data->type << std::endl;

    // Load query file
    std::cout << "========== Load query file ==========" << std::endl;
    Objects *query = new Objects();
    query->loadDataVec(query_file);
    query->type = type;
    std::cout << "Query dimension: " << query->dim << std::endl;
    std::cout << "Query size: " << query->num << std::endl;
    std::cout << "Distance metric type: " << query->type << std::endl;

    GTI *gti = new GTI();
    float time_index = 0;

    switch (process_type)
    {
    case 0:
    {
        gt_file = argv[4];                                               // Ground truth file
        l = std::stoul(argv[5]);                                         // L for k-NN serach
        k = std::stoul(argv[6]);                                         // k for k-NN serach
        res_file = argv[7];                                              // Result file
        build(gti, capacity_up_i, capacity_up_l, m, data, time_index);   // Build GTI
        searchApproKnn(query, gti, k, l, res_file, gt_file, time_index); // Approximate k-NN search
        break;
    }
    case 1:
        l = std::stoul(argv[4]);                                       // L for k-NN serach
        k = std::stoul(argv[5]);                                       // k for k-NN serach
        res_file = argv[6];                                            // Result file
        build(gti, capacity_up_i, capacity_up_l, m, data, time_index); // Build GTI
        searchExactKnn(query, gti, k, l, res_file, time_index);        // Exact k-NN search
        break;
    case 2:
        r = std::stof(argv[4]);                                        // Radius for range search
        res_file = argv[5];                                            // Result file
        build(gti, capacity_up_i, capacity_up_l, m, data, time_index); // Build GTI
        searchExactRange(query, gti, r, res_file, time_index);         // Exact range query
        break;
    case 3:
        gt_file = argv[4];                                             // Ground truth file
        res_file = argv[5];                                            // Result file
        build(gti, capacity_up_i, capacity_up_l, m, data, time_index); // Build GTI
        update(data, gti, query, res_file, gt_file, time_index);       // Update GTI
        break;
    }

    // Release memory
    std::cout << "========== Release memory ==========" << std::endl;
    data->release();
    delete data;
    data = NULL;
    query->release();
    delete query;
    query = NULL;
    delete gti;
    gti = NULL;

    return 0;
}
