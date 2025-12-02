//
// Created by tony on 01/06/24.
//
#include <LSHAPGIndex/basis.h>
#include <LSHAPGIndex/divGraph.h>
#include <queue>
#include <functional>
#include <unordered_set>
#include <stdio.h>
#include <fstream>
void debug_message(int& debug);

std::vector<queryN*> search_candy(float c, int k, divGraph* myGraph, Preprocess& prep, float beta, int qType) {
  int Qnum = prep.data.query_size;
  auto results = std::vector<queryN*>(Qnum, nullptr);
  for (unsigned j = 0; j < Qnum; j++)
  {
    queryN* q = new queryN(j, c, k, prep, beta);
    //printf("searching for %dth query\n", j);
    switch (qType % 2) {
      case 0:
        myGraph->knn(q);
      break;
      case 1:
        myGraph->knnHNSW(q);
      break;
    }
    results[j] = q;

  }
  return results;
}
divGraph::divGraph(Preprocess& prep_, Parameter& param_, const std::string& file_, int T_, int efC_, double probC,double probQ) :zlsh(prep_, param_, ""), link_list_locks_(prep_.data.N)
{
  myData = prep_.data.val;
  T = T_;
  dim = prep_.data.dim;
  file = file_;
  lowDim = K;
  if (L == 0) lowDim = 0;
  maxT = 2 * T;
  //maxT = T;
  efC = 5 * T / 2;
  efC = efC_;
  visited_list_pool_ = new threadPoollib::VisitedListPool(1, N);
  unitL =max(maxT, efC);
  normalizeHash();
  double _coeff = 1.0, _coeffq = 1.0;
  if (lowDim) {
    boost::math::chi_squared chi(lowDim);
    _coeff = sqrt(boost::math::quantile(chi, probC));
    if (probQ == 1.0) _coeffq = DBL_MAX;
    else _coeffq = sqrt(boost::math::quantile(chi, probQ));
  }

#ifdef USE_SQRDIST
  _coeff = _coeff * _coeff;
	coeff = W * W / _coeff;
	_coeffq = _coeffq * _coeffq;
	coeffq = W * W / _coeffq;
#else
  coeff = W / _coeff;
  coeffq = W / _coeffq;
#endif

  lsh::timer timer;
  std::cout << "CONSTRUCTING GRAPH..." << std::endl;
  timer.restart();
  oneByOneInsert();
  std::cout << "CONSTRUCTING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;
  indexingTime = timer.elapsed();

  std::cout << "SAVING GRAPH..." << std::endl;
  timer.restart();
  save(file);
  std::cout << "SAVING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

  showInfo(&prep_);
}

divGraph::divGraph(Preprocess& prep_, Parameter& param_, int T_, int efC_, double probC,double probQ) :zlsh(prep_, param_, ""), link_list_locks_(prep_.data.N)
{
  myData = prep_.data.val;
  T = T_;
  dim = prep_.data.dim;
  lowDim = K;
  if (L == 0) lowDim = 0;
  maxT = 2 * T;
  //maxT = T;
  efC = 5 * T / 2;
  efC = efC_;
  unitL = max(maxT, efC);
  visited_list_pool_ = new threadPoollib::VisitedListPool(1, N);

  normalizeHash();
  double _coeff = 1.0, _coeffq = 1.0;
  if (lowDim) {
    boost::math::chi_squared chi(lowDim);
    _coeff = sqrt(boost::math::quantile(chi, probC));
    if (probQ == 1.0) _coeffq = DBL_MAX;
    else _coeffq = sqrt(boost::math::quantile(chi, probQ));
  }

#ifdef USE_SQRDIST
  _coeff = _coeff * _coeff;
  coeff = W * W / _coeff;
  _coeffq = _coeffq * _coeffq;
  coeffq = W * W / _coeffq;
#else
  coeff = W / _coeff;
  coeffq = W / _coeffq;
#endif
  //printf("\n N= %d\n", N);
  //lsh::timer timer;
  //std::cout << "CONSTRUCTING GRAPH..." << std::endl;
  //timer.restart();
  oneByOneInsert();
  //std::cout << "CONSTRUCTING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;
  //indexingTime = timer.elapsed();

  //std::cout << "SAVING GRAPH..." << std::endl;
  //timer.restart();
  //std::cout << "SAVING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;
  //showInfo(&prep_);
}


divGraph::divGraph(Preprocess* prep, const std::string& path, double probQ):link_list_locks_(prep->data.N)
{
  myData = prep->data.val;
  file = path;

  std::ifstream in(file, std::ios::binary);
  if (!in.good()) {
    std::cout << BOLDGREEN << "WARNING:\n" << GREEN << "Could not find the divGraph index file. \n"
              << "Filename: " << file.c_str() << RESET;
    exit(-1);
  }

  lsh::timer timer;
  std::cout << "LOADING GRAPH..." << std::endl;
  /***********************************************************************************/
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
  std::cout << "Loading hash..." << std::endl;
  lsh::progress_display pd((size_t)N * L);
  for (int i = 0; i != L; ++i) {
    for (int j = 0; j < N; ++j) {
      in.read((char*)&(key), sizeof(zint));
      in.read((char*)&((pointId)), sizeof(int));
      hashTables[i].insert({ key,pointId });
      ++pd;
    }
  }

  /**********************************************************************/

  in.read((char*)&T, sizeof(int));
  in.read((char*)&step, sizeof(int));
  in.read((char*)&nnD, sizeof(int));
  in.read((char*)&edgeTotal, sizeof(size_t));
  in.read((char*)&lowDim, sizeof(int));
  maxT = 2 * T;

  double _coeffq = 1.0;
  if (lowDim) {
    boost::math::chi_squared chi(lowDim);
    if (probQ == 1.0) _coeffq = DBL_MAX;
    else _coeffq = sqrt(boost::math::quantile(chi, probQ));
  }
#ifdef USE_SQRDIST
  _coeffq = _coeffq * _coeffq;
	coeffq = W * W / _coeffq;
#else
  coeffq = W / _coeffq;
#endif

  int len = -1;
  in.read((char*)&len, sizeof(int));
  char* buf = new char[len];
  in.read((char*)buf, sizeof(char) * len);
  flagStates.assign(buf);
  delete[] buf;

  in.read((char*)&len, sizeof(int));
  assert(len == N);
  //linkLists.resize(N, nullptr);
  //How to quickly initialize?
  linkLists.resize(N, nullptr);
  std::cout << "Loading graph..." << std::endl;
  linkListBase.resize((size_t)N * (size_t)maxT);
  //std::swap(pd,lsh::progress_display(N));
  pd.restart(N);
  for (size_t i = 0; i < N; ++i) {
    linkLists[i] = new Node2(i, (Res*)(&(linkListBase[i * (size_t)maxT])));
    linkLists[i]->readFromFile(in);
  }

  in.close();

  std::cout << "LOADING TIME: " << timer.elapsed() << "s." << std::endl << std::endl;

  showInfo(prep);
}

