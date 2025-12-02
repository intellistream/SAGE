#ifndef CANDY_LSHAPGINDEX_DIVEGRAPH_H
#define CANDY_LSHAPGINDEX_DIVEGRAPH_H
#pragma once
#include <LSHAPGIndex/e2lsh.h>
#include <LSHAPGIndex/space_l2.h>
#include <algorithm>
#include <random>
#include <mutex>
#include <boost/math/distributions/chi_squared.hpp>
#include <torch/torch.h>
#if _HAS_CXX17
#include <shared_mutex>
typedef std::shared_mutex mp_mutex;
//In C++17 format, read_lock can be shared
typedef std::shared_lock<std::shared_mutex> read_lock;
typedef std::unique_lock<std::shared_mutex> write_lock;
#else
typedef std::mutex mp_mutex;
//Not in C++17 format, read_lock is the same as write_lock and can not be shared
typedef std::unique_lock<std::mutex> read_lock;
typedef std::unique_lock<std::mutex> write_lock;
#endif // _HAS_CXX17

struct Node2
{
private:
public:
	int id = 0;
	Res* neighbors = nullptr;
	int in = 0;
	int out = 0;
	//int nextFill = -1;
public:
	bool* idxs = nullptr;
	std::unordered_set<int> remainings;

	Node2() {}
	Node2(int pId) :id(pId) {}
	Node2(int pId, Res* ptr) :id(pId), neighbors(ptr) {

	}

	void increaseIn() { ++in; }
	void decreaseIn() { --in; }
	void setOut(int out_) { out = out_; }
	int size() { return out; }
	void insertSafe(int pId, float dist_, int idx) {
		neighbors[idx] = Res(dist_, pId);
	}
	bool findSmaller(float dist_) {
		return dist_ < neighbors[0].dist;
	}

	bool findGreater(float dist_) {
		return dist_ > neighbors[0].dist;
	}

	inline void insert(float dist_, int pId)
	{
        //printf("out=%d ", out);
        if(id==107){
          is_107();
        }
        neighbors[out++] = Res(dist_, pId);
        if(id==107){
          is_107();
        }
		std::push_heap(neighbors, neighbors + out);
if(id==107){
          is_107();
        }
	}

    inline void is_107(){
      return;
    }

	inline void insert(int pId, float dist_)
	{
		neighbors[out++] = Res(dist_, pId);
		std::push_heap(neighbors, neighbors + out);
	}

	inline int& erase()
	{
		std::pop_heap(neighbors, neighbors + out);
		--out;
		return neighbors[out].id;
	}


	inline bool isFull(int maxT_) {
		return out > maxT_;
	}
	inline void reset(int T_) {
		out = 0;
		in = 0;
	}

	int& operator[](int i) const
	{
		return neighbors[i].id;
	}
	Res& getNeighbor(int i) {
		return neighbors[i];
	}

	inline void readFromFile(std::ifstream& in_)
	{
		in_.read((char*)&id, sizeof(int));
		int nnSize = -1;
		in_.read((char*)&nnSize, sizeof(int));
		in_.read((char*)neighbors, sizeof(Res) * nnSize);
		in_.read((char*)&in, sizeof(int));
		in_.read((char*)&out, sizeof(int));
		out = nnSize;
	}

	inline void writeToFile(std::ofstream& out_)
	{
		out_.write((char*)&id, sizeof(int));
		int nnSize = out;
		out_.write((char*)&(nnSize), sizeof(int));
		out_.write((char*)neighbors, sizeof(Res) * nnSize);
		out_.write((char*)&(in), sizeof(int));
		out_.write((char*)&(out), sizeof(int));
	}
};

using minTopResHeap = std::vector<std::priority_queue<Res, std::vector<Res>, std::greater<Res>>>;
typedef std::priority_queue<std::pair<Res, int>, std::vector<std::pair<Res, int>>, std::greater<std::pair<Res, int>>> entryHeap;

//using namespace threadPoollib;


class divGraph :public zlsh
{
private:

	std::string file;
	size_t edgeTotal = 0;

