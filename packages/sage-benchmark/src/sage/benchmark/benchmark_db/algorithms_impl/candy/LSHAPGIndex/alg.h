#ifndef CANDY_LSHAPGINDEX_ALG_H
#define CANDY_LSHAPGINDEX_ALG_H
#pragma once
#include <iostream>
#include <fstream>
#include <LSHAPGIndex/Preprocess.h>
#include <LSHAPGIndex/divGraph.h>
#include <LSHAPGIndex/fastGraph.h>
#include <LSHAPGIndex/Query.h>
#include <time.h>
#include <LSHAPGIndex/basis.h>
#include <sstream>

#if defined(unix) || defined(__unix__)
struct llt
{
	int date, h, m, s;
	llt(size_t diff) { set(diff); }
	void set(size_t diff)
	{
		date = diff / 86400;
		diff = diff % 86400;
		h = diff / 3600;
		diff = diff % 3600;
		m = diff / 60;
		s = diff % 60;
	}
};
#endif
/*
bool find_file(std::string&& file)
{
	std::ifstream in(file);
	return in.good();
}*/
#endif