int  divGraph::searchLSH(int pId, std::vector<zint>& keys, std::priority_queue<Res>& candTable, std::unordered_set<int>& checkedArrs_local, threadPoollib::vl_type tag)
{

  //read_lock lock_hr(hash_lock);
  //std::vector<read_lock> lock_hs;
  //for (int i = 0; i < L; ++i) {
  //  lock_hs.push_back(read_lock(hash_locks_[i]));
  //}

  Res res_pair;

  int lshUB = N / 200;
  lshUB = L * log(pId + 1);
  int step = 2;
  std::vector<int> numAccess(L);
  std::vector<std::multimap<zint, int>::iterator> lpos(L), rpos(L), qpos(L);

  std::priority_queue<posInfo> lEntries, rEntries;


  for (int j = 0; j < L; j++) {

    qpos[j] = hashTables[j].lower_bound(keys[j]);
    if (qpos[j] != hashTables[j].begin()) {
      lpos[j] = qpos[j];
      --lpos[j];
      lEntries.push(posInfo(j, getLevel(lpos[j]->first, qpos[j]->first)));

    }
    //
    rpos[j] = qpos[j];
    if (rpos[j] != hashTables[j].end()) {
      rEntries.push(posInfo(j, getLevel(rpos[j]->first, qpos[j]->first)));
    }

  }

  while (!(lEntries.empty() && rEntries.empty())) {
    posInfo t;

    bool f = true;//TRUE:left; FALSE:right
    if (lEntries.empty()) f = false;
    else if (rEntries.empty()) f = true;
    else if (rEntries.top().dist > lEntries.top().dist) f = false;
    if(f){

    } else {


    }
    if (f) {
      if(lEntries.empty()){
        continue;
      }
      t = lEntries.top();

      lEntries.pop();
      if(t.id>L){
        continue;
      }
      for (int i = 0; i < step; ++i) {
        ++numAccess[t.id];
        res_pair.id = lpos[t.id]->second;
        if (checkedArrs_local.find(res_pair.id)==checkedArrs_local.end()) {
        // TODO: Another bug here with dist vector or perhaps id issues

          res_pair.dist = cal_dist(myData[pId], myData[res_pair.id], dim);
          //printf("calculating dist between %d %d %f\n", pId, res_pair.id, res_pair.dist);
          candTable.push(res_pair);
          //checkedArrs_local[res_pair.id] = tag;
          checkedArrs_local.emplace(res_pair.id);
        }

        if (lpos[t.id] != hashTables[t.id].begin()) {
          --lpos[t.id];
        }
        else {
          break;
        }
      }

      if (lpos[t.id] != hashTables[t.id].begin()) {
        t.dist = getLevel(lpos[t.id]->first, qpos[t.id]->first);
        lEntries.push(t);
      }


    }
    else {
      if(rEntries.empty()){
        continue;

      }
      t = rEntries.top();

      rEntries.pop();

      if(t.id>L){
        continue;
      }
      //read_lock lock_h(hash_locks_[t.id]);
      for (int i = 0; i < step; ++i) {
        ++numAccess[t.id];
        res_pair.id = rpos[t.id]->second;
        if (checkedArrs_local.find(res_pair.id)==checkedArrs_local.end()) {

          res_pair.dist = cal_dist(myData[pId], myData[res_pair.id], dim);
          //printf("calculating dist between %d %d %f\n", pId, res_pair.id, res_pair.dist);
          candTable.push(res_pair);
          //checkedArrs_local[res_pair.id] = tag;
          checkedArrs_local.emplace(res_pair.id);
        }
        if (++rpos[t.id] == hashTables[t.id].end()) {
          break;
        }
      }

      if (rpos[t.id] != hashTables[t.id].end()) {
        t.dist = getLevel(rpos[t.id]->first, qpos[t.id]->first);
        rEntries.push(t);
      }

    }

    if (candTable.size() >= lshUB) break;
  }

  return 0;
}

