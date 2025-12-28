#pragma once

#define USE_SQRDIST //use sqrDist to reduce the sqrt computation

struct Data
{
	// Dimension of data
	unsigned dim = 0;
	// Number of data
	unsigned N = 0;
	unsigned query_size = 0;
	unsigned oldN=0;
	// Data matrix
	float** val = nullptr;
	float** query=nullptr; // NO MORE THAN 200 POINTS
};

struct Ben
{
	unsigned N = 0;
	unsigned num = 0;
	int** indice = nullptr;
	float** dist = nullptr;
};

struct HashParam
{
	// the value of a in S hash functions
	float** rndAs = nullptr;
	// the value of b in S hash functions
	float* rndBs = nullptr;
	//
	//float W = 0.0f;

	//float calHash(float* point, )
};

#define RESET   "\033[0m"
#define BLACK   "\033[30m"      /* Black */
#define RED     "\033[31m"      /* Red */
#define GREEN   "\033[32m"      /* Green */
#define YELLOW  "\033[33m"      /* Yellow */
#define BLUE    "\033[34m"      /* Blue */
#define MAGENTA "\033[35m"      /* Magenta */
#define CYAN    "\033[36m"      /* Cyan */
#define WHITE   "\033[37m"      /* White */
#define BOLDBLACK   "\033[1m\033[30m"      /* Bold Black */
#define BOLDRED     "\033[1m\033[31m"      /* Bold Red */
#define BOLDGREEN   "\033[1m\033[32m"      /* Bold Green */
#define BOLDYELLOW  "\033[1m\033[33m"      /* Bold Yellow */
#define BOLDBLUE    "\033[1m\033[34m"      /* Bold Blue */
#define BOLDMAGENTA "\033[1m\033[35m"      /* Bold Magenta */
#define BOLDCYAN    "\033[1m\033[36m"      /* Bold Cyan */
#define BOLDWHITE   "\033[1m\033[37m"      /* Bold White */

//#define USE_TRI_INEQAUALITY

struct tPoints {
	int u;
	int v;
};


//extern double _chi2inv;
//extern double _chi2invSqr;
//extern double _coeff;

constexpr int _sspace = 8;
constexpr int _lspace = 12;
extern int _lsh_UB;
//#define DIV
