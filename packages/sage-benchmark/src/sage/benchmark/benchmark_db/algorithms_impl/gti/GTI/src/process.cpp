#include "process.h"

// Build GTI
void build(GTI *&gti, unsigned capacity_up_i, unsigned capacity_up_l, unsigned m, Objects *data, float &time_index)
{
    std::cout << "========== Build GTI ==========" << std::endl;
    auto s = std::chrono::high_resolution_clock::now();
    gti->buildGTI(capacity_up_i, capacity_up_l, m, data);
    auto e = std::chrono::high_resolution_clock::now();
    std::chrono::duration<float> diff = e - s;
    time_index = diff.count();
    std::cout << "Time of index construction: " << time_index << "s" << std::endl;
    gti->getTreeSize();
    // double sizeInMB = gti->tree_size / (1024.0 * 1024.0);
    // std::cout << "Size of tree: " << sizeInMB << std::endl;
}

// Approximate k-NN search
void searchApproKnn(Objects *query, GTI *gti, unsigned k, unsigned l, char *res_file, char *gt_file, float time_index)
{
    // Load ground truth
    GroundTruth *gt = new GroundTruth();
    gt->loadGT(gt_file);
    gt->num = 100;

    // Query using GTI
    std::cout << "========== Search GTI ==========" << std::endl;
    query->num = 100;
    printf("query->num: %d\n", query->num);
    NN results(query->num);
    auto s = std::chrono::high_resolution_clock::now();
    for (unsigned i = 0; i < query->num; i++)
        gti->search(query->vecs[i].data(), l, k, results[i]); // Search GTI
    auto e = std::chrono::high_resolution_clock::now();
    std::chrono::duration<float> diff = e - s;
    float time_search = diff.count();
    std::cout << "Time of search: " << time_search / query->num << "s" << std::endl;

    float recall = gt->getRecall(results, k); // Load ground truth
    std::cout << "Search recall: " << recall << std::endl;

    // Save results in file
    std::cout << "========== Save results ==========" << std::endl;
    std::stringstream ss;
    ss << res_file << "cost_" << k << "_" << l << ".txt";
    std::string filename = ss.str();
    std::stringstream ss2;
    ss2 << res_file << "model";
    std::string modelname = ss2.str();
    // gti->index_hnsw->SaveModel(modelname);
    FILE *fcost = fopen(filename.c_str(), "w");
    if (!fcost)
    {
        std::cerr << "Error opening file: " << filename << std::endl;
        return;
    }
    fprintf(fcost, "%d-NN Search\n", k);
    fprintf(fcost, "Time of index construction: %f\n", time_index);
    // double sizeInMB = gti->tree_size / (1024.0 * 1024.0);
    // fprintf(fcost, "Size of tree: %f\n", sizeInMB);
    fprintf(fcost, "Search time: %f\n", time_search / query->num);
    fprintf(fcost, "Search recall: %f\n", recall);
    fflush(fcost);
    fclose(fcost);

    std::cout << "Results saved to " << filename << std::endl;
}

// Exact k-NN search
void searchExactKnn(Objects *query, GTI *gti, unsigned k, unsigned l, char *res_file, float time_index)
{
    // Query using GTI
    std::cout << "========== Exact k-NN Search Using GTI ==========" << std::endl;
    query->num = 100;
    printf("query->num: %d\n", query->num);
    NN results(query->num);
    std::chrono::duration<float> diff = std::chrono::duration<double>::zero();
    std::priority_queue<Neighbor, std::vector<Neighbor>, std::less<Neighbor>> res;
    for (unsigned i = 0; i < query->num; i++)
    {
        auto s = std::chrono::high_resolution_clock::now();
        gti->searchExactKnn(query->vecs[i].data(), l, k, results[i], res); // Search GTI
        auto e = std::chrono::high_resolution_clock::now();
        diff += e - s;

        unsigned j = 0;
        while (!res.empty())
        {
            Neighbor nn;
            nn.id = res.top().id;
            results[i][k - 1 - j] = nn;
            res.pop();
        }
    }
    float time_search = diff.count();
    std::cout << "Time of search: " << time_search / query->num << "s" << std::endl;

    // float recall = gt->getRecall(results, k); // Load ground truth
    // std::cout << "Search recall: " << recall << std::endl;

    // Save results in file
    std::cout << "========== Save results ==========" << std::endl;
    std::stringstream ss;
    ss << res_file << "cost_" << k << "_" << l << ".txt";
    std::string filename = ss.str();
    FILE *fcost = fopen(filename.c_str(), "w");
    if (!fcost)
    {
        std::cerr << "Error opening file: " << filename << std::endl;
    }
    fprintf(fcost, "%d-NN Search\n", k);
    // fprintf(fcost, "\nIndex size: %f\n", index_size);
    fprintf(fcost, "Time of index construction: %f\n", time_index);
    fprintf(fcost, "Search time: %f\n", time_search / query->num);
    // fprintf(fcost, "Search recall: %f\n", recall);
    fflush(fcost);
    fclose(fcost);

    std::cout << "Results saved to " << filename << std::endl;
}