void debug_message(int& debug){
  debug++;
  //printf("debug at %d\n",debug);
  return;
}
void divGraph::insertLSHRefine(int pId)
{
 // printf("\npid %d starts\n", linkLists[pId]->id);
  //printf("link list base size=%ld\n", linkListBase.size());

  for(int i=0; i<N; i++){
    //printf("id%d's first neighbor is %d\n", i, linkLists[i]->neighbors[0].id);

  }

  std::priority_queue<Res> candTable;
  std::vector<zint> keys(L);
  threadPoollib::VisitedList* vl = visited_list_pool_->getFreeVisitedList();
  auto checkedArrs_local = vl->mass;
  //checkedArrs_local.reserve(N);
  threadPoollib::vl_type tag = vl->curV;
  /// for L LSB trees, genereate a key that is z value (grid count combined) within jth LSH tree;
  ///  print the hash value in bits
  auto temp_ptr = (uint32_t*)&hashval[pId];
  uint32_t tempbits = *temp_ptr;
  for(int i=31; i>=0; --i){
    //printf("%u", (tempbits>>i)&1);
    //if(i%8==0) printf(" ");
  }
  //printf("\n");

  for (int j = 0; j < L; j++) {
    keys[j] = getZ(hashval[pId] + j * K);
  }
  int debug=0;
  searchLSH(pId, keys, candTable, checkedArrs_local, tag);

  //compCostConstruction += candTable.size();
  //printf("cand set:\n");
  if (pId != first_id && candTable.empty()) {
    //printf("%d ", first_id);
    candTable.emplace(first_id, cal_dist(myData[pId], myData[first_id], dim));
    //checkedArrs_local[first_id] = tag;
    checkedArrs_local.emplace(first_id);
  }
  //write_lock lock(link_list_locks_[pId]);
  std::priority_queue<Res, std::vector<Res>, std::greater<Res>> eps;
  //printf("linking: \n");
  //printf("%d ", linkLists[pId]->id);
  //printf(" node out=%d \n", linkLists[pId]->out);
  //printf("linkList size=%ld, pId=%d", linkLists.size(), pId);
  while (!candTable.empty()) {

    auto u = candTable.top();

    int qId = u.id;
    float dist = u.dist;
    //printf("%d %f ", qId, dist);

    //printf("%d ", linkLists[pId]->id);
    if (linkLists[pId]->size() > efC)linkLists[pId]->erase();
    linkLists[pId]->insert(u.dist, u.id);
    //printf("finished   ");
    if (linkLists[pId]->size() > efC)linkLists[pId]->erase();
    eps.emplace(u.dist, u.id);
    candTable.pop();
  }
  //printf("linking finished\n");

  //compCostConstruction += searchInBuilding(pId, eps, linkLists[pId]->neighbors, linkLists[pId]->out, checkedArrs_local, tag);
  chooseNN(linkLists[pId]->neighbors, linkLists[pId]->out);



  visited_list_pool_->releaseVisitedList(vl);
  int len = linkLists[pId]->size();
  //Res* arr = new Res[len];
  //memcpy(arr, linkLists[pId]->neighbors, len * sizeof(Res));
  //lock.unlock();
  for (int pos = 0; pos < len; ++pos) {
    auto& x = linkLists[pId]->neighbors[pos];
    int& qId = x.id;
    float& dist = x.dist;

   // write_lock lock_q(link_list_locks_[qId]);

    chooseNN(linkLists[qId]->neighbors, linkLists[qId]->out, Res(pId, dist));
  }
  ///1
  //debug_message(debug);
  //printf("keys size=%ld\n", keys.size());
  for (size_t j = 0; j < keys.size(); j++) {
    //write_lock lock_h(hash_locks_[j]);
    /// TODO: where the bug is
    //printf("key=%ld pid=%d\n", keys[j], pId);
    //debug_message(debug);
    hashTables[j].insert({ keys[j],pId });
    //debug_message(debug);
  }
  ///9
  //debug_message(debug);
}

int divGraph::searchInBuilding(int p, std::priority_queue<Res, std::vector<Res>, std::greater<Res>>& eps, Res* arr, int& size_res,
                               std::unordered_set<int>& checkedArrs_local, threadPoollib::vl_type tag)
{
  //size_res = 0;
  Res res_pair;
  int cost = 0;
  while (!eps.empty()) {
    auto u = eps.top();
    //read_lock lock_e(link_list_locks_[u.id]);
    if (u > arr[0]) break;
    eps.pop();
    for (int pos = 0; pos < linkLists[u.id]->size(); ++pos) {
      res_pair.id = (*(linkLists[u.id]))[pos];
      if (checkedArrs_local.find(res_pair.id)==checkedArrs_local.end()) {
        //checkedArrs_local[res_pair.id] = tag;
        checkedArrs_local.emplace(res_pair.id);
        if (0 || arr[0].dist> cal_dist(hashval[p], hashval[res_pair.id], lowDim) * coeff) {
          res_pair.dist = cal_dist(myData[p], myData[res_pair.id], dim);
          ++cost;
          if(arr[0]> res_pair||size_res<efC){
            arr[size_res++] = res_pair;
            std::push_heap(arr, arr + size_res);
            if (size_res >= efC) {
              std::pop_heap(arr, arr + size_res);
              size_res--;
            }
            eps.emplace(res_pair);
          }
        }
        else {
          ++pruningConstruction;
        }

      }
    }
  }

  return cost;
}

void divGraph::chooseNN_simple(Res* arr, int& size_res)
{
  while (size_res > T) {
    std::pop_heap(arr, arr + size_res);
    size_res--;
  }
}

void divGraph::chooseNN_div(Res* arr, int& size_res)
{
  if (size_res <= T) return;

  int old_res = size_res;

  int choose_num = 0;
  std::sort(arr, arr + size_res);
  //std::priority_queue<Res, std::vector<Res>, std::greater<Res>> res;
  for (int i = 0; i < size_res; ++i) {
    if (choose_num >= T) break;

    auto& curRes = arr[i];
    bool flag = true;
    for (int j = 0; j < choose_num; ++j) {
      ++compCostConstruction;
      float dist = cal_dist(myData[curRes.id], myData[arr[j].id], dim);
      if ( dist < curRes.dist) {
        flag = false;
        break;
      }
    }
    if (flag) {
      if (choose_num < i) {
        Res temp = arr[i];
        arr[i] = arr[choose_num];
        arr[choose_num] = temp;
      }
      choose_num++;
    }
  }

  size_res = choose_num;
  std::swap(arr[size_res - 1], arr[0]);

  bool f = false;
  for (int i = 0; i < size_res - 1; ++i) {
    if (arr[i] == arr[i + 1]) {
      f = true;
      break;
    }
  }
  if (f) {
    int pId = (arr - linkLists[0]->neighbors) / (linkLists[1]->neighbors - linkLists[0]->neighbors);
    printf("Error in %d:\n", pId);
    for (int j = 0; j < size_res; ++j) {
      printf("%2d: dist=%f, id=%d\n", j, arr[j].dist, arr[j].id);
    }
#ifdef _MSC_VER
    system("pause");
#endif
  }
}

void divGraph::chooseNN(Res* arr, int& size_res)
{
#ifdef DIV
  chooseNN_div(arr, size_res);
	//
#else
  chooseNN_simple(arr, size_res);
#endif
}

void divGraph::chooseNN_simple(Res* arr, int& size_res, Res new_res)
{
  if (myFind(arr, arr + size_res, new_res)) return;

  if (size_res < maxT) {
    arr[size_res++] = new_res;
    std::push_heap(arr, arr + size_res);
    //linkLists[qId]->insert(dist, pId);
    //linkLists[pId]->increaseIn();
  }
  else if (arr[0]>new_res) {
    //linkLists[linkLists[qId]->erase()]->decreaseIn();
    std::pop_heap(arr, arr + size_res);
    size_res--;
    arr[size_res++] = new_res;
    std::push_heap(arr, arr + size_res);
  }

  //while (size_res > T) {
  //	std::pop_heap(arr, arr + size_res);
  //	size_res--;
  //}
}

