#pragma once
#include <atomic>
//#include "fastL2_ip.h"
extern int _G_COST;
template<typename MTYPE>
using DISTFUNC = MTYPE(*)(const void*, const void*, const void*);