// Exact range query
void searchExactRange(Objects *query, GTI *gti, float r, char *res_file, float time_index)
{
    // Query using GTI
    std::cout << "========== Exact Range Search Using GTI ==========" << std::endl;
    query->num = 100;
    printf("query->num: %d\n", query->num);
    NN results(query->num);
    auto s = std::chrono::high_resolution_clock::now();
    for (unsigned i = 0; i < query->num; i++)
    {
        gti->searchTreeRange(query->vecs[i].data(), r, results[i]); // Search GTI
    }
    auto e = std::chrono::high_resolution_clock::now();
    std::chrono::duration<float> diff = e - s;
    float time_search = diff.count();
    std::cout << "Time of search: " << time_search / query->num << "s" << std::endl;

    // Save results in file
    std::cout << "========== Save results ==========" << std::endl;
    std::stringstream ss;
    ss << res_file << "cost_" << r << ".txt";
    std::string filename = ss.str();
    FILE *fcost = fopen(filename.c_str(), "w");
    if (!fcost)
    {
        std::cerr << "Error opening file: " << filename << std::endl;
    }
    fprintf(fcost, "Range Search, radius = %f\n", r);
    // fprintf(fcost, "\nIndex size: %f\n", index_size);
    for (unsigned i = 0; i < query->num; i++)
        fprintf(fcost, "%d ", int(results[i].size()));
    fprintf(fcost, "\n");
    fprintf(fcost, "Time of index construction: %f\n", time_index);
    fprintf(fcost, "Search time: %f\n", time_search / query->num);
    fflush(fcost);
    fclose(fcost);

    std::cout << "Results saved to " << filename << std::endl;
}

// Update
void update(Objects *data, GTI *&gti, Objects *query, char *res_file, char *gt_file, float time_index)
{
    std::cout << "========== Update ==========" << std::endl;

    // Load ground truth
    GroundTruth *gt = new GroundTruth();
    gt->loadGT(gt_file);
    gt->num = 100;

    unsigned delete_data_size = 1000;
    Objects *delete_data = new Objects();
    delete_data->vecs.assign(data->vecs.end() - delete_data_size, data->vecs.end());
    delete_data->num = delete_data_size;
    delete_data->dim = data->dim;
    delete_data->type = data->type;

    auto s = std::chrono::high_resolution_clock::now();
    gti->insertGTI(delete_data);
    auto e = std::chrono::high_resolution_clock::now();
    std::chrono::duration<float> diff = e - s;
    float time_insert = diff.count();
    std::cout << "Insert time: " << time_insert / delete_data->num << "s" << std::endl;

    s = std::chrono::high_resolution_clock::now();
    gti->deleteGTI(delete_data);
    e = std::chrono::high_resolution_clock::now();
    diff = e - s;
    float time_delete = diff.count();
    std::cout << "Delete time: " << time_delete / delete_data->num << "s" << std::endl;

    // Query using GTI
    unsigned k = 10;
    unsigned l = 60;
    std::cout << "========== Search GTI ==========" << std::endl;
    query->num = 100;
    printf("query->num: %d\n", query->num);
    NN results(query->num);
    s = std::chrono::high_resolution_clock::now();
    for (unsigned i = 0; i < query->num; i++)
        gti->search(query->vecs[i].data(), l, k, results[i]); // Search GTI
    std::cout << "result[0].size() = " << results[0].size() << std::endl;
    e = std::chrono::high_resolution_clock::now();
    diff = e - s;
    float time_search = diff.count();
    std::cout << "Time of search: " << time_search / query->num << "s" << std::endl;

    float recall = gt->getRecall(results, k); // Load ground truth
    std::cout << "Search recall: " << recall << std::endl;

    // Save results in file
    std::cout << "========== Save results ==========" << std::endl;
    std::stringstream ss;
    ss << res_file << "cost_" << k << "_" << l << ".txt";
    std::string filename = ss.str();
    FILE *fcost = fopen(filename.c_str(), "w");
    if (!fcost)
    {
        std::cerr << "Error opening file: " << filename << std::endl;
        return;
    }
    fprintf(fcost, "%d-NN Search\n", k);
    // fprintf(fcost, "\nIndex size: %f\n", index_size);
    fprintf(fcost, "Time of index construction: %f\n", time_index);
    fprintf(fcost, "Update time:  %f\n", time_insert / delete_data->num + time_delete / delete_data->num + time_search / query->num);
    fprintf(fcost, "Search recall: %f\n", recall);
    fflush(fcost);
    fclose(fcost);

    std::cout << "Results saved to " << filename << std::endl;
}
