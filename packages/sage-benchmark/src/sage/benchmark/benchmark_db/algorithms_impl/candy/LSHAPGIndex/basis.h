/**
 * @file basis.h
 *
 * @brief A set of basic tools.
 */
#ifndef CANDY_LSHAPGINDEX_basis_H
#define CANDY_LSHAPGINDEX_basis_H
#pragma once
#include <string>
#include <iostream>
#include <vector>
#include <ctime>
#include <chrono>
#include <unordered_set>
#include <set>
#include <map>
#include <algorithm>
#include <LSHAPGIndex/space_l2.h>
#include <LSHAPGIndex/fastL2_ip.h>
//#include "distances_simd_avx512.h"
#include <mutex>

#if defined(__GNUC__)
#include <atomic>
#include <cstring>
#include <cfloat>
#include <math.h>
inline int fopen_s(FILE** pFile, const char* path, const char* mode)
{
	if ((*pFile = fopen64(path, mode)) == NULL) return 0;
	else return 1;
}

#elif defined _MSC_VER
#else
#endif

//#define __USE__AVX2__ZX__ 1

namespace lsh
{
	class progress_display
	{
	public:
		explicit progress_display(
			unsigned long expected_count,
			std::ostream& os = std::cout,
			const std::string& s1 = "\n",
			const std::string& s2 = "",
			const std::string& s3 = "")
			: m_os(os), m_s1(s1), m_s2(s2), m_s3(s3)
		{
			restart(expected_count);
		}
		void restart(unsigned long expected_count)
		{
			//_count = _next_tic_count = _tic = 0;
			_expected_count = expected_count;
			m_os << m_s1 << "0%   10   20   30   40   50   60   70   80   90   100%\n"
				<< m_s2 << "|----|----|----|----|----|----|----|----|----|----|"
				<< std::endl
				<< m_s3;
			if (!_expected_count)
			{
				_expected_count = 1;
			}
		}
		unsigned long operator += (unsigned long increment)
		{
			std::unique_lock<std::mutex> lock(mtx);
			if ((_count += increment) >= _next_tic_count)
			{
				display_tic();
			}
			return _count;
		}
		unsigned long  operator ++ ()
		{
			return operator += (1);
		}

		//unsigned long  operator + (int x)
		//{
		//	return operator += (x);
		//}

		unsigned long count() const
		{
			return _count;
		}
		unsigned long expected_count() const
		{
			return _expected_count;
		}
	private:
		std::ostream& m_os;
		const std::string m_s1;
		const std::string m_s2;
		const std::string m_s3;
		std::mutex mtx;
		std::atomic<size_t> _count{ 0 }, _expected_count{ 0 }, _next_tic_count{ 0 };
		std::atomic<unsigned> _tic{ 0 };
		void display_tic()
		{
			unsigned tics_needed = unsigned((double(_count) / _expected_count) * 50.0);
			do
			{
				m_os << '*' << std::flush;
			} while (++_tic < tics_needed);
			_next_tic_count = unsigned((_tic / 50.0) * _expected_count);
			if (_count == _expected_count)
			{
				if (_tic < 51) m_os << '*';
				m_os << std::endl;
			}
		}
	};
	/**
	 * A timer object measures elapsed time, and it is very similar to boost::timer.
	 */
	class timer
	{
	public:
		timer() : time_begin(std::chrono::steady_clock::now()) {};
		~timer() {};
		/**
		 * Restart the timer.
		 */
		void restart()
		{
			time_begin = std::chrono::steady_clock::now();
		}
		/**
		 * Measures elapsed time.
		 *
		 * @return The elapsed time
		 */
		double elapsed()
		{
			std::chrono::steady_clock::time_point time_end = std::chrono::steady_clock::now();
			return (std::chrono::duration_cast<std::chrono::microseconds>(time_end - time_begin).count())*1e-6;// / CLOCKS_PER_SEC;
		}
	private:
		std::chrono::steady_clock::time_point time_begin;
	};
}

struct Res//the result of knns
{
	int id = -1;
	float dist = FLT_MAX;
	Res() {}
	Res(int id_, float dist_) :id(id_), dist(dist_) {}
	Res(float dist_, int id_) :id(id_), dist(dist_) {}
	constexpr bool operator < (const Res& rhs) const noexcept {
		return dist < rhs.dist
			//|| (dist == rhs.dist && id < rhs.id)
			;
	}