void divGraph::chooseNN_div(Res* arr, int& size_res, Res new_res)
{
  if (myFind(arr, arr + size_res, new_res)) return;

  if (size_res < maxT) {
    arr[size_res++] = new_res;
    std::sort(arr, arr + size_res);

    bool f = false;
    for (int i = 0; i < size_res - 1; ++i) {
      if (arr[i] == arr[i + 1]) {
        f = true;
        break;
      }
    }
    if (f) {
      int pId = (arr - linkLists[0]->neighbors) / (linkLists[1]->neighbors - linkLists[0]->neighbors);
      printf("Error in %d:\n", pId);
      for (int j = 0; j < size_res; ++j) {
        printf("%2d: dist=%f, id=%d\n", j, arr[j].dist, arr[j].id);
      }
#ifdef _MSC_VER
      system("pause");
#endif
    }
    std::swap(arr[size_res - 1], arr[0]);
    //arr[size_res] = arr[size_res - 1];
    //arr[size_res - 1] = arr[0];
    //arr[0] = arr[size_res];
  }
  else {
    arr[size_res++] = new_res;
    chooseNN_div(arr, size_res);

    /*if (arr[0] > new_res) {
        arr[size_res] = arr[size_res - 1];
        arr[size_res - 1] = arr[0];
        arr[0] = arr[size_res];

        auto idx = std::upper_bound(arr, arr + size_res, new_res) - arr;
        bool flag = true;
        for (int j = 0; j < idx; ++j) {
            ++compCostConstruction;
            if (cal_dist(myData[new_res.id], myData[arr[j].id], dim) < new_res.dist) {
                flag = false;
                break;
            }
        }
        if (flag) {
            memmove(arr + idx + 1, arr + idx, (size_res - idx + 1) * sizeof(Res));
            arr[idx] = new_res;
            size_res++;
            int choose_num = idx + 1;
            std::sort(arr, arr + size_res);
            std::priority_queue<Res, std::vector<Res>, std::greater<Res>> res;
            for (int i = idx + 1; i < size_res; ++i) {
                if (choose_num >= maxT) break;
                auto& curRes = arr[i];
                ++compCostConstruction;
                if (cal_dist(myData[curRes.id], myData[new_res.id], dim) < curRes.dist) {
                    flag = false;
                    break;
                }
                if (flag) {
                    if (choose_num < i) {
                        Res temp = arr[i];
                        arr[i] = arr[choose_num];
                        arr[choose_num] = temp;
                    }
                    choose_num++;
                }
                else flag = true;
            }

            size_res = choose_num;

            if (size_res < T) {
                size_res = T;
                std::sort(arr, arr + size_res);
            }
        }

        arr[size_res] = arr[size_res - 1];
        arr[size_res - 1] = arr[0];
        arr[0] = arr[size_res];
    }*/
  }

}

void divGraph::chooseNN(Res* arr, int& size_res, Res new_res)
{
#ifdef DIV
  chooseNN_div(arr, size_res, new_res);
#else
  chooseNN_simple(arr, size_res, new_res);
#endif

}

