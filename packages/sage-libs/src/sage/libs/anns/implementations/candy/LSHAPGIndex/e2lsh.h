#pragma once
#include <LSHAPGIndex/def.h>
#include <LSHAPGIndex/Preprocess.h>
#include <LSHAPGIndex/basis.h>
#include <cmath>
#include <assert.h>
#include <unordered_map>
#include <vector>
#include <queue>
#include <map>
#include <unordered_set>
#include <LSHAPGIndex/GenericTool.h>
#include <torch/torch.h>
//
// One of these three settings should be set externally (by the compiler).
//
#define RANDOM_MAP_HASHTABLE //Use random coeffection to map k-d hash values to 1-d
//#define BIJECTION_HASHTABLE

class queryN
{
public:
	// the parameter "c" in "c-ANN"
	float c;
	//which chunk is accessed
	//int chunks;

	//float R_min = 4500.0f;//mnist
	//float R_min = 1.0f;
	float init_w = 1.0f;

	float* queryPoint = NULL;
	float* hashval = NULL;
	float** myData = NULL;
	int dim = 1;

	int UB = 0;
	float minKdist = FLT_MAX;
	// Set of points sifted
	std::priority_queue<Res> resHeap;

	//std::vector<int> keys;

public:
	// k-NN
	unsigned k = 1;
	// Indice of query point in dataset. Be equal to -1 if the query point isn't in the dataset.
	unsigned flag = -1;

	float beta = 0;

	unsigned cost = 0;

	//#access;
	int maxHop = -1;
	//
	unsigned prunings = 0;
	//cost of each partition
	std::vector<int> costs;
	//
	float timeTotal = 0;
	//
	float timeHash = 0;
	//
	float timeSift = 0;

	float timeVerify = 0;
	// query result:<indice of ANN,distance of ANN>
	std::vector<Res> res;

public:
	queryN(unsigned id, float c_, unsigned k_, Preprocess& prep, float beta);
    queryN( float c_, unsigned k_,float **dbStore, torch::Tensor &query,float beta_);

	//void search();

	~queryN() {}
};

class hashBase
{
protected:
	std::string index_file;
public:
	int N = 0;
	int dim = 0;
	// Number of hash functions
	int S = 0;
	int L = 0;
	int K = 0;
	float W = 0.0f;

	float** hashval = NULL;
	std::vector<float> hashMins, hashMaxs;
	HashParam hashPar;
public:
	hashBase(Preprocess& prep_, Parameter& param_, const std::string& file);
	hashBase();
	hashBase(hashBase* hash_);
	void setHash();
	float* calHash(float* point);
	void getHash(Preprocess& prep);

	virtual void getIndexes() = 0;
	//bool isBuilt(const std::string& file);
	//virtual void save(const std::string& file) override {}
	~hashBase();
};

class e2lsh :public hashBase
{
private:
	std::string index_file;
public:
	//Weight
	std::vector< std::vector<int> > weights;
	// Index structure
	std::vector< std::unordered_multimap<int, int> > hashTable;
public:
	e2lsh(hashBase* hash_) :hashBase(hash_) {}
	e2lsh(Preprocess& prep_, Parameter& param_, const std::string& file);
	void getIndexes();
	bool isBuilt(const std::string& file);
	void knn(queryN* q);
	~e2lsh() {}
};

using zint = uint64_t;
const int _ZINT_LEN = sizeof(zint) * 8;



//
#define USE_LCCP //Use LCCP to sort the entries

struct posInfo
{
	//std::vector<std::multimap<zint, int>::iterator> pos;
	int id = -1;
	int dist = -1;
	bool operator < (const posInfo& rhs) const {
#ifdef USE_LCCP
		return dist < rhs.dist;
#else
		return dist < rhs.dist;
#endif // USE_LCCP
	}
	posInfo() {}
	posInfo(int id_, int l_) :id(id_), dist(l_) {}
};

class zlsh :public hashBase
{
private:
	std::string index_file;

public:
	int u = 0;//u bits per hash value
	// Index structure: RB-Tree

public:
	zint getZ(float* _h);
	zint getZ(int* _h);
	void normalizeHash();
	std::vector< std::multimap<zint, int> > hashTables;
public:
	zlsh() = default;
	zlsh(Preprocess& prep_, Parameter& param_, const std::string& file, bool notInheritance = false);
	zlsh(const std::string& file);
	zlsh(hashBase* hash_) :hashBase(hash_) {}
	void getIndexes();
	int getLLCP(zint k1, zint k2);
	virtual void save(const std::string& file);
	int getLevel(zint k1, zint k2);
	virtual void knn(queryN* q);
	void knnBestFirst(queryN* q);
	void testLLCP();
	//bool isBuilt(const std::string& file);
	~zlsh() {}
};
