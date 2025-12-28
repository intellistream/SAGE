#include <LSHAPGIndex/e2lsh.h>
#include <LSHAPGIndex/Preprocess.h>
#include <LSHAPGIndex/basis.h>
#include <fstream>
#include <assert.h>
#include <random>
#include <iostream>
#include <fstream>
#include <map>
#include <ctime>
#include <sstream>
#include <numeric>

hashBase::hashBase(Preprocess& prep_, Parameter& param_,
	const std::string& file)
{
	N = param_.N;
	dim = param_.dim;
	L = param_.L;
	K = param_.K;
	S = L * K;
	W = param_.W;

	//std::cout << std::endl << "START HASHING..." << std::endl << std::endl;
	//lsh::timer timer;

	//std::cout << "SETTING HASH PARAMETER..." << std::endl;
	//timer.restart();
	//setHash();
	//std::cout << "SETTING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	//std::cout << "COMPUTING HASH..." << std::endl;
	//timer.restart();
	//getHash(prep_);
	//std::cout << "COMPUTING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	//std::cout << "BUILDING INDEX..." << std::endl;
	//std::cout << "THERE ARE " << L << " " << K << "-D HASH TABLES." << std::endl;
	//timer.restart();
	//getIndexes(prep_);
	//std::cout << "BUILDING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;
}

hashBase::hashBase()
{
}

hashBase::hashBase(hashBase* hash_)
{
	N = hash_->N;
	dim = hash_->dim;
	L = hash_->L;
	K = hash_->K;
	S = L * K;
	W = hash_->W;

}

void hashBase::setHash()
{
	hashPar.rndAs = new float* [S];
	hashPar.rndBs = new float[S];

	for (int i = 0; i < S; i++) {
		hashPar.rndAs[i] = new float[dim];
	}

	//std::mt19937 rng(int(std::time(0)));
	std::mt19937 rng(int(0));
	std::uniform_real_distribution<float> ur(0, W);
	std::normal_distribution<float> nd;//nd is a norm random variable generator: mu=0, sigma=1
	for (int j = 0; j < S; j++){
		for (int i = 0; i < dim; i++){
			hashPar.rndAs[j][i] = (nd(rng));
		}
		hashPar.rndBs[j] = (ur(rng));
	}

}

float* hashBase::calHash(float* point)
{
	float* res = new float[S];
	for (int i = 0; i < S; i++) {
		res[i] = (cal_inner_product(point, hashPar.rndAs[i], dim) + hashPar.rndBs[i]) / W;
	}
	return res;
}

void hashBase::getHash(Preprocess& prep)
{
	showMemoryInfo();
//printf("\n\ncall this with oldN=%ld N=%ld\n\n", prep.data.oldN,N);
    if(prep.data.oldN==0){
    	hashval = new float* [N];
    } else {
        auto old_hash = hashval;
        hashval = new float* [N];
        for(int i=0; i<prep.data.oldN; i++){
          hashval[i] = old_hash[i];
        }
    }

	for (int j = prep.data.oldN; j < N; j++) {
		hashval[j] = calHash(prep.data.val[j]);
	}
    for(int j=0; j<N; j++){
      //printf("hash%d=%f ", j, hashval[j]);
    }

	hashMins.resize(S);
	hashMaxs.resize(S);
	for (int j = 0; j < S; j++){
		hashMins[j] = FLT_MAX;
		hashMaxs[j] = -FLT_MAX;
		for (int i = prep.data.oldN; i < N; i++){
			if (hashMins[j] > hashval[i][j]) hashMins[j] = hashval[i][j];

			if (hashMaxs[j] < hashval[i][j]) hashMaxs[j] = hashval[i][j];
		}
	}
	showMemoryInfo();
}

hashBase::~hashBase()
{
	clear_2d_array(hashPar.rndAs, S);
	//clear_2d_array(hashpar.rndAs2, S);
	//for (int i = 0; i < L; ++i) {
	//	delete myIndexes[i];
	//}
	//delete myIndexes;
}