void divGraph::oneByOneInsert()
{
  linkLists.resize(N, nullptr);
  time_append +=1;
  linkListBase.resize((size_t)N * (size_t)unitL /*+ efC*time_append*/);
  //printf("linkListBase size=%ld with unitL %d\n", linkListBase.size(), unitL);
  for (int i = 0; i < N; ++i) {
    linkLists[i] = new Node2(i, (&(linkListBase.data()[i * unitL])));
    //printf("%d assigned to base %d ", i,  i * unitL/*+efC*(time_append-1)*/);
   // printf("with first id = %d\n", linkLists[i]->neighbors[linkLists[i]->out].id);
  }
  //printf("linkListBase size=%ld with unitL %d\n", linkListBase.size(), unitL);
  flagStates.resize(N, 'E');

  hashTables.resize(L);
  std::vector<mp_mutex>(L).swap(hash_locks_);

  int* idx = new int[N];
  for (int j = 0; j < N; ++j) {
    idx[j] = j;
  }

  //unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
  //std::shuffle(idx, idx + N, std::default_random_engine(seed));
  first_id = idx[0];
  insertLSHRefine(idx[0]);//Ensure there is at least one point in the graph before parallelizing
  //lsh::progress_display pd(N - 1);
//#pragma omp parallel for
  for (int i = 1; i < N; i++) {
    insertLSHRefine(idx[i]);
   // ++pd;
  }
  //std::cout << "count: " << pd.count() << std::endl;

//#pragma omp parallel for
//	for (int i = N - 1; i >= 0; i--) {
//		insertHNSW(i);
//		++pd;
//	}

  //refine();
}
#if defined(__GNUC__) && (__GNUC__ >= 4)
#define DIVG_memcpy(dst, src, size) __builtin_memcpy(dst, src, size)
#else
#define DIVG_memcpy(dst, src, size) memcpy(dst, src, size)
#endif
void divGraph::appendHash(float **newData,int64_t oldSize,int64_t newSize) {
  float **newHash=new float* [newSize];
  DIVG_memcpy(newHash,hashval,oldSize*sizeof(float*));
  for (int j = oldSize; j < newSize; j++) {
    newHash[j] = calHash(newData[j]);
  }
  delete hashval;
  hashval =newHash;

  for (int j = 0; j < S; j++){
    hashMins[j] = FLT_MAX;
    hashMaxs[j] = -FLT_MAX;
    for (int i = oldSize; i < newSize; i++){
      if (hashMins[j] > hashval[i][j]) hashMins[j] = hashval[i][j];

      if (hashMaxs[j] < hashval[i][j]) hashMaxs[j] = hashval[i][j];
    }
  }
 // std::cout<<"Hash extend done"<<std::endl;
}
void divGraph::appendTensor(torch::Tensor &t, Preprocess *prep){

  int64_t newSize=N+t.size(0);
  int64_t oldSize = N;

  int64_t vecDim=t.size(1);
  time_append +=1;
  int64_t  appendSize=t.size(0);
  //printf("before resizing\n");

  for(int i=0; i<N; i++){
    //printf("id%d's first neighbor is %d\n", i, linkLists[i]->neighbors[0].id);

  }
  linkLists.resize(newSize, nullptr);
  std::vector<Res> new_linkListBase = std::vector<Res>(newSize*unitL);
  //printf("new list first neighbor is %d\n", new_linkListBase[0].id);
  //link_list_locks_=std::vector<mp_mutex>(newSize);
  /// Corruption!
  //linkListBase.resize((size_t)(newSize) * (size_t)unitL /*+ efC*time_append*/);
  //printf("new list first neighbor is %d\n", new_linkListBase[0].id);
  //printf("link list first neighbor is %d\n",  linkLists[0]->neighbors[0].id);
  //printf("before newing\n");
  for (int i = oldSize; i < newSize; ++i) {
    linkLists[i] = new Node2(i, (&(new_linkListBase.data()[i * unitL/*+efC*(time_append-1)*/])));
  }
  //printf("after newing\n");
  //printf("link list first neighbor is %d\n",  linkLists[0]->neighbors[0].id);
  for(size_t i=0; i<linkListBase.size(); i++){
    new_linkListBase[i] = linkListBase[i];

  }
  for (int i = 0; i < oldSize; ++i) {
    linkLists[i] = new Node2(i, (&(new_linkListBase.data()[i * unitL/*+efC*(time_append-1)*/])));
  }

  //printf("after copying list\n");
  //printf("new list first neighbor is %d\n", new_linkListBase[0].id);
  //printf("old list first neighbor is %d\n", linkListBase[0].id);
  //printf("link list first neighbor is %d\n",  linkLists[0]->neighbors[0].id);
  linkListBase = new_linkListBase;

  // copy linkLists


  //printf("after resizing\n");
  //printf("new list first neighbor is %d\n", linkListBase[0].id);
  //printf("old list first neighbor is %d\n", linkListBase[0].id);
  //printf("link list first neighbor is %d\n",  linkLists[0]->neighbors[0].id);
  for(int i=0; i<newSize; i++){
    //printf("id%d's first neighbor is %d\n", i, linkLists[i]->neighbors[0].id);
  }

  flagStates.resize(newSize+1, 'E');
  //printf("before copying data\n");
  for(int i=0; i<newSize; i++){
    //printf("id%d's first neighbor is %d\n", i, linkLists[i]->neighbors[0].id);
  }
  /**
   * @brief adjust myData field
   */
 // std::cout<<"Memory extend begin"<<std::endl;
  float **newData=new float* [newSize];
  DIVG_memcpy(newData,myData,oldSize*sizeof(float*));

  //myData= (float **) realloc(myData,newSize*(sizeof (float *)));
  for (int i = 0; i < appendSize; i++) {
    //in.seekg(sizeof(float), std::ios::cur);
    newData[i+oldSize]=new float[vecDim];
    auto rowI=t.slice(0,i,i+1).contiguous();
    auto dataRowI= rowI.data_ptr<float>();
    DIVG_memcpy(newData[i+oldSize],dataRowI,vecDim*sizeof(float));
  }
  //printf("before appending hash\n");
  for(int i=0; i<newSize; i++){
    //printf("id%d's first neighbor is %d\n", i, linkLists[i]->neighbors[0].id);
  }
  appendHash(newData,oldSize,newSize);

 // std::cout<<"Memory extend done"<<std::endl;
  delete myData;
  myData=newData;
  prep->data.val=myData;


  /**
 * @brief adjust the N field
 */
   prep->data.oldN=N;
  N=newSize;
  prep->data.N=newSize;
  getHash(*prep);
   for(int i=0; i<N; i++){
   //printf("vec%d=", i);
     for(int j=0; j<prep->data.dim; j=j+32){
         //printf("%f ", myData[i][j]);
     }
     //printf("\n");
   }

  int* idx = new int[appendSize];
  for (int j = 0; j < appendSize; j++) {
    idx[j] = j+oldSize;
  }

 /* unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
  std::shuffle(idx, idx + appendSize, std::default_random_engine(seed));*/
  first_id = idx[0];
  //printf("before inserting the first\n");
  for(int i=0; i<newSize; i++){
    //printf("id%d's first neighbor is %d\n", i, linkLists[i]->neighbors[0].id);
  }
  insertLSHRefine(idx[0]);//Ensure there is at least one point in the graph before parallelizing
  //lsh::progress_display pd(appendSize - 1);
  //printf("after inserting the first\n");
  for(int i=0; i<newSize; i++){
    //printf("id%d's first neighbor is %d\n", i, linkLists[i]->neighbors[0].id);
  }
  for (int i = 1; i < appendSize; i++) {
    insertLSHRefine(idx[i]);
   // ++pd;
  }

}
void divGraph::refine()
{
  Res* rnns = new Res[N * maxT + 1];
  std::vector<int> rnnSize(N, 0);
  for (int i = 0; i < N; ++i) {
    const auto& nns = linkLists[i]->neighbors;
    for (int j = 0; j < linkLists[i]->size(); ++j) {
      auto& qId = nns[j].id;
      const auto& rnn = rnns + qId * maxT;
      if (rnnSize[qId] < maxT) {
        rnn[rnnSize[qId]++] = Res(nns[j].dist, i);
        std::push_heap(rnn, rnn + rnnSize[qId]);
      }
      else if (nns[j].dist < rnn[0].dist) {
        std::pop_heap(rnn, rnn + rnnSize[qId]);
        rnn[rnnSize[qId] - 1] = Res(nns[j].dist, i);
        std::push_heap(rnn, rnn + rnnSize[qId]);
      }

    }
  }
  for (int i = 0; i < N; ++i) {
    const auto& nns = linkLists[i]->neighbors;
    const auto& rnn = rnns + i * maxT;
    for (int j = 0; j < rnnSize[i]; ++j) {
      //if (rnn[j].dist > nns[0].dist) break;
      if (!myFind(nns, nns + linkLists[i]->size(), rnn[j])) {
        if (linkLists[i]->size() < maxT) {
          linkLists[i]->insert(rnn[j].dist, rnn[j].id);
        }
        else if (rnn[j].dist < nns[0].dist) {
          linkLists[i]->erase();
          linkLists[i]->insert(rnn[j].dist, rnn[j].id);
          //printf("Find one!\n");
        }
      }
    }
  }
}

