#include <LSHAPGIndex/basis.h>
#include <cmath>
#include <vector>
#include <random>
#include <set>
#include <assert.h>

void setW(std::string& datatsetName, float& R_min)
{
	if (datatsetName == "audio") {
		R_min = 0.3f;
	}
	else if (datatsetName == "mnist") {
		R_min = 3000.0f;
	}
	else if (datatsetName == "cifar") {
		R_min = 300.0f;
	}
	else if (datatsetName == "deep1m") {
		R_min = 0.2f;
	}
	else if (datatsetName == "NUS") {
		R_min = 6.50f;
	}
	else if (datatsetName == "Trevi") {
		R_min = 700.0f;
	}
	else if (datatsetName == "gist") {
		R_min = 0.3f;
	}
}

#if defined(unix) || defined(__unix__)
void showMemoryInfo(){}
#else
	#include <iostream>
	#include <windows.h>
	#include <psapi.h>
	#pragma comment(lib,"psapi.lib")
	//using namespace std;
	void showMemoryInfo()
	{
		HANDLE handle = GetCurrentProcess();
		PROCESS_MEMORY_COUNTERS pmc;
		GetProcessMemoryInfo(handle, &pmc, sizeof(pmc));
		std::cout << "Memory Usage: " << pmc.WorkingSetSize / (1024 * 1024) << "M/" <<
			pmc.PeakWorkingSetSize / (1024 * 1024) << "M + " <<
			pmc.PagefileUsage / (1024 * 1024) << "M/" <<
			pmc.PeakPagefileUsage / (1024 * 1024) << "M." << std::endl;
	}
#endif

//inline
//bool Is_Intersect(float*& mbr, float*& data, int& dim)
//{
//	return true;
//	bool flag_intersect;
//	for (int i = 0; i < dim; ++i) {
//		if ((mbr[2 * i] > data[i]) ||
//			(mbr[2 * i + 1] < data[i])) {
//			return false;
//		}
//	}
//	return true;
//}
