#include <LSHAPGIndex/Query.h>
#include <LSHAPGIndex/basis.h>
#include <iostream>
#include <set>
#include <queue>
#include <algorithm>
#include <vector>

void Performance::update(queryN* query, Preprocess& prep)
{
	num++;
	cost += query->cost;
	timeHash += query->timeHash;
	timeSift += query->timeSift;
	timeVerify += query->timeVerify;
	timeTotal += query->timeTotal;
	prunings += query->prunings;
	maxHop += query->maxHop;
	if (costs.size() == 0) {
		costs.resize(query->costs.size(),0);
	}
	for (int i = 0; i < query->costs.size(); ++i) {
		costs[i] += query->costs[i];
	}

	unsigned num0 = query->res.size();
	if (num0 > query->k)
		num0 = query->k;
	resNum += num0;

	std::set<unsigned> set1, set2;
	std::vector<unsigned> set_intersection;
	set_intersection.clear();
	set1.clear();
	set2.clear();

	for (unsigned j = 0; j < num0; j++)
	{
		//if(query->res[0])
#ifdef USE_SQRDIST
		float dist = sqrt(query->res[j].dist);
#else
		float dist = query->res[j].dist;
#endif
		float rate = dist / prep.benchmark.dist[query->flag][j];
		if (prep.benchmark.dist[query->flag][j] == 0) {
			rate = 1.0f;
		}
		//if (rate <0.99)
		//{
		//	std::cerr << "An abnormol ratio appears in:" << query->flag << ',' << j  <<
		//		std::endl;
		//	system("pause");

		//}
		ratio += rate;

		set1.insert(query->res[j].id);
		set2.insert((unsigned)prep.benchmark.indice[query->flag][j]);
	}

	if (set1.size() != query->res.size())  throw std::runtime_error("Appear duplicate result");
	std::set_intersection(set1.begin(), set1.end(), set2.begin(), set2.end(),
		std::back_inserter(set_intersection));

	NN_num += set_intersection.size();
}

Performance::~Performance()
{

}