e2lsh::e2lsh(Preprocess& prep_, Parameter& param_,
	const std::string& file):hashBase(prep_,param_,file)
{
	//std::cout << std::endl << "START HASHING..." << std::endl << std::endl;
	//lsh::timer timer;

	//std::cout << "SETTING HASH PARAMETER..." << std::endl;
	//timer.restart();
	setHash();
	//std::cout << "SETTING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	//std::cout << "COMPUTING HASH..." << std::endl;
	//timer.restart();
printf("get hash in 2\n");
	getHash(prep_);
	//std::cout << "COMPUTING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	//std::cout << "BUILDING INDEX..." << std::endl;
	//std::cout << "THERE ARE " << L << " " << K << "-D HASH TABLES." << std::endl;
	//timer.restart();
	getIndexes();
	//std::cout << "BUILDING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;
}

bool e2lsh::isBuilt(const std::string& file)
{
	return 0;
}

void e2lsh::knn(queryN* q)
{
	lsh::timer timer;

	timer.restart();
	q->hashval = calHash(q->queryPoint);
	q->timeHash = timer.elapsed();

	timer.restart();
	//knn();
	std::vector<bool> flag_(N, false);
	std::vector<Res> candidate;
	Res res_pair;

	int UB = (int)floor(15 * L) + q->k + 1;
	UB = N + 1;
	//UB = (int)hash.param.N / 2;
	candidate.clear();
	int j;

	int test = 0;
	for (j = 0; j < L; j++)
	{
		int key = 0;
		for (int i = 0; i < K; i++)
		{
			key += weights[j][i] * (int)floor(q->hashval[K * j + i]);//(int) is not equal to floor()
		}

		auto pr = hashTable[j].equal_range(key); // pair of begin & end iterators returned
		while (pr.first != pr.second)
		{
			if (flag_[pr.first->second] == false)
			{
				//printf("%d-th Table: p.key=%d, p.id=%d,q.key=%d\n", j, pr.first->first, pr.first->second, key);
				//for (int k = 0; k < hash->K; ++k) {
				//	printf("p.key[%d]=%d,q.key[%d]=%d,weight=%d\n", k, hash->hashval[pr.first->second][j * hash->K + k], k, hashval[j * hash->K + k], hash->weights[j][k]);
				//}
				res_pair.id = pr.first->second;
				res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
				candidate.push_back(res_pair);
				flag_[pr.first->second] = true;

				//if (q->flag == 1 && test == 0) {
				//	std::cout << pr.first->second << std::endl;
				//	for (int l = 0; l < K; ++l) {
				//		printf("%f ", hashval[pr.first->second][l]);
				//	}
				//	std::cout << std::endl;
				//}

			}

			++pr.first; // Increment begin iterator
		}
		//test++;
		if (candidate.size() >= UB)
			break;
	}
	std::sort(candidate.begin(), candidate.end());
	q->cost = candidate.size();
	if (q->cost <= q->k)
		q->res.assign(candidate.begin(), candidate.end());// printf("******cost<=k\n");
	else
		q->res.assign(candidate.begin(), candidate.begin() + q->k);

	q->timeSift = timer.elapsed();

	q->timeTotal = q->timeHash + q->timeSift;
}