	std::default_random_engine ng;
	std::uniform_int_distribution<uint64_t> rnd = std::uniform_int_distribution<uint64_t>(0, (uint64_t)-1);
	std::vector<int> records;
	int clusterFlag = 0;

	void oneByOneInsert();

	void refine();
	void buildExact(Preprocess* prep);
	void buildExactLikeHNSW(Preprocess* prep);
	void buildChunks();
	void insertPart(int pId, int ep, int mT, int mC, std::vector<std::vector<Res>>& partEdges);

public:
	//Only for construction, not saved
	int maxT = -1;
	int unitL = 40;
	int time_append = 0;
	std::atomic<size_t> compCostConstruction{ 0 };
	std::atomic<size_t> pruningConstruction{ 0 };
    void appendTensor(torch::Tensor &t,Preprocess* prep);
    void appendHash(float **newData,int64_t oldSize,int64_t newSize);
	float indexingTime = 0.0f;
	std::unordered_set<uint64_t> foundEdges;
	//std::vector<int> checkedArrs;
	int efC = 40;
	float coeff = 0.0f;
	float coeffq = 0.0f;
	std::vector<Res> linkListBase;
	//
	int T = -1;
	int step = 10;
	int nnD = 0;
	int lowDim = -1;
	float** myData = nullptr;
	std::string flagStates;
	std::vector<Node2*> linkLists;

	threadPoollib::VisitedListPool* visited_list_pool_ = nullptr;
	std::vector<mp_mutex> link_list_locks_;
	std::vector<mp_mutex> hash_locks_;
	mp_mutex hash_lock;
	int ef = -1;
	int first_id = 0;
	uint64_t getKey(int u, int v);
	inline constexpr uint64_t getKey(tPoints& tp) const noexcept { return *(uint64_t*)&tp; }
public:
	std::string getFilename() const { return file; }
	void knn(queryN* q) override;
	//void knn(queryN* q);
	void knnHNSW(queryN* q);
	void insertHNSW(int pId);
	//int searchLSH(int pId, std::vector<zint>& keys, std::priority_queue<Res>& candTable, threadPoollib::vl_type* checkedArrs_local, threadPoollib::vl_type tag);
	int searchLSH(int pId, std::vector<zint>& keys, std::priority_queue<Res>& candTable, std::unordered_set<int>& checkedArrs_local, threadPoollib::vl_type tag);
	//int searchLSH(std::vector<zint>& keys, std::priority_queue<Res>& candTable, threadPoollib::vl_type* checkedArrs_local, threadPoollib::vl_type tag);
	//int searchLSH(std::vector<zint>& keys, std::priority_queue<Res>& candTable);
	void insertLSHRefine(int pId);
	//int searchInBuilding(int pId, int ep, Res* arr, int& size_res);
	int searchInBuilding(int p, std::priority_queue<Res, std::vector<Res>, std::greater<Res>>& eps, Res* arr, int& size_res, std::unordered_set<int>& checkedArrs_local, threadPoollib::vl_type tag);
	void chooseNN_simple(Res* arr, int& size_res);
	void chooseNN_div(Res* arr, int& size_res);
	void chooseNN(Res* arr, int& size_res);
	void chooseNN_simple(Res* arr, int& size_res, Res new_res);
	void chooseNN_div(Res* arr, int& size_res, Res new_res);
	void chooseNN(Res* arr, int& size_res, Res new_res);
	void bestFirstSearchInGraph(queryN* q, std::string& stateFlags, entryHeap& pqEntries);
	void showInfo(Preprocess* prep);
	void traverse();
	void save(const std::string& file) override;
public:
	divGraph(Preprocess& prep, Parameter& param_, const std::string& file_, int T_,int efC_, double probC = 0.95, double probQ = 0.99);
	divGraph(Preprocess* prep, const std::string& path, double probQ = 0.99);
    divGraph(Preprocess& prep, Parameter& param_, int T_,int efC_, double probC = 0.95, double probQ = 0.99);
};
std::vector<queryN*> search_candy(float c, int k, divGraph* myGraph, Preprocess& prep, float beta, int qType);

#endif
