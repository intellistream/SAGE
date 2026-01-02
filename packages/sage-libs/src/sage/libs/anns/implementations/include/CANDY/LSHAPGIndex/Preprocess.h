#pragma once
#include <CANDY/LSHAPGIndex/def.h>
#include <cmath>
#include <assert.h>
#include <unordered_map>
#include <string>
#include <torch/torch.h>
//#define _NOQUERY

class Preprocess
{
public:
	Data data;
	float* SquareLen = NULL;
	float** Dists = NULL;
	Ben benchmark;
	std::string data_file;
	std::string ben_file;
	bool hasT = false;
	float beta = 0.1f;

public:
	Preprocess()=default;
	Preprocess(uint64_t vecDim);
	Preprocess(const std::string& path, const std::string& ben_file_);
	Preprocess(const std::string& path, const std::string& ben_file_, float beta_);
	void load_data(const std::string& path);
    void load_data(torch::Tensor &t);
	void insert_data(float* new_data, uint64_t n);
	void set_query(float* query, int size);
	void ben_make();
	void ben_save();
	void ben_correct();
	void ben_correct_inverse();
	void ben_load();
	void ben_create();
	void showDataset();
	~Preprocess();
};

struct Dist_id
{
	unsigned id = 0;
	float dist = 0;
	bool operator < (const Dist_id& rhs) {
		return dist < rhs.dist;
	}
};

class Parameter //N,dim,S, L, K, M, W;
{
public:
	unsigned N = 0;
	unsigned dim = 0;
	// Number of hash functions
	unsigned S = 0;
	//#L Tables;
	unsigned L = 0;
	// Dimension of the hash table
	unsigned K = 0;

	float W = 1.0f;
	int MaxSize = 0;

	float R_min = 0.3f;

	Parameter(Preprocess& prep, unsigned L_, unsigned K_, float rmin_);
	~Parameter();
};