void e2lsh::getIndexes()
{
	hashTable.resize(L);
	weights.clear();
	std::vector<int> weight;
	int i, j, k;
	for (j = 0; j < L; j++)
	{
		weight.clear();
		weight.resize(K);
#ifdef RANDOM_MAP_HASHTABLE
		std::mt19937 rng(int(0));
		std::uniform_real_distribution<float> ur(0, N);
		for (i = 0; i < K; i++)
		{
			weight[i] = (int)(ur(rng));
		}
#else
		for (i = 0; i < K; i++)
		{
			weight[i] = 1;
		}
		for (i = param.K - 2; i > -1; --i) {
			weight[i] = weight[i + 1] * (hashMaxs[j * K + i + 1] - hashMins[j * K + i + 1] + 1) + 0;
		}
		//for (i = 0; i < K - 1; i++)
		//{
		//	for (k = 0; k <= i; k++)
		//		weight[k] *= hashMaxs[j * param.K + i + 1] - hashMins[j * param.K + i + 1] + 5;
		//}
#endif

		weights.push_back(weight);
		hashTable[j].clear();
		for (i = 0; i < N; i++)
		{
			int key = 0;
			for (k = 0; k < K; k++)
			{
				key += weight[k] * (int)floor(hashval[i][j * K + k]);
			}
			hashTable[j].insert({ key,i });
		}
	}
}

zlsh::zlsh(Preprocess& prep_, Parameter& param_,
	const std::string& file, bool notInheritance) :hashBase(prep_, param_, file)
{


	//std::cout << std::endl << "START HASHING..." << std::endl << std::endl;
	//lsh::timer timer;

	//std::cout << "SETTING HASH PARAMETER..." << std::endl;
	//timer.restart();
	setHash();
	//std::cout << "SETTING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	//std::cout << "COMPUTING HASH..." << std::endl;
	//timer.restart();
    printf("get hash in 3\n");
	getHash(prep_);
	//std::cout << "COMPUTING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	if (notInheritance) {
		index_file = file;

	//	std::cout << "BUILDING INDEX..." << std::endl;
	//	std::cout << "THERE ARE " << L << " " << K << "-D HASH TABLES." << std::endl;
	//	timer.restart();
	//	getIndexes();
	//	std::cout << "BUILDING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	//	std::cout << "SAVING LSH INDEX..." << std::endl;
	//	timer.restart();
	//	save(index_file);
	//	std::cout << "SAVING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;
	}
}

zlsh::zlsh(const std::string& file)
{
	index_file = file;
	std::ifstream in(file, std::ios::binary);
	if (!in.good()) {
		std::cout << BOLDGREEN << "WARNING:\n" << GREEN << "Could not find the LSH index file. \n"
			<< "Filename: " << file.c_str() << RESET;
		exit(-1);
	}
	std::cout << "LOADING LSH INDEX..." << std::endl;
	lsh::timer timer;

	in.read((char*)&N, sizeof(int));
	in.read((char*)&dim, sizeof(int));
	in.read((char*)&L, sizeof(int));
	in.read((char*)&K, sizeof(int));
	in.read((char*)&W, sizeof(float));
	in.read((char*)&u, sizeof(int));

	S = L * K;

	//hashval
	hashval = new float* [N];
	for (int i = 0; i < N; ++i) {
		hashval[i] = new float[S];
		in.read((char*)(hashval[i]), sizeof(float) * S);
	}

	//hashpar,hashmin,hashmax
	hashPar.rndBs = new float[S];
	hashMaxs.resize(S);
	hashMins.resize(S);
	hashPar.rndAs = new float* [S];

	in.read((char*)hashPar.rndBs, sizeof(float) * S);
	in.read((char*)&hashMins[0], sizeof(float) * S);
	in.read((char*)&hashMaxs[0], sizeof(float) * S);
	for (int i = 0; i != S; ++i) {
		hashPar.rndAs[i] = new float[dim];
		in.read((char*)hashPar.rndAs[i], sizeof(float) * dim);
	}

	//Index
	hashTables.resize(L);
	zint key;
	int pointId;
	for (int i = 0; i != L; ++i) {
		for (int j = 0; j < N; ++j) {
			in.read((char*)&(key), sizeof(zint));
			in.read((char*)&((pointId)), sizeof(int));
			hashTables[i].insert({ key,pointId });
		}
	}
	in.close();

	std::cout << "LOADING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;
}