void divGraph::buildExact(Preprocess* prep)
{
  getIndexes();
  flagStates.resize(N, 'E');
  ////How to quickly initialize?
  //linkLists.resize(N, NULL);
  //for (auto& pt : linkLists) {
  //	pt = new Node2();
  //}
  for (int i = 0; i < N; ++i) {
    int numEdges = T;
    linkLists[i]->setOut(numEdges);
    for (int l = 1; l <= numEdges; ++l) {
      int v = prep->benchmark.indice[i + 200][l];
      linkLists[i]->insertSafe(v, prep->benchmark.dist[i + 200][l], l - 1);
      linkLists[v]->increaseIn();
    }
  }
}

void divGraph::buildExactLikeHNSW(Preprocess* prep)
{
  getIndexes();
  flagStates.resize(N, 'E');
  std::vector<float> minTDists(N);
  ////How to quickly initialize?
  //linkLists.resize(N, NULL);
  //for (auto& pt : linkLists) {
  //	pt = new Node2();
  //}
  for (int i = 0; i < N; ++i) {
    int numEdges = T;
    linkLists[i]->setOut(numEdges);
    for (int l = 1; l <= numEdges; ++l) {
      int v = prep->benchmark.indice[i + 200][l];
      linkLists[i]->insertSafe(v, prep->benchmark.dist[i + 200][l], l - 1);
      linkLists[v]->increaseIn();
    }
    std::make_heap(&(linkListBase[0]) + i * maxT, &(linkListBase[0]) + i * maxT + T);
    minTDists[i] = linkLists[i]->getNeighbor(0).dist;
  }

  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < T; ++j) {
      auto& v = linkLists[i]->getNeighbor(j);
      if (v.dist > minTDists[v.id]) {// avoid inserting the appeared point
        if (linkLists[v.id]->findSmaller(v.dist)) {
          if (linkLists[v.id]->isFull(maxT)) linkLists[v.id]->erase();
          linkLists[v.id]->insert(v.dist, i);
        }

      }
    }
  }

}

inline uint64_t divGraph::getKey(int u, int v)
{
  if (u > v) {
    return (((uint64_t)u) << 32) | (uint64_t)v;
  }
  else {
    return getKey(v, u);
  }
}

extern int _lsh_UB;

void divGraph::knn(queryN* q)
{
  lsh::timer timer;
  timer.restart();
  q->hashval = calHash(q->queryPoint);

  std::string flag_(N, 'U');
  std::vector<float> visitedDists(N);
  entryHeap pqEntries;
  std::priority_queue<Res> candTable;
  Res res_pair;

  q->UB = (int)N / 10;
  int lshUB = N / 200;
  lshUB = 4 * L * log(N);
  int step = 1;
  if(_lsh_UB>0) lshUB=_lsh_UB;
  std::vector<int> numAccess(L);
  std::vector<std::multimap<zint, int>::iterator> lpos(L), rpos(L), qpos(L);
  std::priority_queue<posInfo> lEntries, rEntries;
  std::vector<zint> keys(L);
  for (int j = 0; j < L; j++) {
    keys[j] = getZ(q->hashval + j * K);
    qpos[j] = hashTables[j].lower_bound(keys[j]);
    if (qpos[j] != hashTables[j].begin()) {
      lpos[j] = qpos[j];
      --lpos[j];
#ifdef USE_LCCP
      lEntries.push(posInfo(j, getLLCP(lpos[j]->first, keys[j])));
#else
      lEntries.push(posInfo(j, getLevel(lpos[j]->first, qpos[j]->first)));
#endif // USE_LCCP

    }
    //
    rpos[j] = qpos[j];
    if (rpos[j] != hashTables[j].end()) {
#ifdef USE_LCCP
      rEntries.push(posInfo(j, getLLCP(rpos[j]->first, keys[j])));
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
        if (flag_[res_pair.id] == 'U') {
          res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
          visitedDists[res_pair.id] = res_pair.dist;
          candTable.push(res_pair);
          flag_[res_pair.id] = 'T';
        }
        if (lpos[t.id] != hashTables[t.id].begin()) {
          --lpos[t.id];
        }
        else {
          break;
        }
      }

      if (lpos[t.id] != hashTables[t.id].begin()) {
#ifdef USE_LCCP
        t.dist = getLLCP(lpos[t.id]->first, keys[t.id]);
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
        if (flag_[res_pair.id] == 'U')
        {
          res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
          visitedDists[res_pair.id] = res_pair.dist;
          candTable.push(res_pair);
          flag_[res_pair.id] = 'T';
        }
        if (++rpos[t.id] == hashTables[t.id].end()) {
          break;
        }
      }
      if (rpos[t.id] != hashTables[t.id].end()) {
#ifdef USE_LCCP
        t.dist = getLLCP(rpos[t.id]->first, keys[t.id]);
#else
        t.dist = getLevel(rpos[t.id]->first, qpos[t.id]->first);
#endif // USE_LCCP
        rEntries.push(t);
      }
    }
    if (candTable.size() >= lshUB) break;
  }



  q->cost = candTable.size();
  while (candTable.size() > ef) candTable.pop();

  q->timeHash = timer.elapsed();
  timer.restart();
  if (candTable.empty()) {
    candTable.emplace(0, cal_dist(q->queryPoint, myData[0], dim));
  }

  while (!candTable.empty()) {
    auto u = candTable.top();
    pqEntries.push(std::make_pair(u, 1));
    q->resHeap.push(u);
    candTable.pop();
  }
  q->minKdist = q->resHeap.top().dist;
  entryHeap tempPQ;
  tempPQ.emplace(pqEntries.top());
  pqEntries.swap(tempPQ);

  bestFirstSearchInGraph(q, flag_, pqEntries);
  q->timeSift = timer.elapsed();
  q->timeTotal = q->timeHash + q->timeSift;
  q->costs = numAccess;

  //delete[] q->hashval;
}

