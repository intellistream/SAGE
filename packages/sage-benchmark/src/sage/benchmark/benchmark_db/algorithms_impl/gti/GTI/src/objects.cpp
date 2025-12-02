// Data (query) objects
// Created by Ruiyao Ma on 24-01-30

#include "objects.h"

// Load data
void Objects::loadData(char *file)
{
    std::ifstream in(file, std::ios::binary);
    if (!in.is_open())
    {
        std::cout << "open file error" << std::endl;
        exit(-1);
    }
    in.read((char *)&dim, 4);
    in.seekg(0, std::ios::end);
    std::ios::pos_type ss = in.tellg();
    size_t fsize = (size_t)ss;
    num = (unsigned)(fsize / (dim + 1) / 4);
    // num = 10000000;
    objects = new float[(size_t)num * (size_t)dim];

    in.seekg(0, std::ios::beg);
    for (size_t i = 0; i < num; i++)
    {
        in.seekg(4, std::ios::cur);
        in.read((char *)(objects + i * dim), dim * 4);
    }
    in.close();
}

// Load data in vector format
void Objects::loadDataVec(char *file)
{
    std::ifstream in(file, std::ios::binary);
    if (!in.is_open())
    {
        std::cout << "open file error" << std::endl;
        exit(-1);
    }
    in.read((char *)&dim, 4);
    in.seekg(0, std::ios::end);
    std::ios::pos_type ss = in.tellg();
    size_t fsize = (size_t)ss;
    num = (unsigned)(fsize / (dim + 1) / 4);
    // num = 10000000;
    vecs.resize(num, std::vector<float>(dim));

    in.seekg(0, std::ios::beg);
    for (size_t i = 0; i < num; i++)
    {
        in.seekg(4, std::ios::cur);
        in.read((char *)(vecs[i].data()), dim * 4);
    }

    // for (unsigned i = 0; i < 3; i++)
    // {
    //     for (unsigned j = 0; j < 5; j++)
    //     {
    //         std::cout << vecs[i][j] << " ";
    //     }
    //     std::cout << std::endl;
    // }
    // std::cout << std::endl;

    in.close();
}

// Load data in vector format
void Objects::loadDataVec(char *file, unsigned m)
{
    std::ifstream in(file, std::ios::binary);
    if (!in.is_open())
    {
        std::cout << "open file error" << std::endl;
        exit(-1);
    }
    in.read((char *)&dim, 4);
    in.seekg(0, std::ios::end);
    std::ios::pos_type ss = in.tellg();
    size_t fsize = (size_t)ss;
    size_t num_full = (unsigned)(fsize / (dim + 1) / 4);

    size_t num_load = m < num_full ? m : num_full;
    vecs.resize(num_load, std::vector<float>(dim));

    in.seekg(0, std::ios::beg);
    for (size_t i = 0; i < num_load; i++)
    {
        in.seekg(4, std::ios::cur);
        in.read((char *)(vecs[i].data()), dim * 4);
        if (in.eof())
            break;
    }
    num = num_load;

    in.close();
}

void Objects::loadDataVecB(char *file, size_t m)
{
    std::ifstream in(file, std::ios::binary);
    if (!in.is_open())
    {
        std::cout << "open file error" << std::endl;
        exit(-1);
    }
    in.read((char *)&dim, 4);

    in.seekg(0, std::ios::end);
    std::ios::pos_type ss = in.tellg();
    size_t fsize = (size_t)ss;
    size_t num_full = fsize / (dim + 4);

    size_t num_load = m < num_full ? m : num_full;
    vecs.resize(num_load, std::vector<float>(dim));

    in.seekg(0, std::ios::beg);
    for (size_t i = 0; i < num_load; i++)
    {
        in.seekg(4, std::ios::cur);

        std::vector<unsigned char> temp(dim);
        in.read((char *)(temp.data()), dim);
        for (size_t j = 0; j < dim; j++)
        {
            vecs[i][j] = static_cast<float>(temp[j]);
        }

        if (in.eof())
            break;
    }

    num = num_load;

    for (unsigned i = 0; i < 3; i++)
    {
        for (unsigned j = 0; j < 5; j++)
        {
            std::cout << vecs[i][j] << " ";
        }
        std::cout << std::endl;
    }
    std::cout << std::endl;

    in.close();
}

void Objects::release()
{
    if (objects != NULL)
    {
        delete this->objects;
        this->objects = NULL;
    }
    if (!vecs.empty())
    {
        for (unsigned i = 0; i < vecs.size(); i++)
        {
            std::vector<float>().swap(vecs[i]);
        }
        std::vector<std::vector<float>>().swap(vecs);
    }
}