zint zlsh::getZ(float* _h)
{
	zint res = 0;
	for (int i = u - 1; i >= 0; i--){
		int mask = 1 << i;
		for (int j = 0; j < K; j++){
			res <<= 1;
			if ((int)floor(_h[j]) & mask)
				++res;
		}
	}
	return res;
}

zint zlsh::getZ(int* _h)
{
	zint res = 0;
	for (int i = u - 1; i >= 0; i--) {
		int mask = 1 << i;
		for (int j = 0; j < K; j++) {
			res <<= 1;
			printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);printf("j=%d  ",j);
			if (_h[j] & mask)
				++res;
		}
	}
	return res;
}

void zlsh::normalizeHash()
{
	int hMax = 1 << (_ZINT_LEN / K);
	//--hMax;
	float rMax = -1;
	float* ranges = new float[S];
	for (int i = 0; i < S; ++i) {
		float b = floor(hashMins[i]);
		ranges[i] = hashMaxs[i] - b;
		if (rMax < ranges[i])rMax = ranges[i];
	}

	float oldW = W;
	float r = 1.0f;

	//r = rMax / (float)hMax;
	//W *= r;

	if (rMax > (float) hMax) {
		--hMax;
		r = rMax / (float)hMax;
		W *= r;
		rMax = hMax;
	//	std::cout << BOLDRED << "WARNING:\n" << RED << "Ranges of hash values is too LARGE. \n"
	//		<< "Please increase W at least " << rMax / (float)hMax << "times.\n" << RESET;
		//exit(-1);
	}




	//u = _ZINT_LEN / K;
	for (int i = 0; i < S; ++i) {
		//float b = (hMax - ranges[i]) / 2 - hashMins[i];
		float b = -floor(hashMins[i]);
		//b = -hashMins[i];
		hashMaxs[i] += b;
		hashMaxs[i] /= r;

		hashMins[i] += b;
		hashMins[i] /= r;

		hashPar.rndBs[i] += b * oldW;
		for (int j = 0; j < N; ++j) {
			hashval[j][i] += b;
			hashval[j][i] /= r;
		}
	}

	u = (int)floor(log(rMax) / log(2.0f)) + 1;

	//std::cout << RED << "Old W=    " << oldW
		//<< "\nNew W=    " << W
		//<< "\nIncrease  " << r << "times.\n" << RESET;
}

void zlsh::getIndexes()
{
	normalizeHash();

	hashTables.resize(L);
	for (int j = 0; j < L; j++)
	{
		for (int i = 0; i < N; i++)
		{
			zint key = getZ(hashval[i] + j * K);
			hashTables[j].insert({ key,i });
		}
	}
}

#if defined _MSC_VER
#include <intrin.h>
#endif

int zlsh::getLLCP(zint k1, zint k2)
{
	if (k1 == k2) {
		//return u * K;
		return _ZINT_LEN;
	}
	else {
#if defined(__GNUC__)
		return __builtin_clzll(k1 ^ k2);
#elif defined _MSC_VER
		return (int)_lzcnt_u64(k1 ^ k2);
#else
		std::cout << BOLDRED << "WARNING:" << RED << "getLLCP Undefined. \n" << RESET;
		exit(-1);
#endif
	}

}

void zlsh::save(const std::string& file)
{

	std::ofstream out(file, std::ios::binary);


	out.write((char*)&N, sizeof(int));
	out.write((char*)&dim, sizeof(int));
	out.write((char*)&L, sizeof(int));
	out.write((char*)&K, sizeof(int));
	out.write((char*)&W, sizeof(float));
	out.write((char*)&u, sizeof(int));

	//hashval
	for (int i = 0; i < N; ++i) {
		out.write((char*)(hashval[i]), sizeof(float) * S);
	}

	//hashpar,hashmin,hashmax
	out.write((char*)hashPar.rndBs, sizeof(float) * S);
	out.write((char*)&hashMins[0], sizeof(float) * S);
	out.write((char*)&hashMaxs[0], sizeof(float) * S);
	for (int i = 0; i != S; ++i){
		out.write((char*)hashPar.rndAs[i], sizeof(float) * dim);
	}

	for (int i = 0; i != L; ++i) {
		for (auto iter = hashTables[i].begin(); iter != hashTables[i].end(); ++iter) {
			out.write((char*)&(iter->first), sizeof(zint));
			out.write((char*)&((iter->second)), sizeof(int));
		}
	}
	out.close();
}