	constexpr bool operator > (const Res& rhs) const noexcept {
		return dist > rhs.dist;
	}

	constexpr bool operator == (const Res& rhs) const noexcept {
		return id == rhs.id;
	}
};

inline float cal_inner_product(float* v1, float* v2, int dim)
{

  return calIp_fast(v1, v2, dim);

}

inline float cal_lengthSquare(float* v1, int dim)
{
	float res = 0.0;
	for (int i = 0; i < dim; ++i) {
		res += v1[i] * v1[i];
	}
	return res;
}
extern int _g_dist_mes;
inline float cal_dist(float* v1, float* v2, int dim)
{
  return calL2Sqr_fast(v1, v2, dim);

}

inline float cal_distSqrt(float* v1, float* v2, int dim)
{
  return calL2Sqr_fast(v1, v2, dim);
}

template <class T>
inline bool myFind(T* begin, T* end, const T& val)
{
	for (T* iter = begin; iter != end; ++iter) {
		if (*iter == val) return true;
	}
	return false;
}

void setW(std::string& datatsetName, float& R_min);

template <class T>
void clear_2d_array(T** array, int n)
{
	for (int i = 0; i < n; ++i) {
		delete[] array[i];
	}
	delete[] array;
}

void showMemoryInfo();

//template <class T>
inline int isUnique(std::vector<Res>& vec) {
	int len = vec.size();
	std::set<int> s;
	for (auto& x : vec) {
		s.insert(x.id);
	}
	//std::set<T> s(vec.begin(), vec.end());
	return len == s.size();
}

inline int isUnique(std::vector<int>& vec) {
	int len = vec.size();

	std::set<int> s(vec.begin(), vec.end());
	return len == s.size();
}

inline int isUnique(Res* sta, Res* end) {
	int len = end - sta;
	std::set<int> s;
	for (auto u = sta; u < end; ++u) {
		s.insert(u->id);
	}
	return len == s.size();
}

template <class T, class U>
int isUnique(std::map<U, T>& vec) {
	int len = 0;
	std::set<T> s;
	for (auto& x : vec) {
		s.insert(x.second);
		++len;
	}
	return len == s.size();
}

#include <mutex>
#include <deque>
#include <set>

namespace threadPoollib
{
	typedef unsigned short int vl_type;

	class VisitedList {
	public:
		vl_type curV;
		//vl_type* mass;
		std::unordered_set<int> mass;
		unsigned int numelements;

		VisitedList(int numelements1) {
			curV = -1;
			numelements = numelements1;
			//mass = new vl_type[numelements];
		}

		void reset() {
			curV++;
			if (curV == 0) {
				//memset(mass, 0, sizeof(vl_type) * numelements);
				curV++;
			}
		};

		~VisitedList() {
			//delete[] mass;
		}
	};
	///////////////////////////////////////////////////////////
	//
	// Class for multi-threaded pool-management of VisitedLists
	//
	/////////////////////////////////////////////////////////


	class VisitedListPool {
		std::deque<VisitedList*> pool;
		//std::mutex poolguard;
		int numelements;

	public:
		VisitedListPool(int initmaxpools, int numelements1) {
			numelements = numelements1;
			for (int i = 0; i < initmaxpools; i++)
				pool.push_front(new VisitedList(numelements));
		}

		VisitedList* getFreeVisitedList() {
			VisitedList* rez = nullptr;
			pool.front()->reset();
			//printf("currV=%d  numelements=%d\n", pool.front()->curV,pool.front()->numelements);
			return pool.front();

				//std::unique_lock <std::mutex> lock(poolguard);
				if (pool.size() > 0) {
			//		printf("popping\n");
					rez = pool.front();
					pool.pop_front();
			//		printf("popping success\n");
				}
				else {
			//		printf("newning\n");
					rez = new VisitedList(numelements);
				}
		//	printf("visited list %d\n", rez->curV);
		//	printf("trying to reset\n");
			rez->reset();
		//	printf("reset complete\n");
			return rez;
		};

		void releaseVisitedList(VisitedList* vl) {
			//std::unique_lock <std::mutex> lock(poolguard);
			pool.push_front(vl);
		};

		~VisitedListPool() {
			while (pool.size()) {
				VisitedList* rez = pool.front();
				pool.pop_front();
				delete rez;
			}
		};
	};
}
#endif
