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
#include <algorithm>
#include <omp.h>
#define E 2.718281746
#define PI 3.1415926

#define min(a,b)            (((a) < (b)) ? (a) : (b))
#define max(a,b)            (((a) > (b)) ? (a) : (b))

Preprocess::Preprocess(const std::string& path, const std::string& ben_file_)
{
	lsh::timer timer;
	std::cout << "LOADING DATA..." << std::endl;
	timer.restart();
	load_data(path);
	std::cout << "LOADING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	data_file = path;
	ben_file = ben_file_;
	if (data.N > 500) {
		ben_create();
	}
}

Preprocess::Preprocess(const std::string& path, const std::string& ben_file_, float beta_)
{

	hasT = true;
	beta = beta_;
	lsh::timer timer;
	std::cout << "LOADING DATA..." << std::endl;
	timer.restart();
	load_data(path);
	std::cout << "LOADING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	data_file = path;
	ben_file = ben_file_;
	if (data.N > 1000) {
		ben_create();
	}
}

Preprocess::Preprocess(uint64_t vecDim){
	data.N  = 0;
	data.dim = vecDim;
}


void Preprocess::insert_data(float* new_data, uint64_t n){
	auto old_data = data.val;
	data.val = new float* [data.N+n];
	for(int i=0; i<data.N; i++){
		data.val[i] = old_data[i];
	}
	for(int i=data.N; i<data.N+n; i++){
		data.val[i] = new float[data.dim];
		for(int j=0; j<data.dim; j++){
			data.val[i][j] = new_data[(i-data.N)*data.dim + j];
		}
	}
	data.N += n;
}

void Preprocess::load_data(const std::string& path)
{
	std::string file = path + "_new";
	std::ifstream in(file.c_str(), std::ios::binary);
	while (!in) {
		printf("Fail to find data file!\n");
		exit(0);
	}

	unsigned int header[1] = {};
	assert(sizeof header == 1 * 4);
	in.read((char*)header, sizeof(header));
	printf("dim = %d\n", header[0]);
	data.N = 100000;
	data.dim = 768;

	data.val = new float* [data.N];
	for (int i = 0; i < data.N; ++i) {
		data.val[i] = new float[data.dim];
		//in.seekg(sizeof(float), std::ios::cur);
		in.read((char*)data.val[i], sizeof(float) * data.dim);
	}

	//data.val = new float* [data.N];
	//float* dataBase = new float[data.N * data.dim];
	//in.read((char*)dataBase, sizeof(float) * (size_t)data.N * data.dim);
	//for (int i = 0; i < data.N; ++i) {
	//	data.val[i] = dataBase + i * data.dim;
	//	//in.seekg(sizeof(float), std::ios::cur);
	//	//in.read((char*)data.val[i], sizeof(float) * header[2]);
	//}
	int MaxQueryNum = 200;
	data.query = data.val;
	data.val = &(data.query[MaxQueryNum]);
	data.N -= MaxQueryNum;

	//std::cout << "Load from new file: " << file << "\n";
	std::cout << "N=    " << data.N << "\n";
	std::cout << "dim=  " << data.dim << "\n\n";

	in.close();
}

#if defined(__GNUC__) && (__GNUC__ >= 4)
#define PREP_memcpy(dst, src, size) __builtin_memcpy(dst, src, size)
#else
#define PREP_memcpy(dst, src, size) memcpy(dst, src, size)
#endif
void  Preprocess::load_data(torch::Tensor &t) {
  data.N = t.size(0);
  data.dim = t.size(1);
  data.val = new float* [data.N];
  for (int i = 0; i < data.N; i++) {
    data.val[i] = new float[data.dim];
    //in.seekg(sizeof(float), std::ios::cur);
    auto rowI=t.slice(0,i,i+1).contiguous();
    auto dataRowI= rowI.data_ptr<float>();
    PREP_memcpy(data.val[i],dataRowI,data.dim*sizeof(float));
  }

  //data.val = new float* [data.N];
  //float* dataBase = new float[data.N * data.dim];
  //in.read((char*)dataBase, sizeof(float) * (size_t)data.N * data.dim);
  //for (int i = 0; i < data.N; ++i) {
  //	data.val[i] = dataBase + i * data.dim;
  //	//in.seekg(sizeof(float), std::ios::cur);
  //	//in.read((char*)data.val[i], sizeof(float) * header[2]);
  //


}
struct Tuple
{
	unsigned id;
	float dist;
};

