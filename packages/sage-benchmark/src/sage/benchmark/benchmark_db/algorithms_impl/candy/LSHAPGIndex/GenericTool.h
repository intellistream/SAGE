//This file contains some neat implementations of useful tool functions
//by GS
#ifndef _GENERIC_TOOL_H_
#define _GENERIC_TOOL_H_

#pragma once

//#include "Common.h"

//Cross Platform snprintf
#include <cstdio>
#include <cstdarg>

using namespace std;

#ifdef _MSC_VER
//Under vc, we have to use some simulation
int msvc_snprintf(char *str, size_t size, const char *format, ...);
#define c99_snprintf msvc_snprintf
#else
#ifdef __GNUC__
//Under g++, we just directly use snprintf
#define c99_snprintf snprintf
#else
//For other compiler, we output error
int other_snprintf(char *str, size_t size, const char *format, ...);
#define c99_snprintf other_snprintf
#endif
#endif

//Random Number Handling using MT19937 library
//#include "mt19937ar.h"

//init seed function
#define setseed(seed) init_genrand(seed)

//can change to different variaion in mt19937 library
//this version get double value in [0,1)
#define getrand() genrand_real2()

//Some Cross Platform Important Functions
#include <cmath>
#include <ctime>
#include <algorithm>
#include <iterator>
#include <cstdio>
#include <cerrno>
#include <cfloat>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <fstream>

using namespace std;

class GenericTool
{
public:
	//generic purpose tool function
	static int CountBit(int num);

	//for file manipulation
	static bool CheckPathExistence(const char *path);
	static int RegularizeDirPath(const char *path, char *buffer);
	static void EnsurePathExistence(const char *path);
	static int GetCombinedPath(const char *dir, const char *file, char *buffer);
	static bool JudgeExistence(const char *full_path, bool force_new);
	static int ChangeFileExtension(const char *full_path, const char *new_ext, char *buffer);

	//random number related and data generation
	static double GetGaussianRandom(double mean, double sigma);

	//some useful templates
	template <typename T> static T DotProduct(int dim, T *a, T *b);
	template <typename T> static T GetSign(T val);

	//for simple matrix operation
	//T should be float, double or long double to make sense
	template <typename T> static T **AllocateMatrix(int m, int n); //we also assign every element with zero
	template <typename T> static T **CopyMatrix(T **mat, int m, int n);
	template <typename T> static void ReleaseMatrix(T **mat, int m, int n);
	template <typename T> static void OutMatrix(T **mat, int m, int n);
	template <typename T> static bool GaussJordanElimination(T **mat, int m, int n); //Gaussian Elimination for matrix m(total row)x n(total column)
	template <typename T> static bool InverseMatrix(T **mat, int m, T **inv); //inverse mxm matrix

	//functions for discretization
	//typename T should be floating type
	template <typename T> static int DiscreteValueFloor(T val, int seg_num);
	template <typename T> static int DiscreteValueFloor(T val, int seg_num, T val_min, T val_max);
	template <typename T> static int DiscreteValueCeil(T val, int seg_num);
	template <typename T> static int DiscreteValueCeil(T val, int seg_num, T val_min, T val_max);
	template <typename T> static T ContinuousValueFloor(int seg_id, int seg_num);
	template <typename T> static T ContinuousValueFloor(int seg_id, int seg_num, T val_min, T val_max);
	template <typename T> static T ContinuousValueCeil(int seg_id, int seg_num);
	template <typename T> static T ContinuousValueCeil(int seg_id, int seg_num, T val_min, T val_max);

	//for indirect compare
	template <typename T>
	struct indirect_comp_less
	{
		T *ref_data;

		indirect_comp_less(T *scores) : ref_data(scores) {}
		bool operator()(const int id1, const int id2) const
		{
			if(ref_data[id1]<ref_data[id2]) return true;
			else return false;
		}
	};

	template <typename T>
	struct indirect_comp_greater
	{
		T *ref_data;

		indirect_comp_greater(T *scores) : ref_data(scores) {}
		bool operator()(const int id1, const int id2) const
		{
			if(ref_data[id1]>ref_data[id2]) return true;
			else return false;
		}
	};
};

inline int GenericTool::CountBit(int num)
{
	int count=0;
	while(num)
	{
		count++;
		num&=(num-1); //every time we reduce the number of "1" in the binary representation of num by 1
	}
	return count;
}

template<typename T>
inline T GenericTool::DotProduct(int dim, T *a, T *b)
{
	T res=0;
	for(int i=0;i<dim;i++) res+=a[i]*b[i];
	return res;
}

template <typename T>
inline T GenericTool::GetSign(T val)
{
	return (T)((val>0)-(val<0));
}

//templates for matri operations
template <typename T>
inline T **GenericTool::AllocateMatrix(int m, int n)
{
	T **mat=new (T*[m]);
	for(int i=0;i<m;i++)
	{
		mat[i]=new T[n];
		memset(mat[i], 0, n*sizeof(T));
	}
	return mat;
}

template <typename T>
inline T **GenericTool::CopyMatrix(T **mat, int m, int n)
{
	T **copy_mat=AllocateMatrix<T>(m, n);
	for(int i=0;i<m;i++) memcpy(copy_mat[i], mat[i], n*sizeof(T));

	return copy_mat;
}

template <typename T>
inline void GenericTool::ReleaseMatrix(T **mat, int m, int n)
{
	for(int i=0;i<m;i++) delete[] mat[i];
	delete[] mat;
}

template <typename T>
inline void GenericTool::OutMatrix(T **mat, int m, int n)
{
	for(int i=0;i<m;i++)
	{
		for(int j=0;j<n;j++) cout <<mat[i][j]<<' ';
		cout <<endl;
	}
}

template <typename T>
inline bool GenericTool::GaussJordanElimination(T **mat, int m, int n)
{
	int i=0;
	int j=0;

	while((i<m)&&(j<n))
	{
		//find pivot in column j, starting fron row i
		int maxi=i;
		T mx=mat[i][j];
		for(int k=i+1;k<m;k++)
		{
			if(abs(mat[k][j])>abs(mx))
			{
				mx=mat[k][j];
				maxi=k;
			}
		}

		//if max is zero then we cannot continue
		if(mx!=0)
		{
			//swap row
			if(maxi!=i)
			{
				T *temp_row=mat[i];
				mat[i]=mat[maxi];
				mat[maxi]=temp_row;
			}

			for(int k=j;k<n;k++) mat[i][k]/=mx;
			for(int k=0;k<m;k++)
			{
				if(k==i) continue;

				T mul=mat[k][j];
				for(int l=j;l<n;l++) mat[k][l]-=mul*mat[i][l];
			}
		}
		else return false;

		i++;
		j++;
	}

	return true;
}

template <typename T>
inline bool GenericTool::InverseMatrix(T **mat, int m, T **inv)
{
	T **temp=AllocateMatrix<T>(m, 2*m);
	for(int i=0;i<m;i++)
	{
		memcpy(temp[i], mat[i], m*sizeof(T));
		temp[i][m+i]=1;
	}

	if(!GaussJordanElimination(temp, m, 2*m))
	{
		ReleaseMatrix(temp, m, 2*m);
		return false;
	}
	else
	{
		for(int i=0;i<m;i++) memcpy(inv[i], temp[i]+m, m*sizeof(T));
		ReleaseMatrix(temp, m, 2*m);
		return true;
	}
}

#endif