void divGraph::knnHNSW(queryN* q)
{
  lsh::timer timer;
  q->hashval = calHash(q->queryPoint);
#ifdef USE_SSE
  _mm_prefetch((char*)(q->queryPoint), _MM_HINT_T0);
#endif
  timer.restart();
  std::string flag_(N, 'U');
  std::vector<float> visitedDists(N);
  std::priority_queue<std::pair<Res, int>, std::vector<std::pair<Res, int>>, std::greater<std::pair<Res, int>>> pqEntries;
  //std::priority_queue<Res> candTable;
  Res res_pair;

  //ef = q->k;
  //ef += 200;
  std::priority_queue<Res, std::vector<Res>, std::greater<Res>> eps;
  int ep0 = 0;
  flag_[ep0] = 'G';
  float dist = cal_dist(q->queryPoint, myData[ep0], dim);
  //float lowerBound = dist;
  eps.emplace(dist, ep0);
  q->resHeap.emplace(dist, ep0);
  pqEntries.push(std::make_pair(Res(dist, ep0), 1));

  //bestFirstSearchInGraph2(q, flag_, visitedDists, pqEntries);
  //bestFirstSearchInGraphHNSW(q, flag_, visitedDists, pqEntries);
  bestFirstSearchInGraph(q, flag_, pqEntries);
  q->timeSift = timer.elapsed();
  q->timeTotal = q->timeHash + q->timeSift;
}

void divGraph::bestFirstSearchInGraph(queryN * q, std::string & stateFlags, entryHeap & pqEntries)
{
  int debug=0;

  while (!pqEntries.empty()) {
    int knnth=0;
    //printf("poping %dth candidate\n", knnth++);
    auto u = pqEntries.top().first;

    if (u.dist > q->minKdist) {
      break;
    }
    //printf("candidate id=%d dist=%f\n", u.id, u.dist);
    int hop = pqEntries.top().second;
    pqEntries.pop();
    q->maxHop = q->maxHop > hop ? q->maxHop : hop;
    Res* nns = linkLists[u.id]->neighbors;
#ifdef USE_SSE
    //_mm_prefetch((char*)&(stateFlags[u.id]), _MM_HINT_T0);
		//_mm_prefetch((char*)(&(stateFlags[u.id]) + 64), _MM_HINT_T0);
		//_mm_prefetch(links + (*(data + 1)) * size_data_per_element_ + offsetData_, _MM_HINT_T0);
		_mm_prefetch((char*)(myData[nns[0].id]), _MM_HINT_T0);
		_mm_prefetch((char*)(myData[nns[1].id]), _MM_HINT_T0);
#endif
    //for(int i=0; i<52; i++){
      //printf("id%d's first neighbor addr is %d\n", i, (linkListBase[i*unitL+0].id));

    //}
    //debug_message(debug);
    //printf("link list size=%ld\n", linkLists.size());
    //printf("first neigh
    //debug_message(debug);bors addr %p\n", linkLists[u.id]);
    //printf("first neighobr is %d\n",(*(linkLists[u.id]))[0]);
    //printf("reading neighbors\n");

    for (int pos = 0; pos != maxT; ++pos) {
      //debug_message(debug);
      //printf("%dth ", pos);
      //int v = (*(linkLists[u.id]))[pos];
      int v = linkListBase[u.id*unitL+pos].id;
      if (v < 0 || v> linkListBase.size()) continue;
      switch (stateFlags[v]) {
        case 'U':
          stateFlags[v] = 'G';
          if (0 || cal_dist(q->hashval, hashval[v], lowDim) * coeffq < q->minKdist) {
            float dist = cal_dist(q->queryPoint, myData[v], dim);
            ++q->cost;
            if (false || dist < q->minKdist
              //|| visitedDists[v] < u.dist
                ) {
              pqEntries.push(std::make_pair(Res(v, dist), hop + 1));
              q->resHeap.push(Res(v, dist));
              if (q->resHeap.size() > ef) {
                q->resHeap.pop();
                q->minKdist = q->resHeap.top().dist;
              }
            }
          }
          else {
            q->prunings++;
          }
          break;
      }
    }
  }
  //printf("reading neighbors over\n");
  //debug_message(debug);
  while (q->resHeap.size() > q->k) q->resHeap.pop();
  q->res.resize(q->k);
  for (int i = q->k - 1; i > -1; --i) {
    q->res[i] = q->resHeap.top();
    q->resHeap.pop();
  }
}

