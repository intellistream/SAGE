 #pragma once
 #include <CANDY/LSHAPGIndex/divGraph.h>

 using dist_t = float;
 using labeltype = int;
 using tableint = int;

extern int _lsh_UB;

 using namespace threadPoollib;

 struct CompareByFirst {
 	constexpr bool operator()(std::pair<dist_t, tableint> const& a,
 		std::pair<dist_t, tableint> const& b) const noexcept {
 		return a.first < b.first;
 	}
 };

 struct hashPair
 {
     zint val;
     int id;
     hashPair() = default;
     hashPair(zint v_, int id_) :val(v_), id(id_) {}
     bool operator < (const hashPair& rhs) const {
         return val < rhs.val;
     }
 };

struct fastGraph
 {
 	std::string file;
 	char* links = nullptr;
 	size_t N = 0;
 	size_t dim = 0;
 	size_t maxT = 0;
 	size_t size_data_per_element_;
 	float** dataset = nullptr;
    float** hashval = nullptr;
    hashPair** hashTables = nullptr;
    divGraph* myhash = nullptr;//for computing q's hash values
 	//size_t max_elements_;
 	const size_t sint = sizeof(int);
 	threadPoollib::VisitedListPool* visited_list_pool_ = nullptr;
 public:
 	int ef = 0;
 	int T = 0;
 	int K = 0;
 	int L = 0;
    int S = 0;
    int lowDim = 0;
    int u = 0;
 	std::string getFilename() const { return file; }

 	fastGraph(divGraph* divG)
 	{
 		file = divG->getFilename();
 		ef = divG->ef;
 		N = divG->N;
 		maxT = divG->maxT;
 		size_data_per_element_ = (size_t)(maxT + 1) * sint;
 		dataset = divG->myData;
 		dim = divG->dim;
 		visited_list_pool_ = new VisitedListPool(1, N);
 		loadLite(divG);
 	}

 	void loadLite(divGraph* divG){
 		links = (char*)malloc(N * size_data_per_element_);
 		for (size_t i = 0; i < N; ++i) {
 			char* begin = links + i * size_data_per_element_;
 			auto& nns = divG->linkLists[i];
 			memcpy(begin, &(nns->out), sint);
 			begin += sint;
 			for (int i = 0; i < nns->out; ++i) {
 				memcpy(begin + i * sint, &(nns->neighbors[i].id), sint);
 			}
 		}
        K = divG->K;
        L = divG->L;
        S = divG->S;
        lowDim = divG->lowDim;
        myhash = divG;
        hashval = divG->hashval;
        u = myhash->u;
        hashTables = new hashPair * [L];
        for (int i = 0; i < L; ++i) {
            hashTables[i] = new hashPair[N];
            int cnt = 0;
            auto pt = divG->hashTables[i].begin();
            while (pt != divG->hashTables[i].end()) {
                hashTables[i][cnt++] = hashPair(pt->first, pt->second);
                pt++;
            }
        }
 	}

 	void knnHNSW1(queryN* q){
 		lsh::timer timer;
 		timer.restart();



 		std::priority_queue<std::pair<dist_t, labeltype >> result;
 #ifdef USE_SSE
 		_mm_prefetch((char*)(q->queryPoint), _MM_HINT_T0);
 #endif

 		int currObj = 0;
 		int ep_id = 0;
 		dist_t curdist = cal_dist(q->queryPoint, dataset[ep_id], dim);
 		q->cost++;
 		VisitedList* vl = visited_list_pool_->getFreeVisitedList();
 		auto visited_array = vl->mass;
 		vl_type visited_array_tag = vl->curV;

 		std::priority_queue<std::pair<dist_t, tableint>> top_candidates;
 		std::priority_queue<std::pair<dist_t, tableint>> candidate_set;
 		//std::priority_queue<std::pair<dist_t, tableint>, std::vector<std::pair<dist_t, tableint>>, CompareByFirst> top_candidates;
 		//std::priority_queue<std::pair<dist_t, tableint>, std::vector<std::pair<dist_t, tableint>>, CompareByFirst> candidate_set;

 		dist_t lowerBound;
 		dist_t dist = curdist;
 		lowerBound = dist;
 		top_candidates.emplace(dist, ep_id);
 		candidate_set.emplace(-dist, ep_id);

 		//visited_array[ep_id] = visited_array_tag;
        visited_array.emplace(ep_id);

 		while (!candidate_set.empty()) {

 			std::pair<dist_t, tableint> current_node_pair = candidate_set.top();

 			if ((-current_node_pair.first) > lowerBound) {
 				break;
 			}
 			candidate_set.pop();

 			tableint current_node_id = current_node_pair.second;
 			int* data = (int*)(links + current_node_id * size_data_per_element_);
 			size_t size = *data;
 			//bool cur_node_deleted = isMarkedDeleted(current_node_id);

 #ifdef USE_SSE
 			//_mm_prefetch((char*)(visited_array + *(data + 1)), _MM_HINT_T0);
 			//_mm_prefetch((char*)(visited_array + *(data + 1) + 64), _MM_HINT_T0);
 			//_mm_prefetch(links + (*(data + 1)) * size_data_per_element_ + offsetData_, _MM_HINT_T0);
 			_mm_prefetch((char*)(dataset[data[1]]), _MM_HINT_T0);
 			_mm_prefetch((char*)(data + 1), _MM_HINT_T0);
 #endif

 			for (size_t j = 1; j <= size; j++) {
 				int candidate_id = *(data + j);
 				//                    if (candidate_id == 0) continue;
 #ifdef USE_SSE
 				//_mm_prefetch((char*)(visited_array + *(data + j + 1)), _MM_HINT_T0);
 				//_mm_prefetch((char*)(dataset[*(data + j + 1)]), _MM_HINT_T0);
 #endif
 				if ((visited_array.find(candidate_id) == visited_array.end())) {

 					//visited_array[candidate_id] = visited_array_tag;
                    visited_array.emplace(candidate_id);

 					float* currObj1 = dataset[*(data + j)];
 					dist_t dist = cal_dist(q->queryPoint, currObj1, dim);
 					q->cost++;
 					if (top_candidates.size() < ef || lowerBound > dist) {
 						candidate_set.emplace(-dist, candidate_id);
 #ifdef USE_SSE
 						_mm_prefetch((char*)(dataset[candidate_set.top().second]),_MM_HINT_T0);
 #endif

 						top_candidates.emplace(dist, candidate_id);
 						if (top_candidates.size() > ef)
 							top_candidates.pop();

 						if (!top_candidates.empty())
 							lowerBound = top_candidates.top().first;
 					}
 				}
 			}
 		}

 		visited_list_pool_->releaseVisitedList(vl);

 		while (top_candidates.size() > q->k) {
 			top_candidates.pop();
 		}
 		q->res.resize(q->k);
 		for (int i = q->k - 1; i > -1; --i) {
 			std::pair<dist_t, tableint> rez = top_candidates.top();
 			q->res[i] = Res(rez.first, rez.second);
 			top_candidates.pop();
 		}

 		q->timeTotal = timer.elapsed();

 	}

    zint getZ(float* _h)
    {
        zint res = 0;
        for (int i = u - 1; i >= 0; i--) {
            int mask = 1 << i;
            for (int j = 0; j < K; j++) {
                res <<= 1;
                if ((int)floor(_h[j]) & mask)
                    ++res;
            }
        }
        return res;
    }

#if defined _MSC_VER
#include <intrin.h>
#endif
#include "divGraph.h"

    int getLLCP(zint k1, zint k2)
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

    void searchLSHQuery(queryN * q, std::priority_queue<Res>& candTable, std::vector<bool>& flag_)
    {
        q->hashval = myhash->calHash(q->queryPoint);
        //std::vector<bool> flag_(N, false);
        //std::vector<float> visitedDists(N);

        //std::priority_queue<Res> candTable;
        //Res res_pair;

        q->UB = (int)N / 10;
        int lshUB = N / 200;
        lshUB = 4 * L * log(N) + ef;
        int step = 1;
        if(_lsh_UB>0) lshUB=_lsh_UB;
        //std::vector<int> numAccess(L);
        std::vector<hashPair*> lpos(L), rpos(L), qpos(L);
        std::priority_queue<posInfo> lEntries, rEntries;
        std::vector<zint> keys(L);
        for (int j = 0; j < L; j++) {
            keys[j] = getZ(q->hashval + j * K);
            qpos[j] = std::lower_bound(hashTables[j], hashTables[j] + N, hashPair(keys[j], -1));
            //qpos[j] = hashTables[j].lower_bound(keys[j]);
            if (qpos[j] != hashTables[j]) {
                lpos[j] = qpos[j];
                --lpos[j];
#ifdef USE_LCCP
                lEntries.emplace(j, getLLCP(lpos[j]->val, keys[j]));
#else
                lEntries.push(posInfo(j, getLevel(lpos[j]->first, qpos[j]->first)));
#endif // USE_LCCP

            }
            //
            rpos[j] = qpos[j];
            if (rpos[j] != hashTables[j]+N) {
#ifdef USE_LCCP
                rEntries.emplace(j, getLLCP(rpos[j]->val, keys[j]));
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
                    //++numAccess[t.id];
                    //res_pair.id = lpos[t.id]->second;
                    int rid = lpos[t.id]->id;
                    if (!flag_[rid]) {
                        //res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
                        //visitedDists[res_pair.id] = res_pair.dist;
                        candTable.emplace(rid, cal_dist(q->queryPoint, q->myData[rid], dim));
                        flag_[rid] = true;
                    }
                    if (lpos[t.id] != hashTables[t.id]) {
                        --lpos[t.id];
                    }
                    else {
                        break;
                    }
                }

                if (lpos[t.id] != hashTables[t.id]) {
#ifdef USE_LCCP
                    t.dist = getLLCP(lpos[t.id]->val, keys[t.id]);
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
                    //++numAccess[t.id];

                    int rid = rpos[t.id]->id;
                    if (!flag_[rid]) {
                        //res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
                        //visitedDists[res_pair.id] = res_pair.dist;
                        candTable.emplace(rid, cal_dist(q->queryPoint, q->myData[rid], dim));
                        flag_[rid] = true;
                    }
                    if (++rpos[t.id] == hashTables[t.id] + N) {
                        break;
                    }

                    //res_pair.id = rpos[t.id]->second;
                    //if (flag_[res_pair.id] == 'U')
                    //{
                    //    res_pair.dist = cal_dist(q->queryPoint, q->myData[res_pair.id], dim);
                    //    visitedDists[res_pair.id] = res_pair.dist;
                    //    candTable.push(res_pair);
                    //    flag_[res_pair.id] = 'T';
                    //}
                    //if (++rpos[t.id] == hashTables[t.id].end()) {
                    //    break;
                    //}
                }
                if (rpos[t.id] != hashTables[t.id]+N) {
#ifdef USE_LCCP
                    t.dist = getLLCP(rpos[t.id]->val, keys[t.id]);
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

        if (candTable.empty()) {
            candTable.emplace(0, cal_dist(q->queryPoint, dataset[0], dim));
        }
    }

 	void knn(queryN* q) {
        lsh::timer timer;

        //entryHeap pqEntries;
        std::priority_queue<Res> candTable;
        std::vector<bool> flag_(N, false);

        timer.restart();
        searchLSHQuery(q, candTable,flag_);
        q->timeHash = timer.elapsed();

        //std::priority_queue<std::pair<dist_t, labeltype >> result;
#ifdef USE_SSE
        _mm_prefetch((char*)(q->queryPoint), _MM_HINT_T0);
#endif

        //int currObj = 0;
        //int ep_id = 0;
        //dist_t curdist = cal_dist(q->queryPoint, dataset[ep_id], dim);
        //q->cost++;
        //VisitedList* vl = visited_list_pool_->getFreeVisitedList();
        //auto visited_array = vl->mass;
        //vl_type visited_array_tag = vl->curV;

        std::priority_queue<std::pair<dist_t, tableint>> top_candidates;
        std::priority_queue<std::pair<dist_t, tableint>> candidate_set;
        //std::priority_queue<std::pair<dist_t, tableint>, std::vector<std::pair<dist_t, tableint>>, CompareByFirst> top_candidates;
        //std::priority_queue<std::pair<dist_t, tableint>, std::vector<std::pair<dist_t, tableint>>, CompareByFirst> candidate_set;

        while (!candTable.empty()) {
            auto u = candTable.top();
            top_candidates.emplace(u.dist, u.id);
            candidate_set.emplace(-u.dist, u.id);
            //pqEntries.push(u);
            //q->resHeap.push(u);
            candTable.pop();
        }

        dist_t lowerBound = top_candidates.top().first;
        //top_candidates.emplace(dist, ep_id);
        //candidate_set.emplace(-dist, ep_id);

        ////visited_array[ep_id] = visited_array_tag;
        //visited_array.emplace(ep_id);

        while (!candidate_set.empty()) {

            std::pair<dist_t, tableint> current_node_pair = candidate_set.top();

            if ((-current_node_pair.first) > lowerBound) {
                break;
            }
            candidate_set.pop();

            tableint current_node_id = current_node_pair.second;
            int* data = (int*)(links + current_node_id * size_data_per_element_);
            size_t size = *data;
            //bool cur_node_deleted = isMarkedDeleted(current_node_id);

#ifdef USE_SSE
           //_mm_prefetch((char*)(visited_array + *(data + 1)), _MM_HINT_T0);
           //_mm_prefetch((char*)(visited_array + *(data + 1) + 64), _MM_HINT_T0);
           //_mm_prefetch(links + (*(data + 1)) * size_data_per_element_ + offsetData_, _MM_HINT_T0);
            _mm_prefetch((char*)(dataset[data[1]]), _MM_HINT_T0);
            _mm_prefetch((char*)(data + 1), _MM_HINT_T0);
#endif

            for (size_t j = 1; j <= size; j++) {
                int candidate_id = *(data + j);
                //                    if (candidate_id == 0) continue;
#ifdef USE_SSE
               //_mm_prefetch((char*)(visited_array + *(data + j + 1)), _MM_HINT_T0);
               //_mm_prefetch((char*)(dataset[*(data + j + 1)]), _MM_HINT_T0);
#endif
                if (!flag_[candidate_id]) {

                    //visited_array[candidate_id] = visited_array_tag;
                    flag_[candidate_id] = true;

                    if (0 || cal_dist(q->hashval, hashval[candidate_id], lowDim) * myhash->coeffq < lowerBound) {
                        float* currObj1 = dataset[*(data + j)];
                        dist_t dist = cal_dist(q->queryPoint, currObj1, dim);
                        q->cost++;
                        if (top_candidates.size() < ef || lowerBound > dist) {
                            candidate_set.emplace(-dist, candidate_id);
#ifdef USE_SSE
                            _mm_prefetch((char*)(dataset[candidate_set.top().second]), _MM_HINT_T0);
#endif

                            top_candidates.emplace(dist, candidate_id);
                            if (top_candidates.size() > ef)
                                top_candidates.pop();

                            if (!top_candidates.empty())
                                lowerBound = top_candidates.top().first;
                        }
                    }
                    else {
                        q->prunings++;
                    }


                }
            }
        }

        //visited_list_pool_->releaseVisitedList(vl);

        while (top_candidates.size() > q->k) {
            top_candidates.pop();
        }
        q->res.resize(q->k);
        for (int i = q->k - 1; i > -1; --i) {
            std::pair<dist_t, tableint> rez = top_candidates.top();
            q->res[i] = Res(rez.first, rez.second);
            top_candidates.pop();
        }

        q->timeTotal = timer.elapsed();
    }

    void knnHNSW(queryN* q) {
        lsh::timer timer;

        //entryHeap pqEntries;
        std::priority_queue<Res> candTable;
        std::vector<bool> flag_(N, false);
        std::priority_queue<Res, std::vector<Res>, std::greater<Res>> candidate_set;
        Res top_candidates[500];

        timer.restart();
        searchLSHQuery(q, candTable, flag_);
        q->timeHash = timer.elapsed();

        //std::priority_queue<std::pair<dist_t, labeltype >> result;
#ifdef USE_SSE
        _mm_prefetch((char*)(q->queryPoint), _MM_HINT_T0);
#endif

        //int currObj = 0;
        //int ep_id = 0;
        //dist_t curdist = cal_dist(q->queryPoint, dataset[ep_id], dim);
        //q->cost++;
        //VisitedList* vl = visited_list_pool_->getFreeVisitedList();
        //auto visited_array = vl->mass;
        //vl_type visited_array_tag = vl->curV;

        //std::priority_queue<std::pair<dist_t, tableint>> top_candidates;
        //std::priority_queue<std::pair<dist_t, tableint>> candidate_set;

        //std::priority_queue<Res>

        //std::priority_queue<std::pair<dist_t, tableint>, std::vector<std::pair<dist_t, tableint>>, CompareByFirst> top_candidates;
        //std::priority_queue<std::pair<dist_t, tableint>, std::vector<std::pair<dist_t, tableint>>, CompareByFirst> candidate_set;


        size_t size_c = 0;

        while (!candTable.empty()) {
            auto u = candTable.top();
            //top_candidates.emplace(u.dist, u.id);
            top_candidates[size_c++] = u;
            candidate_set.emplace(u.dist, u.id);
            //pqEntries.push(u);
            //q->resHeap.push(u);
            candTable.pop();
        }
        std::make_heap(top_candidates, top_candidates + size_c);
        dist_t lowerBound = top_candidates[0].dist;
        //top_candidates.emplace(dist, ep_id);
        //candidate_set.emplace(-dist, ep_id);

        ////visited_array[ep_id] = visited_array_tag;
        //visited_array.emplace(ep_id);

        while (!candidate_set.empty()) {

            auto current_node_pair = candidate_set.top();

            if ((current_node_pair.dist) > lowerBound) {
                break;
            }
            candidate_set.pop();

            tableint current_node_id = current_node_pair.id;
            int* data = (int*)(links + current_node_id * size_data_per_element_);
            size_t size = *data;
            //bool cur_node_deleted = isMarkedDeleted(current_node_id);

#ifdef USE_SSE
           //_mm_prefetch((char*)(visited_array + *(data + 1)), _MM_HINT_T0);
           //_mm_prefetch((char*)(visited_array + *(data + 1) + 64), _MM_HINT_T0);
           //_mm_prefetch(links + (*(data + 1)) * size_data_per_element_ + offsetData_, _MM_HINT_T0);
            _mm_prefetch((char*)(dataset[data[1]]), _MM_HINT_T0);
            _mm_prefetch((char*)(data + 1), _MM_HINT_T0);
#endif

            for (size_t j = 1; j <= size; j++) {
                int candidate_id = *(data + j);
                //                    if (candidate_id == 0) continue;
#ifdef USE_SSE
               //_mm_prefetch((char*)(visited_array + *(data + j + 1)), _MM_HINT_T0);
               //_mm_prefetch((char*)(dataset[*(data + j + 1)]), _MM_HINT_T0);
#endif
                if (!flag_[candidate_id]) {

                    //visited_array[candidate_id] = visited_array_tag;
                    flag_[candidate_id] = true;

                    if (0 || cal_dist(q->hashval, hashval[candidate_id], lowDim) * myhash->coeffq < lowerBound) {
                        float* currObj1 = dataset[*(data + j)];
                        dist_t dist = cal_dist(q->queryPoint, currObj1, dim);
                        q->cost++;
                        if (size_c < ef || lowerBound > dist) {
                            candidate_set.emplace(dist, candidate_id);
#ifdef USE_SSE
                            _mm_prefetch((char*)(dataset[candidate_set.top().id]), _MM_HINT_T0);
#endif
                            if (size_c == ef && dist < top_candidates[0].dist) {
                                std::pop_heap(top_candidates, top_candidates + size_c);
                                size_c--;
                                top_candidates[size_c++] = Res(dist, candidate_id);
                                std::push_heap(top_candidates, top_candidates + size_c);
                            }

                            if (size_c) {
                                lowerBound = top_candidates[0].dist;
                            }

                            //top_candidates.emplace(dist, candidate_id);
                            //if (top_candidates.size() > ef)
                            //    top_candidates.pop();

                            //if (!top_candidates.empty())
                            //    lowerBound = top_candidates.top().first;
                        }
                    }
                    else {
                        q->prunings++;
                    }


                }
            }
        }

        //visited_list_pool_->releaseVisitedList(vl);

        while (size_c > q->k) {
            std::pop_heap(top_candidates, top_candidates + size_c);
            size_c--;
        }

        //while (top_candidates.size() > q->k) {
        //    top_candidates.pop();
        //}


        q->res.resize(q->k);
        for (int i = q->k - 1; i > -1; --i) {
            //auto rez = top_candidates[0];
            //q->res[i] = rez;
            q->res[i]= top_candidates[0];

            std::pop_heap(top_candidates, top_candidates + size_c);
            size_c--;
            //top_candidates.pop();
        }

        q->timeTotal = timer.elapsed();
    }
 };