bool comp(const Tuple& a, const Tuple& b)
{
	return a.dist < b.dist;
}

void Preprocess::ben_make()
{
	int MaxQueryNum = min(200, (int)data.N - 201);
	benchmark.N = MaxQueryNum, benchmark.num = 100;

	benchmark.N += 200;

	benchmark.indice = new int* [benchmark.N];
	benchmark.dist = new float* [benchmark.N];
	for (unsigned j = 0; j < benchmark.N; j++) {
		benchmark.indice[j] = new int[benchmark.num];
		benchmark.dist[j] = new float[benchmark.num];
	}

	lsh::progress_display pd(benchmark.N);

//#pragma omp parallel for num_threads(100)
	for (int j = 0; j < benchmark.N; j++)
	{
		std::vector<Tuple> dists(data.N);

		for (unsigned i = 0; i < data.N; i++)
		{
			dists[i].id = i;
			dists[i].dist = cal_distSqrt(data.val[i], data.query[j], data.dim);
		}

		sort(dists.begin(), dists.end(), comp);
		for (unsigned i = 0; i < benchmark.num; i++)
		{
			benchmark.indice[j][i] = (int)dists[i].id;
			benchmark.dist[j][i] = dists[i].dist;
		}
		++pd;
	}
}

void Preprocess::ben_save()
{
	std::ofstream out(ben_file.c_str(), std::ios::binary);
	out.write((char*)&benchmark.N, sizeof(unsigned));
	out.write((char*)&benchmark.num, sizeof(unsigned));

	for (unsigned j = 0; j < benchmark.N; j++) {
		out.write((char*)&benchmark.indice[j][0], sizeof(int) * benchmark.num);
	}

	for (unsigned j = 0; j < benchmark.N; j++) {
		out.write((char*)&benchmark.dist[j][0], sizeof(float) * benchmark.num);
	}

	out.close();
}

//Be cautious to use!!!!!!!!!!!!!!!!
//Please delete the sentence that uses this function after using it!!!!
void Preprocess::ben_correct()
{
	std::ofstream out(ben_file.c_str(), std::ios::binary);
	out.write((char*)&benchmark.N, sizeof(unsigned));
	out.write((char*)&benchmark.num, sizeof(unsigned));

	for (unsigned j = 0; j < benchmark.N; j++) {
		out.write((char*)&benchmark.indice[j][0], sizeof(int) * benchmark.num);
	}

	for (unsigned j = 0; j < benchmark.N; j++) {
		for (int l = 0; l < benchmark.num; ++l) {
			benchmark.dist[j][l] = sqrt(benchmark.dist[j][l]);
		}
		out.write((char*)&benchmark.dist[j][0], sizeof(float) * benchmark.num);
	}

	out.close();
	exit(0);
}

//Be cautious to use!!!!!!!!!!!!!!!!
//Please delete the sentence that uses this function after using it!!!!
void Preprocess::ben_correct_inverse()
{
	std::ofstream out(ben_file.c_str(), std::ios::binary);
	out.write((char*)&benchmark.N, sizeof(unsigned));
	out.write((char*)&benchmark.num, sizeof(unsigned));

	for (unsigned j = 0; j < benchmark.N; j++) {
		out.write((char*)&benchmark.indice[j][0], sizeof(int) * benchmark.num);
	}

	for (unsigned j = 0; j < benchmark.N; j++) {
		for (int l = 0; l < benchmark.num; ++l) {
			benchmark.dist[j][l] = (benchmark.dist[j][l]) * (benchmark.dist[j][l]);
		}
		out.write((char*)&benchmark.dist[j][0], sizeof(float) * benchmark.num);
	}

	out.close();
	exit(0);
}