int zlsh::getLevel(zint k1, zint k2)
{
	if (k1 == k2) {
		return u;
	}
	else {
#if defined(__GNUC__)
		return __builtin_ctzll(k1 ^ k2) / K;
#elif defined _MSC_VER
		return (int)_tzcnt_u64(k1 ^ k2) / K;
#else
		std::cout << BOLDRED << "WARNING:" << RED << "getLLCP Undefined. \n" << RESET;
		exit(-1);
#endif
	}

}

void zlsh::knn(queryN* q)
{
	lsh::timer timer;

	timer.restart();
	q->hashval = calHash(q->queryPoint);
	q->timeHash = timer.elapsed();

	timer.restart();
	//knn();
	std::vector<bool> flag_(N, false);
	std::vector<Res> candidate;
	Res res_pair;

	int UB = (int)floor(15 * L) + q->k + 1;
	UB = N + 1;
	//UB = (int)hash.param.N / 2;
	candidate.clear();

	//std::vector<std::multimap<zint, int>::iterator> lpos(L), rpos(L);

	int test = 0;

	for (int j = 0; j < L; j++)
	{
		zint key = getZ(q->hashval + j * K);
		//auto pos = myIndexes[j].lower_bound(key);

		auto pr = hashTables[j].equal_range(key); // pair of begin & end iterators returned
		while (pr.first != pr.second)
		{
			if (flag_[pr.first->second] == false)
			{
				res_pair.id = pr.first->second;
				res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
				candidate.push_back(res_pair);
				flag_[pr.first->second] = true;

			}
			++pr.first; // Increment begin iterator
		}
		//test++;

		if (candidate.size() >= UB)
			break;
	}
	std::sort(candidate.begin(), candidate.end());
	q->cost = candidate.size();
	if (q->cost <= q->k)
		q->res.assign(candidate.begin(), candidate.end());
	else
		q->res.assign(candidate.begin(), candidate.begin() + q->k);

	q->timeSift = timer.elapsed();

	q->timeTotal = q->timeHash + q->timeSift;
}

