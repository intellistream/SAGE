#pragma once
#include <CANDY/LSHAPGIndex/def.h>
#include <CANDY/LSHAPGIndex/Preprocess.h>
#include <vector>
#include <queue>
#include <CANDY/LSHAPGIndex/basis.h>
#include <CANDY/LSHAPGIndex/e2lsh.h>


class Performance
{
public:
	//cost
	unsigned cost = 0;
	//the average rounds of (r,c)-BC query for any point
	unsigned prunings = 0;
	//
	std::vector<unsigned> costs;
	// times of query
	unsigned num = 0;
	//
	float timeTotal = 0;
	//
	int maxHop = 0;
	//
	float timeHash = 0;
	//
	float timeSift = 0;
	//
	float timeVerify = 0;
	//number of exact NN
	unsigned NN_num = 0;
	//number of results
	unsigned resNum = 0;
	//
	float ratio = 0;
public:
	Performance() {}
	//update the query results
	void update(queryN* query, Preprocess& prep);
	~Performance();
};