void Preprocess::ben_load()
{
	std::ifstream in(ben_file.c_str(), std::ios::binary);
	in.read((char*)&benchmark.N, sizeof(unsigned));
	in.read((char*)&benchmark.num, sizeof(unsigned));

	benchmark.indice = new int* [benchmark.N];
	benchmark.dist = new float* [benchmark.N];
	for (unsigned j = 0; j < benchmark.N; j++) {
		benchmark.indice[j] = new int[benchmark.num];
		in.read((char*)&benchmark.indice[j][0], sizeof(int) * benchmark.num);
	}

	for (unsigned j = 0; j < benchmark.N; j++) {
		benchmark.dist[j] = new float[benchmark.num];
		in.read((char*)&benchmark.dist[j][0], sizeof(float) * benchmark.num);
	}
	in.close();
}

void Preprocess::ben_create()
{
	//unsigned a_test = data.N + 1;
	lsh::timer timer;
	std::ifstream in(ben_file.c_str(), std::ios::binary);
	//in.read((char*)&a_test, sizeof(unsigned));
	bool f = in.good();
	in.close();
	if (f){
		std::cout << "LOADING BENMARK..." << std::endl;
		timer.restart();
		ben_load();
		std::cout << "LOADING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	}
	else{
		std::cout << "MAKING BENMARK..." << std::endl;
		timer.restart();
		ben_make();
		std::cout << "MAKING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

		std::cout << "SAVING BENMARK..." << std::endl;
		timer.restart();
		ben_save();
		std::cout << "SAVING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

	}
}

void Preprocess::showDataset()
{
	std::vector<float> lens(data.N);
	float sqrSum = 0, vSum = 0;
	float vmin = FLT_MAX, vmax = -FLT_MAX;
	float lmin = vmin, lmax = vmax;
	for (int i = 0; i < data.N; ++i) {
		float distSqr = cal_lengthSquare(data.val[i], data.dim);
		lens[i] = sqrt(distSqr);
		sqrSum += distSqr;
		lmin = min(lmin, lens[i]);
		lmax = max(lmax, lens[i]);
		for (int j = 0; j < data.dim; ++j) {
			vSum += data.val[i][j];
			vmin = min(vmin, data.val[i][j]);
			vmax = max(vmax, data.val[i][j]);
		}
	}

	float vavg = vSum / (data.N * data.dim);
	float vstd = (sqrSum) / (data.N * data.dim) - pow(vavg, 2);
	float lSum = std::accumulate(lens.begin(), lens.end(), 0.0f);
	float lavg = lSum / data.N;
	float lstd = (sqrSum) / (data.N) - -pow(lavg, 2);

	std::cout << "min value:  " << vmin << "\n";
	std::cout << "max value:  " << vmax << "\n";
	std::cout << "std value:  " << vstd << "\n";
	std::cout << "avg value:  " << vavg << "\n";
	//std::cout << "nstd value: " << vavg << "\n";
	std::cout << "min dist:   " << lmin << "\n";
	std::cout << "max dist:   " << lmax << "\n";
	std::cout << "std dist:   " << lstd << "\n";
	std::cout << "avg dist:   " << lavg << "\n";
	//std::cout << "nstd value: " << vavg << "\n";
	exit(0);
}

Preprocess::~Preprocess()
{
	int MaxQueryNum = min(200, (int)data.N - 201);
	//clear_2d_array(data.query, data.querySize);
	clear_2d_array(data.val, data.N);
	//clear_2d_array(Dists, MaxQueryNum);
	clear_2d_array(benchmark.indice, benchmark.N);
	clear_2d_array(benchmark.dist, benchmark.N);
	delete[] SquareLen;
}

void Preprocess::set_query(float* query, int size){
	data.query_size = size;
	data.query = new float* [size];
	for(int i=0; i<size; i++){
		data.query[i]=new float[data.dim];
		for(int j=0; j<data.dim; j++){
			data.query[i][j] = query[i*data.dim+j];
		}
	}
}

Parameter::Parameter(Preprocess& prep, unsigned L_, unsigned K_, float rmin_)
{
	N = prep.data.N;
	dim = prep.data.dim;
	L = L_;
	K = K_;
	MaxSize = 5;
	R_min = rmin_;
}

Parameter::~Parameter()
{
}
