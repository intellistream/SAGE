//
// Created by Xi on March 2022
//

#include <LSHAPGIndex/alg.h>
int _lsh_UB=0;
//double _chi2inv;
//double _chi2invSqr;
//double _coeff;

int VIRmain(int argc, char const* argv[])
{
	float c = 1.5;
	unsigned k = 50;
	unsigned L = 8, K = 10;//NUS
	//L = 10, K = 5;
	float beta = 0.1;
	unsigned Qnum = 100;
	float W = 1.0f;
	int T = 24;
	int efC = 80;
	L = 2;
	K = 18;
	double pC = 0.95, pQ = 0.9;
	std::string datasetName;
	bool isbuilt = 0;
	_lsh_UB=0;
	if (argc > 1) datasetName = argv[1];
	if (argc > 2) isbuilt = std::atoi(argv[2]);
	if (argc > 3) k = std::atoi(argv[3]);
	if (argc > 4) L = std::atoi(argv[4]);
	if (argc > 5) K = std::atoi(argv[5]);
	if (argc > 6) T = std::atoi(argv[6]);
	if (argc > 7) efC = std::atoi(argv[7]);
	if (argc > 8) pC = std::atof(argv[8]);
	if (argc > 9) pQ = std::atof(argv[9]);
	if (argc > 10) _lsh_UB = std::atoi(argv[10]);
	if (argc == 1) {
		const std::string datas[] = { "audio","mnist","cifar","NUS","Trevi","gist","deep1m","skew_10M_8d","gauss_8d","gauss_25w_128" };
		datasetName = datas[0];
		//datasetName = "sift1B";
		setW(datasetName, W);
		std::cout << "Using the default configuration!\n\n";
	}

	#if defined(unix) || defined(__unix__)
		std::string data_fold = "../../dataset/", index_fold = "./indexes/";
	#else
		std::string data_fold = "E:/Dataset_for_c/", index_fold = data_fold + "graphIndex/";
	#endif



	std::cout << "Using LSH-Graph for " << datasetName << " ..." << std::endl;
	std::cout << "c=        " << c << std::endl;
	std::cout << "k=        " << k << std::endl;
	std::cout << "L=        " << L << std::endl;
	std::cout << "K=        " << K << std::endl;
	std::cout << "T=        " << T << std::endl;
	std::cout << "lsh_UB=   " << _lsh_UB << std::endl;
	Preprocess prep(data_fold + datasetName + ".data", data_fold + "ANN/" + datasetName + ".bench_graph");

	//return 0;

	showMemoryInfo();

	std::string path = index_fold + datasetName + ".index";
	Parameter param1(prep, L, K, 1.0f);
	param1.W = 0.3f;
	zlsh* gLsh= nullptr;
	divGraph* divG = nullptr;
	if (isbuilt&&find_file(path + "_divGraph")) {
		divG = new divGraph(&prep, path + "_divGraph", pQ);

		divG->L = L;
		if (L == 0) divG->coeffq = 0;
	}
	else {
		if (!GenericTool::CheckPathExistence(index_fold.c_str())) {
			GenericTool::EnsurePathExistence(index_fold.c_str());
		}
		divG = new divGraph(prep, param1, path + "_divGraph", T, efC, pC, pQ);
	}

	//divG->traverse();
	//return 0;

	std::cout << "Loading FastGraph...\n";
	fastGraph* fsG = new fastGraph(divG);

	std::stringstream ss;
	ss  << "*******************************************************************************************************\n"
		<< "The result of LSH-G for " << datasetName << " is as follow: "<< "k=" << k<< ", probQ = " << pQ << ", L = " << L << ", K = " << K << ", T = " << T
		<< "\n"
		<< "******************************************************************************************************\n";

	ss << std::setw(_lspace) << "algName"
		<< std::setw(_sspace) << "k"
		<< std::setw(_sspace) << "ef"
		<< std::setw(_lspace) << "Time"
		<< std::setw(_lspace) << "Recall"
		//<< std::setw(_lspace) << "Ratio"
		<< std::setw(_lspace) << "Cost"
		<< std::setw(_lspace) << "CPQ1"
		<< std::setw(_lspace) << "CPQ2"
		<< std::setw(_lspace) << "Pruning"
		//<< std::setw(_lspace) << "MaxHop"
		<< std::endl
		<< std::endl;

	std::cout << ss.str();

	std::string query_result(divG->getFilename());
	auto idx = query_result.rfind('/');
	query_result.assign(query_result.begin(), query_result.begin() + idx + 1);
	query_result += "result.txt";
	std::ofstream os(query_result, std::ios_base::app);
	os.seekp(0, std::ios_base::end);
	os << ss.str();
	os.close();

	std::vector<size_t> efs;
	for (int i = k; i < 100; i += 10) {
		efs.push_back(i);
	}

#ifdef _DEBUG
#else
	for (int i = 100; i < 250; i += 10) {
		efs.push_back(i);
	}
	for (int i = 250; i < 300; i += 50) {
		efs.push_back(i);
	}
	//for (int i = 500; i < 3000; i += 300) {
	//	efs.push_back(i);
	//}
	//if (datasetName == "mnist") {
	//	for (int i = 500; i < 6000; i += 300) {
	//		efs.push_back(i);
	//	}
	//}
#endif // _DEBUG
	if (k == 50) {
		// for (auto& ef : efs) {
		// 	if (divG) divG->ef = ef;
		// 	graphSearch(c, k, divG, prep, beta, datasetName, data_fold, 2);
		// }
		// std::cout << std::endl;
	}
	else {
		std::vector<int> ks = { 1,10,20,30,40,50,60,70,80,90,100 };

		for (auto& kk : ks) {
			k = kk;

			if (divG) divG->ef = k + 150;
			graphSearch(c, k, divG, prep, beta, datasetName, data_fold, 2);

			//for (auto& ef : efs) {
			//	if (ef < k) continue;
			//	if (divG) divG->ef = ef;
			//	graphSearch(c, kk, divG, prep, beta, datasetName, data_fold, 2);
			//}
			std::cout << std::endl;
		}
	}


	//for (auto& ef : efs) {
	//	if (divG) divG->ef = ef;
	//	graphSearch(c, k, divG, prep, beta, datasetName, data_fold, 3);
	//}
	//std::cout << std::endl;
	efs={200};
	for (auto& ef : efs) {
		if (fsG) fsG->ef = ef;
		graphSearch(c, k, fsG, prep, beta, datasetName, data_fold, 0);
	}

	std::vector<float> pts={0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95};

	std::cout << std::endl;

	//for (auto& ef : efs) {
	//	if (fsG) fsG->ef = ef;
	//	graphSearch(c, k, fsG, prep, beta, datasetName, data_fold, 1);
	//}
	//std::cout << std::endl;

	time_t now = time(0);


	time_t zero_point = 1635153971 - 17 * 3600 - 27 * 60;//Let me set the time at 2021.10.25. 17:27 as the zero point
	size_t diff = (size_t)(now - zero_point);

	//ss.flush();
	//ss.erase_event();
	ss.str("");
#if defined(unix) || defined(__unix__)
	llt lt(diff);
#endif

#if defined(unix) || defined(__unix__)
	ss << "\n******************************************************************************************************\n"
		<< "                                                                                    "
		<< lt.date << '-' << lt.h << ':' << lt.m << ':' << lt.s
		<< "\n*****************************************************************************************************\n\n\n";
#else
	tm* ltm = new tm[1];
	localtime_s(ltm, &now);
	ss << "\n******************************************************************************************************\n"
		<< "                                                                                    "
		<< ltm->tm_mon + 1 << '-' << ltm->tm_mday << ' ' << ltm->tm_hour << ':' << ltm->tm_min
		<< "\n*****************************************************************************************************\n\n\n";
#endif
	std::ofstream os1(query_result, std::ios_base::app);
	os1.seekp(0, std::ios_base::end);
	os1 << ss.str();
	os1.close();
	std::cout << ss.str();
	return 0;
}