void zlsh::knnBestFirst(queryN* q)
{
	lsh::timer timer;

	timer.restart();
	q->hashval = calHash(q->queryPoint);
	q->timeHash = timer.elapsed();

	timer.restart();
	//knn();
	std::vector<bool> flag_(N, false);
	std::vector<Res> candidate;
	Res res_pair;

	int UB = (int)floor(15 * L) + q->k + 1;
	UB = N + 1;
	UB = (int)N / 10;
	int step = 100;
	candidate.clear();

	std::vector<int> numAccess(L);

	std::vector<std::multimap<zint, int>::iterator> lpos(L), rpos(L), qpos(L);
	std::priority_queue<posInfo> lEntries, rEntries;
	for (int j = 0; j < L; j++)
	{
		zint key = getZ(q->hashval + j * K);
		qpos[j] = hashTables[j].lower_bound(key);
		if (qpos[j] != hashTables[j].begin()) {
			lpos[j] = qpos[j];
			--lpos[j];
#ifdef USE_LCCP
			lEntries.push(posInfo(j, getLLCP(lpos[j]->first, qpos[j]->first)));
#else
			lEntries.push(posInfo(j, getLevel(lpos[j]->first, qpos[j]->first)));
#endif // USE_LCCP

		}
		//
		rpos[j] = qpos[j];
		if (rpos[j] != hashTables[j].end()) {
#ifdef USE_LCCP
			rEntries.push(posInfo(j, getLLCP(rpos[j]->first, qpos[j]->first)));
#else
			rEntries.push(posInfo(j, getLevel(rpos[j]->first, qpos[j]->first)));
#endif // USE_LCCP
		}
	}

	while (!(lEntries.empty() && rEntries.empty())) {
		posInfo t;
		bool f = true;//TRUE:left; FALSE:right
		if (lEntries.empty()) f = false;
		else if (rEntries.empty()) f = true;
		else if (rEntries.top().dist > lEntries.top().dist) f = false;

		if (f) {
			t = lEntries.top();
			lEntries.pop();
			for (int i = 0; i < step; ++i) {
				++numAccess[t.id];
				res_pair.id = lpos[t.id]->second;
				if (flag_[res_pair.id] == false)
				{
					res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
					candidate.push_back(res_pair);
					flag_[res_pair.id] = true;
				}
				if (lpos[t.id] != hashTables[t.id].begin()) {
					--lpos[t.id];
				}
				else {
					break;
				}
				//--lpos[t.id];
			}

			if (lpos[t.id] != hashTables[t.id].begin()) {
#ifdef USE_LCCP
				t.dist = getLLCP(lpos[t.id]->first, qpos[t.id]->first);
#else
				t.dist = getLevel(lpos[t.id]->first, qpos[t.id]->first);
#endif // USE_LCCP
				lEntries.push(t);
			}
		}
		else {
			t = rEntries.top();
			rEntries.pop();
			for (int i = 0; i < step; ++i) {
				++numAccess[t.id];
				res_pair.id = rpos[t.id]->second;
				if (flag_[res_pair.id] == false)
				{
					res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
					candidate.push_back(res_pair);
					flag_[res_pair.id] = true;
				}
				if (++rpos[t.id] == hashTables[t.id].end()) {
					break;
				}
			}
			if (rpos[t.id] != hashTables[t.id].end()) {
#ifdef USE_LCCP
				t.dist = getLLCP(rpos[t.id]->first, qpos[t.id]->first);
#else
				t.dist = getLevel(rpos[t.id]->first, qpos[t.id]->first);
#endif // USE_LCCP
				rEntries.push(t);
			}
		}
		if (candidate.size() >= UB) break;
	}

	std::sort(candidate.begin(), candidate.end());
	q->cost = candidate.size();
	if (q->cost <= q->k)
		q->res.assign(candidate.begin(), candidate.end());
	else
		q->res.assign(candidate.begin(), candidate.begin() + q->k);

	q->timeSift = timer.elapsed();

	q->timeTotal = q->timeHash + q->timeSift;

	q->costs = numAccess;
}

queryN::queryN(unsigned id, float c_, unsigned k_, Preprocess& prep, float beta_)
{
	flag = id;
	c = c_;
	k = k_;
	beta = beta_;
	myData = prep.data.val;
	dim = prep.data.dim;
	queryPoint = prep.data.query[flag];
	//search();
}
queryN::queryN( float c_, unsigned k_,float **dbStore, torch::Tensor &query,float beta_)
{
  flag = 0;
  c = c_;
  k = k_;
  beta = beta_;
  myData = dbStore;
  dim = query.size(1);
  queryPoint = query.contiguous().data_ptr<float>();
  //search();
}
void zlsh::testLLCP()
{
	u = 2;
	std::cout << "u=         " << u << std::endl;
	K = 2;
	float a[] = { 2.1,3.8 };
	std::cout << "Z=         " << getZ(a) << std::endl;
	zint z1 = 2, z2 = 1;
	std::cout << "LLCP(4,3)= " << getLLCP(z1, z2) << std::endl;
	std::cout << "LLCP(4,4)= " << getLLCP(z1, z1) << std::endl;
}