void divGraph::showInfo(Preprocess* prep)
{
  float dist_total = 0.0f;
  size_t sqrMat = 0;
  size_t cnt = 0, rec = 0, N1 = 0, cnt1 = 0;
  int f = 1;
  for (int u = 0; u < N; ++u) {
    cnt += linkLists[u]->size();
    sqrMat += linkLists[u]->size() * linkLists[u]->size();
    N1++;
    if (u >= prep->benchmark.N - 200) continue;

    cnt1 += linkLists[u]->size();;
    auto& pt = linkLists[u]->neighbors;
    f = f & isUnique(pt, pt + linkLists[u]->size());
    if (f == 0) {
      printf("***%d\n", u);
      const auto& nns = pt;
      for (int j = 0; j < maxT; ++j) {
        if (j == linkLists[u]->size()) printf("size=%d\n", j);
        printf("%2d: dist=%f, id=%d\n", j, nns[j].dist, nns[j].id);
      }
#ifdef _MSC_VER
      system("pause");
#endif
    }

    for (int pos = 0; pos != linkLists[u]->size(); ++pos) {
      float dist = linkLists[u]->getNeighbor(pos).dist;
#ifdef USE_SQRDIST
      dist_total += sqrt(dist);
#else
      res += dist;
#endif
    }
  }

  float ratio = 0.0f;
  for (int u = 0; u < prep->benchmark.N - 200; ++u) {
    std::set<unsigned> set1, set2;
    std::vector<unsigned> set_intersection;
    set_intersection.clear();
    set1.clear();
    set2.clear();

    int j = 1;
    for (int pos = 0; pos != linkLists[u]->size(); ++pos) {
      set1.insert((*(linkLists[u]))[pos]);
      set2.insert((unsigned)prep->benchmark.indice[u + 200][j]);
      ++j;
    }
    std::set_intersection(set1.begin(), set1.end(), set2.begin(), set2.end(),
                          std::back_inserter(set_intersection));

    rec += set_intersection.size();
  }

  //return res / cnt;
  float derivation = (float)sqrMat / N1 - ((float)cnt / N1) * ((float)cnt / N1);
  float sigma = sqrt(derivation);
  auto idx = file.rfind('/');
  std::string fname(file.begin(), file.begin() + idx + 1);
  fname += "indexInfo.txt";
  FILE* fp = nullptr;
  fopen_s(&fp, fname.c_str(), "a");


  printf("dist=%f, cnt=%f, unique=%d, std=%f, Recall=%f\ncc=%f, pruning=%f\n\n", dist_total / cnt1, (float)cnt / N1, (int)f, sigma, (float)rec / cnt1,
         (float)compCostConstruction / N, (float)pruningConstruction / compCostConstruction);
  if (fp) fprintf(fp, "%s\nT=%d,L=%d,K=%d\ndist=%f, cnt=%f, unique=%d, std=%f, Recall=%f\ncc=%f, pruning=%f, IndexingTime=%f s.\n\n", file.c_str(), T, L, K, dist_total / cnt1, (float)cnt / N1, (int)f, sigma, (float)rec / cnt1,
                  (float)compCostConstruction / N, (float)pruningConstruction / compCostConstruction, indexingTime);

  //if (compCostConstruction == 0) {
  //	printf("dist=%f, cnt=%f, unique=%d, Dcnt=%f, Recall=%f\n\n", dist_total / cnt1, (float)cnt / N1, (int)f, sigma, (float)rec / cnt1);
  //	if (fp) fprintf(fp, "dist=%f, cnt=%f, unique=%d, Dcnt=%f, Recall=%f\ncc=%f, pruning=%f, IndexingTime=%f s.\n\n", dist_total / cnt1, (float)cnt / N1, (int)f, sigma, (float)rec / cnt1,
  //		(float)compCostConstruction / N, (float)pruningConstruction / compCostConstruction, indexingTime);
  //}
  //else {
  //	printf("dist=%f, cnt=%f, unique=%d, Dcnt=%f, Recall=%f\ncc=%f, pruning=%f\n\n", dist_total / cnt1, (float)cnt / N1, (int)f, sigma, (float)rec / cnt1,
  //		(float)compCostConstruction / N, (float)pruningConstruction / compCostConstruction);
  //	if (fp) fprintf(fp, "dist=%f, cnt=%f, unique=%d, Dcnt=%f, Recall=%f\ncc=%f, pruning=%f, IndexingTime=%f s.\n\n", dist_total / cnt1, (float)cnt / N1, (int)f, sigma, (float)rec / cnt1,
  //		(float)compCostConstruction / N, (float)pruningConstruction / compCostConstruction, indexingTime);
  //}
}

static int connectivity(std::vector<std::vector<int>>& us)
{
  int N = us.size();
  std::vector<int> unions(N);
  int flag = 0;
  int ef = 0;
  int cnt = 0;
  int last_zero = 0;

  std::unordered_set<size_t> uniques;

  while (cnt < N) {
    flag++;
    for (int i = last_zero; i < N; ++i) {
      if (unions[i] == 0) {
        last_zero = i;
        break;
      }
    }
    ef = last_zero;
    last_zero++;
    unions[ef] = flag;
    cnt++;
    std::priority_queue<int> qs;
    qs.push(ef);
    while (qs.size()) {
      ef = qs.top();
      qs.pop();
      for (auto& v : us[ef]) {
        if (unions[v] == 0) {
          unions[v] = flag;
          qs.push(v);
          cnt++;
        }
        else if (unions[v] < flag) printf("alg Error!\n");

      }
    }
  }

  return flag;
}

void divGraph::traverse()
{
  std::vector<int> unions(N);
  int flag = 0;
  int ef = 0;
  int cnt = 0;
  int last_zero = 0;

  std::unordered_set<size_t> uniques;

  while (cnt < N) {
    flag++;
    for (int i = last_zero; i < N; ++i) {
      if (unions[i] == 0) {
        last_zero = i;
        break;
      }
    }
    ef = last_zero;
    last_zero++;
    unions[ef] = flag;
    cnt++;
    std::priority_queue<int> qs;
    qs.push(ef);
    while (qs.size()) {
      ef = qs.top();
      qs.pop();
      auto& nns = linkLists[ef]->neighbors;
      int size = linkLists[ef]->out;
      for (int i = 0; i < size; ++i) {
        if (unions[nns[i].id] == 0) {
          unions[nns[i].id] = flag;
          qs.push(nns[i].id);
          cnt++;
        }

        else if (unions[nns[i].id] < flag) {
          //flag--;
          uniques.insert(((size_t)N) * unions[nns[i].id] + flag);
        }
      }
    }
  }

  std::vector<std::vector<int>> us(flag + 1);
  us[0].push_back(1);
  us[1].push_back(0);
  for (auto& x : uniques) {
    size_t u = x % N;
    size_t v = x / N;
    us[u].push_back(v);
    us[v].push_back(u);
  }

  flag = connectivity(us);

  printf("The union number is:%d\n", flag);
}


void divGraph::save(const std::string & file)
{

  std::ofstream out(file, std::ios::binary);
  /*****************************LSH************************/
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
  for (int i = 0; i != S; ++i) {
    out.write((char*)hashPar.rndAs[i], sizeof(float) * dim);
  }

  for (int i = 0; i < L; ++i) {
    if (hashTables[i].size() != N)
      throw std::runtime_error("Size error in hashTables!\n");
    for (auto iter = hashTables[i].begin(); iter != hashTables[i].end(); ++iter) {
      out.write((char*)&(iter->first), sizeof(zint));
      out.write((char*)&((iter->second)), sizeof(int));
    }
  }

  /*****************************graph************************/

  out.write((char*)&T, sizeof(int));
  out.write((char*)&step, sizeof(int));
  out.write((char*)&nnD, sizeof(int));
  out.write((char*)&edgeTotal, sizeof(size_t));
  out.write((char*)&lowDim, sizeof(int));
  //out.write((char*)&dataSize, sizeof(int));
  //out.write((char*)&dim, sizeof(int));
  int len = flagStates.size();
  out.write((char*)&len, sizeof(int));
  out.write((char*)(flagStates.c_str()), sizeof(char) * len);

  len = linkLists.size();
  out.write((char*)&len, sizeof(int));
  for (int i = 0; i < len; ++i) {
    linkLists[i]->writeToFile(out);
  }
  out.close();
}
