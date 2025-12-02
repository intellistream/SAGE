// Ground truth
// Created by Ruiyao Ma on 24-03-09

#include "ground_truth.h"

// Load Ground truth
void GroundTruth::loadGT(char *file)
{
    std::ifstream infile(file, std::ios::binary);
    if (!infile.is_open())
    {
        std::cerr << "Error opening file: " << file << std::endl;
        return;
    }

    while (true)
    {
        int num_elements;
        infile.read(reinterpret_cast<char *>(&num_elements), sizeof(int));
        if (infile.eof())
            break;

        std::vector<int> current_topk(num_elements);
        infile.read(reinterpret_cast<char *>(current_topk.data()), num_elements * sizeof(int));

        objects_int.push_back(current_topk);
    }

    num = objects_int.size();

    infile.close();
}

// Compute recall
float GroundTruth::getRecall(NN &results, unsigned k)
{
    float recall = 0;
    for (unsigned i = 0; i < num; i++)
    {
        for (unsigned j = 0; j < k; j++)
        {
            int id = results[i][j].id;
//            std::cout << "id = " << id <<std::endl;
            auto ptr = std::find(objects_int[i].begin(), objects_int[i].begin() + k, id);
            if (ptr != objects_int[i].begin() + k)
                recall++;
        }
    }
    recall = recall / (num * k);
    return recall;
}
