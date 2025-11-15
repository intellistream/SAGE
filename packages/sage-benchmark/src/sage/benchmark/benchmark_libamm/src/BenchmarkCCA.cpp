/*! \file Benchmark.h*/

/**
 * @brief This is the main entry point of the entire program.
 * We use this as the entry point for benchmarking.
 */
#include <LibAMM.h>
#include <Utils/UtilityFunctions.h>
#include <Streaming/Streamer.h>
#include <cstdlib> // For the exit() function
#include <iostream>
#include <filesystem>
#include <regex>

using namespace std;
using namespace INTELLI;
using namespace torch;
using namespace DIVERSE_METER;
using namespace LibAMM;
namespace fs = std::filesystem;

void printStatsOfTensor(torch::Tensor M) {
  torch::Tensor mean = at::mean(M);
  torch::Tensor std = at::std(M);
  torch::Tensor max_val = at::max(M);
  torch::Tensor min_val = at::min(M);

  // Print the results
  std::cout << "Mean:" << mean.item<float>() << std::endl;
  std::cout << "Standard Deviation:" << std.item<float>() << std::endl;
  std::cout << "Max value: " << max_val.item<float>() << std::endl;
  std::cout << "Min value: " << min_val.item<float>() << std::endl;
}

 /**
 * @brief For PQ and VQ, the prototype and index&book need to change if we perform different matrix multiplication, e.g. ATA, BTB. so we need to update the cfg path and call cppAlgoPtr->setConfig(cfg)
 */
void adjustConfig(ConfigMapPtr cfg, std::string stage){

    // e.g. torchscripts/VQ/CodewordLookUpTable/MNIST_AA_m10_lA3_lB3.pth, torchscripts/VQ/CodewordLookUpTable/MediaMill_AB_m1_lA12_lB10.pth

    std::string search_directory = "./torchscripts/VQ/CodewordLookUpTable/";
    std::string datasetName = cfg->tryString("matrixLoaderTag", "MediaMill", true);
    std::string m;
    if (cfg->tryString("cppAlgoTag", "mm", true)=="pq"){m="10";}
    else if (cfg->tryString("cppAlgoTag", "mm", true)=="vq"){m="1";}
    std::regex pattern(datasetName+"_"+stage+"_m"+m+"_.*pth");

    for (const auto& entry : fs::directory_iterator(search_directory)) {
        if (fs::is_regular_file(entry.path())) {
            std::string filename = entry.path().filename().string();
            if (std::regex_match(filename, pattern)) {
                std::cout << "Found matching file: " << entry.path() << std::endl;
                cfg->edit("pqvqCodewordLookUpTablePath", entry.path());
            }
        }
    }
}
class CCAChecker{
public:
  CCAChecker() = default;

  ~CCAChecker() = default;
public:
  // torch::Tensor A, B, At, Bt;
  torch::Tensor Sxx, Syy, Sxy;
  torch::Tensor SxxNegativeHalf, SyyNegativeHalf, M, M1;
  torch::Tensor correlation;
  void calculate_correlation(torch::Tensor A, torch::Tensor B,torch::Tensor At,torch::Tensor Bt)
  {

  // Sxx, Syy, Sxy: covariance matrix
  Sxx = torch::matmul(A, At) / A.size(1); // 120*120
  Syy = torch::matmul(B, Bt) / A.size(1); // 101*101
  Sxy = torch::matmul(A, Bt) / A.size(1); // 120*101
  INTELLI_INFO("sxx, sxy,syy done ");
  // Sxx^(-1/2), Syy^(-1/2), M
  // Sxx^(-1/2) 120*120
  torch::Tensor eigenvaluesSxx, eigenvectorsSxx;
  std::tie(eigenvaluesSxx, eigenvectorsSxx) = torch::linalg::eig(Sxx); // diagonization
  INTELLI_INFO("eigen x done ");
  torch::Tensor diagonalMatrixSxx = torch::diag(
      1.0 / torch::sqrt(eigenvaluesSxx + torch::full({}, 1e-12))); // 1/sqrt(eigenvalue+epsilon) +epsilon to avoid nan
  SxxNegativeHalf = torch::matmul(torch::matmul(eigenvectorsSxx, diagonalMatrixSxx), eigenvectorsSxx.t());
  SxxNegativeHalf = at::real(SxxNegativeHalf); // ignore complex part, it comes from numerical computations
  // Syy^(-1/2) 101*101
  torch::Tensor eigenvaluesSyy, eigenvectorsSyy;
  INTELLI_INFO("neg half x done ");
  std::tie(eigenvaluesSyy, eigenvectorsSyy) = torch::linalg::eig(Syy);
  INTELLI_INFO("eig y done ");
  torch::Tensor diagonalMatrixSyy = torch::diag(1.0 / torch::sqrt(eigenvaluesSyy + torch::full({}, 1e-12)));
  SyyNegativeHalf = torch::matmul(torch::matmul(eigenvectorsSyy, diagonalMatrixSyy), eigenvectorsSyy.t());
  SyyNegativeHalf = at::real(SyyNegativeHalf);
  INTELLI_INFO("neg half y done ");
  // M 120*101
  M1 = torch::matmul(SxxNegativeHalf.t(), Sxy);
  M = torch::matmul(M1, SyyNegativeHalf);

  // correlation
  torch::Tensor U, S, Vh;
  std::tie(U, S, Vh) = torch::linalg::svd(M, false, c10::nullopt);
  correlation = torch::clamp(S, -1.0, 1.0);
  }
};

void benchmarkCCA(std::string configName) {

    // Step1. Set up environments
    ConfigMapPtr cfg = newConfigMap();
    cfg->fromFile(configName);
    INTELLI_INFO(cfg->toString());
    uint64_t coreBind = cfg->tryU64("coreBind", 0, true);
    UtilityFunctions::bind2Core((int) coreBind);
    // 1.1 AMM algorithm
    LibAMM::CPPAlgoTable cppAlgoTable;
    std::string cppAlgoTag = cfg->tryString("cppAlgoTag", "mm", true);
    LibAMM::AbstractCPPAlgoPtr cppAlgoPtr = cppAlgoTable.findCppAlgo(cppAlgoTag);
    INTELLI_INFO("1.1 algo: " + cppAlgoTag);
    // 1.2 matrixLoader uses MNIST dataset
    std::string matrixLoaderTag = cfg->tryString("matrixLoaderTag", "MediaMill", true);
    INTELLI_INFO("1.2 matrixLoaderTag: " + matrixLoaderTag);
    LibAMM::MatrixLoaderTable mLoaderTable;
    //std::shared_ptr<LibAMM::AbstractMatrixLoader> matLoaderPtr;
    auto matLoaderPtr = mLoaderTable.findMatrixLoader(matrixLoaderTag);
   /* if (matrixLoaderTag=="MediaMill"){
        matLoaderPtr = std::dynamic_pointer_cast<LibAMM::MediaMillMatrixLoader>(mLoaderTable.findMatrixLoader("MediaMill"));
        // std::cout << "1 The type of myVariable is: " << typeid(matLoaderPtr).name() << std::endl;
    }
    else if (matrixLoaderTag=="MNIST"){
        matLoaderPtr = std::dynamic_pointer_cast<LibAMM::MNISTMatrixLoader>(mLoaderTable.findMatrixLoader("MNIST"));
        // std::cout << "2 The type of myVariable is: " << typeid(matLoaderPtr).name() << std::endl;
    }
    else{
        INTELLI_ERROR(matrixLoaderTag+" not found");
        std::exit(EXIT_FAILURE);
    }*/

    // if (matrixLoaderTag=="MediaMill"){
    //     std::shared_ptr<LibAMM::MediaMillMatrixLoader> matLoaderPtr = std::dynamic_pointer_cast<LibAMM::MediaMillMatrixLoader>(mLoaderTable.findMatrixLoader(matrixLoaderTag));
    // }
    // else if (matrixLoaderTag=="MNIST"){
    //     std::shared_ptr<LibAMM::MNISTMatrixLoader> matLoaderPtr = std::dynamic_pointer_cast<LibAMM::MNISTMatrixLoader>(mLoaderTable.findMatrixLoader(matrixLoaderTag));
    // }
    // else{
    //     INTELLI_ERROR(matrixLoaderTag+" not found");
    //     std::exit(EXIT_FAILURE);
    // }
    assert(matLoaderPtr);
    matLoaderPtr->setConfig(cfg);
    auto A = matLoaderPtr->getA(); // 120*43907 double or 392*60000 float
    auto B = matLoaderPtr->getB(); // 101*43907 double or 392*60000 float
    auto At = A.t();
    auto Bt = B.t();
    CCAChecker checker;
    INTELLI_INFO("1.2 run checker ");
    checker.calculate_correlation(A,B,At,Bt); // cleaner code
     INTELLI_INFO("1.2 done checker " );
    // 1.3 sketch dimension
    uint64_t sketchSize;
    sketchSize = cfg->tryU64("sketchDimension", 1, true);
    INTELLI_INFO("1.3 sketch dimension: " + to_string(sketchSize));

    // uint64_t isStreaming = cfg->tryU64("isStreaming", 0, true);
    // uint64_t streamingTwoMatrices = cfg->tryU64("streamingTwoMatrices", 0, true);
    // if (isStreaming!=streamingTwoMatrices){
    //     INTELLI_ERROR("isStreaming, streamingTwoMatrices must be both 0 or 1");
    //     exit(EXIT_FAILURE);
    // }

    uint64_t staticDataSet = cfg->tryU64("staticDataSet", 1, true);
    uint64_t fullLazy = cfg->tryU64("fullLazy", 1, true);

    uint64_t threads = cfg->tryU64("threads", 1, true);
    if (threads!=1){
        INTELLI_ERROR("only single thread");
        exit(EXIT_FAILURE);
    }

    // Step2. AMM
    ConfigMapPtr allMetrics;
    torch::Tensor Sxx, Sxy, Syy;

    // if (isStreaming){
    //     INTELLI_INFO("Runing AMM streaming");
    //     B=Bt; // A: 392*60000, B:60000*392

    //     LibAMM::SingleThreadStreamer ss;
    //     ConfigMapPtr cfgGlobal = cfg;
    //     uint64_t aRows = A.size(0);
    //     cfgGlobal->edit("streamingTupleCnt", (uint64_t) aRows);
    //     uint64_t batchSize = cfg->tryU64("batchSize", 1, true);
    //     if (batchSize > aRows) {
    //         batchSize = aRows;
    //     }
    //     LibAMM::TimeStamper tsGen,tsGenB;
    //     tsGen.setConfig(cfgGlobal);
    //     std::vector<LibAMM::AMMTimeStampPtr> myTs = tsGen.getTimeStamps();

    //     tsGenB.setSeed(7758258);
    //     tsGenB.setConfig(cfgGlobal);
    //     std::vector<LibAMM::AMMTimeStampPtr> myTsB = tsGenB.getTimeStamps();
    //     INTELLI_INFO("Generate time stamps for two streams done");
    //     Sxy = torch::zeros({A.size(0), B.size(1)});
    //     Sxx = torch::zeros({A.size(0), A.size(0)});
    //     Syy = torch::zeros({B.size(1), B.size(1)});
    //     // INTELLI_INFO("Shape of matrix Sxy: " + torch::str(Sxy.sizes()));
    //     // INTELLI_INFO("Shape of matrix Sxx: " + torch::str(Sxx.sizes()));
    //     // INTELLI_INFO("Shape of matrix Syy: " + torch::str(Syy.sizes()));

    //     //INTELLI_INFO("I am mm");
    //     INTELLI_INFO("Start Streaming A rows and B cols");
    //     uint64_t startRow = 0;
    //     uint64_t endRow = startRow + batchSize;
    //     uint64_t tNow = 0;
    //     uint64_t tEXpectedArrival = myTs[endRow - 1]->arrivalTime;
    //     if(myTsB[endRow-1]->arrivalTime>tEXpectedArrival)
    //     {
    //         tEXpectedArrival=myTsB[endRow-1]->arrivalTime;
    //     }
    //     uint64_t tDone = 0;

    //     ThreadPerf pef(-1);
    //     pef.setPerfList();
    //     pef.start();

    //     auto tstart = std::chrono::high_resolution_clock::now();
    //     // struct timeval tstart;
    //     // gettimeofday(&tstart, NULL);
    //     uint64_t iterationCnt=0;
    //     torch::Tensor incomingA,incomingB,oldArrivedB,oldArrivedA;
    //     uint64_t aBCols=0,lastABCols=0;
    //     while (startRow < aRows) {
    //         tNow = chronoElapsedTime(tstart);;
    //         //auto subA = A.slice(0, startRow, endRow);
    //         incomingA =A.slice(0, startRow, endRow);
    //         incomingB=B.slice(1,startRow,endRow);
    //         oldArrivedB=B.slice(1,0,endRow);
    //         while (tNow < tEXpectedArrival) {
    //         tNow = chronoElapsedTime(tstart);;
    //         //usleep(1);
    //         }
    //         INTELLI_INFO("batch of " + to_string(startRow) + " to " + to_string(endRow) + " are ready");
    //         /**
    //          * @brief do the incomingA*oldArrivedB part to get Sxy[startRow:endRow, 0:aBCols]
    //          */
    //         torch::manual_seed(123);
    //         auto aB=cppAlgoPtr->amm(incomingA, oldArrivedB, sketchSize);
    //         lastABCols=aBCols;
    //         aBCols=aB.size(1);
    //         Sxy.slice(0,startRow,endRow).slice(1,0,aBCols).copy_(aB);
    //         /**
    //         * @brief do the oldArrivedA*incomingB part
    //         */
    //         if(iterationCnt!=0)
    //         {
    //             torch::manual_seed(123);
    //             auto aB2=cppAlgoPtr->amm(oldArrivedA, incomingB, sketchSize);
    //             uint64_t aB2Rows=aB2.size(0);
    //             uint64_t aB2Cols=aB2.size(1);
    //             Sxy.slice(0,0,aB2Rows).slice(1,lastABCols,lastABCols+aB2Cols).copy_(aB2);
    //         }
    //         oldArrivedA=A.slice(0, 0, endRow);
    //         /**
    //         * @brief do the incomingA*oldArrivedA part
    //         */
    //         torch::manual_seed(123);
    //         auto aA=cppAlgoPtr->amm(incomingA, oldArrivedA.t(), sketchSize);
    //         Sxx.slice(0,startRow,endRow).slice(1,0,aBCols).copy_(aA);
    //         Sxx.slice(0,0,aBCols).slice(1,startRow,endRow).copy_(aA.t()); // every time batch_size*batch_size part will be overwrite

    //         torch::manual_seed(123);
    //         auto bB=cppAlgoPtr->amm(oldArrivedB.t(), incomingB, sketchSize);
    //         Syy.slice(0,0,aBCols).slice(1,startRow,endRow).copy_(bB);
    //         Syy.slice(0,startRow,endRow).slice(1,0,aBCols).copy_(bB.t());

    //         /**
    //          * @brief update the indexes
    //          */
    //         startRow += batchSize;
    //         endRow += batchSize;
    //         if (endRow >= aRows) {
    //         endRow = aRows;
    //         }
    //         tEXpectedArrival = myTs[endRow - 1]->arrivalTime;
    //         if(myTsB[endRow-1]->arrivalTime>tEXpectedArrival)
    //         {
    //         tEXpectedArrival=myTsB[endRow-1]->arrivalTime;
    //         }
    //         iterationCnt++;
    //     }
    //     tDone = chronoElapsedTime(tstart);
    //     pef.end();
    //     /**
    //      * @brief The latency calculation is different from one stream case here,
    //      * as older A will still be probed by newer B
    //      */
    //         for (size_t i = 0; i < aRows; i++) {
    //         myTs[i]->processedTime = tDone;
    //         }

    //     allMetrics = pef.resultToConfigMap();
    //     INTELLI_INFO("Done in " + to_string(tDone) + "us");
    //     double throughput = aRows * 1e6 / tDone;
    //     double throughputByElements = throughput * A.size(1);
    //     double latency95 = ss.getLatencyPercentage(0.95);
    //     allMetrics->edit("throughput", throughput);
    //     allMetrics->edit("throughputByElements", throughputByElements);
    //     allMetrics->edit("95%latency", latency95);
    //     allMetrics->addPrefixToKeys("AMM");

    //     Sxx = Sxx/A.size(1);
    //     Syy = Syy/A.size(1);
    //     Sxy = Sxy/A.size(1);
    // }
     torch::manual_seed(999);
    if ((staticDataSet!=1) || (fullLazy!=1)){
        INTELLI_ERROR("Must be staticDataSet=1 and fullLazy=1");
        exit(EXIT_FAILURE);
    }
    else{
        INTELLI_INFO("staticDataSet=1 and fullLazy=1");
        ThreadPerf pef(-1);
        pef.setPerfList();
        uint64_t ammTime=0;
        // vq
        adjustConfig(cfg, "AA"); // update cfg index book prototype path
        cppAlgoPtr->setConfig(cfg); // update cfg index book prototype path
        torch::manual_seed(123); // CRS requires same sampling seed
        pef.start();
        Sxx = cppAlgoPtr->amm(A, At, sketchSize);
        pef.end();
        Sxx=Sxx/A.size(1);
        ammTime+=pef.resultToConfigMap()->getU64("perfElapsedTime");
        std::cout << "Sxx:" << std::endl;
        std::cout << "Maximum Value: " << Sxx.max().item<float>() << std::endl;
        std::cout << "Mean Value: " << Sxx.mean().item<float>() << std::endl;
        std::cout << "Minimum Value: " << Sxx.min().item<float>() << std::endl;
        std::cout << "checker.Sxx:" << std::endl;
        std::cout << "Maximum Value: " << checker.Sxx.max().item<float>() << std::endl;
        std::cout << "Mean Value: " << checker.Sxx.mean().item<float>() << std::endl;
        std::cout << "Minimum Value: " << checker.Sxx.min().item<float>() << std::endl;

        adjustConfig(cfg, "BB"); // update cfg index book prototype path
        cppAlgoPtr->setConfig(cfg); // update cfg index book prototype path
        torch::manual_seed(123); // CRS requires same sampling seed
        pef.start();
        Syy = cppAlgoPtr->amm(B, Bt, sketchSize);
        pef.end();
        Syy=Syy/A.size(1);
        ammTime+=pef.resultToConfigMap()->getU64("perfElapsedTime");
        std::cout << "Syy:" << std::endl;
        std::cout << "Maximum Value: " << Syy.max().item<float>() << std::endl;
        std::cout << "Mean Value: " << Syy.mean().item<float>() << std::endl;
        std::cout << "Minimum Value: " << Syy.min().item<float>() << std::endl;
        std::cout << "checker.Syy:" << std::endl;
        std::cout << "Maximum Value: " << checker.Syy.max().item<float>() << std::endl;
        std::cout << "Mean Value: " << checker.Syy.mean().item<float>() << std::endl;
        std::cout << "Minimum Value: " << checker.Syy.min().item<float>() << std::endl;

        adjustConfig(cfg, "AB"); // update cfg index book prototype path
        cppAlgoPtr->setConfig(cfg); // update cfg index book prototype path
        torch::manual_seed(123); // CRS requires same sampling seed
        pef.start();
        Sxy = cppAlgoPtr->amm(A, Bt, sketchSize);
        pef.end();
        Sxy=Sxy/A.size(1);
        ammTime+=pef.resultToConfigMap()->getU64("perfElapsedTime");
        std::cout << "Sxy:" << std::endl;
        std::cout << "Maximum Value: " << Sxy.max().item<float>() << std::endl;
        std::cout << "Mean Value: " << Sxy.mean().item<float>() << std::endl;
        std::cout << "Minimum Value: " << Sxy.min().item<float>() << std::endl;
        std::cout << "checker.Sxy:" << std::endl;
        std::cout << "Maximum Value: " << checker.Sxy.max().item<float>() << std::endl;
        std::cout << "Mean Value: " << checker.Sxy.mean().item<float>() << std::endl;
        std::cout << "Minimum Value: " << checker.Sxy.min().item<float>() << std::endl;

       // pef.end();
        allMetrics = pef.resultToConfigMap();
        allMetrics->addPrefixToKeys("AMM");
        double throughput = (A.size(0) * 1e6) /ammTime;
        allMetrics->edit("AMMThroughput", throughput);
        allMetrics->edit("AMMPerfElapsedTime",(uint64_t)ammTime);
    }
    allMetrics->edit("SxxFroError", (double) INTELLI::UtilityFunctions::relativeFrobeniusNorm(checker.Sxx, Sxx));
    allMetrics->edit("SxyFroError", (double) INTELLI::UtilityFunctions::relativeFrobeniusNorm(checker.Sxy, Sxy));
    allMetrics->edit("SyyFroError", (double) INTELLI::UtilityFunctions::relativeFrobeniusNorm(checker.Syy, Syy));

    // Step3. The rest of the CCA task
    ThreadPerf pef(-1);
    pef.setPerfList();
    pef.start();
    // 3.1 Sxx^(-1/2)
    INTELLI_INFO("Sxx^(-1/2)");
    torch::Tensor eigenvaluesSxx, eigenvectorsSxx;
	std::tie(eigenvaluesSxx, eigenvectorsSxx) = torch::linalg::eig(Sxx); // diagonization
	torch::Tensor diagonalMatrixSxx = torch::diag(1.0 / torch::sqrt(eigenvaluesSxx+torch::full({}, 1e-12))); // 1/sqrt(eigenvalue+epsilon) +epsilon to avoid nan
	torch::Tensor SxxNegativeHalf = torch::matmul(torch::matmul(eigenvectorsSxx, diagonalMatrixSxx), eigenvectorsSxx.t());
    SxxNegativeHalf = at::real(SxxNegativeHalf); // ignore complex part, it comes from numerical computations
    // 3.2 Syy^(-1/2)
    INTELLI_INFO("Syy^(-1/2)");
	torch::Tensor eigenvaluesSyy, eigenvectorsSyy;
	std::tie(eigenvaluesSyy, eigenvectorsSyy) = torch::linalg::eig(Syy);
	torch::Tensor diagonalMatrixSyy = torch::diag(1.0 / torch::sqrt(eigenvaluesSyy+torch::full({}, 1e-12)));
	torch::Tensor SyyNegativeHalf = torch::matmul(torch::matmul(eigenvectorsSyy, diagonalMatrixSyy), eigenvectorsSyy.t());
	SyyNegativeHalf = at::real(SyyNegativeHalf);
    // 3.3 M
    INTELLI_INFO("M");
    torch::manual_seed(123);
    // torch::Tensor M1 = cppAlgoPtr->amm(SxxNegativeHalf.t(), Sxy, 39);
    torch::Tensor M1 = torch::matmul(SxxNegativeHalf.t(), Sxy);
    std::cout << "M1:" << std::endl;
    std::cout << "Maximum Value: " << M1.max().item<float>() << std::endl;
    std::cout << "Mean Value: " << M1.mean().item<float>() << std::endl;
    std::cout << "Minimum Value: " << M1.min().item<float>() << std::endl;
    std::cout << "checker.M:" << std::endl;
    std::cout << "Maximum Value: " << checker.M1.max().item<float>() << std::endl;
    std::cout << "Mean Value: " << checker.M1.mean().item<float>() << std::endl;
    std::cout << "Minimum Value: " << checker.M1.min().item<float>() << std::endl;
    double M1FroError = INTELLI::UtilityFunctions::relativeFrobeniusNorm(M1, checker.M1);
    allMetrics->edit("M1FroError", (double) M1FroError);

    torch::manual_seed(123);
    // torch::Tensor M = cppAlgoPtr->amm(M1, SyyNegativeHalf, 39);
    torch::Tensor M = torch::matmul(M1, SyyNegativeHalf);
    std::cout << "M:" << std::endl;
    std::cout << "Maximum Value: " << M.max().item<float>() << std::endl;
    std::cout << "Mean Value: " << M.mean().item<float>() << std::endl;
    std::cout << "Minimum Value: " << M.min().item<float>() << std::endl;
    std::cout << "checker.M:" << std::endl;
    std::cout << "Maximum Value: " << checker.M.max().item<float>() << std::endl;
    std::cout << "Mean Value: " << checker.M.mean().item<float>() << std::endl;
    std::cout << "Minimum Value: " << checker.M.min().item<float>() << std::endl;
    double MFroError = INTELLI::UtilityFunctions::relativeFrobeniusNorm(M, checker.M);
    allMetrics->edit("MFroError", (double) MFroError);

    // torch::Tensor M = torch::matmul(torch::matmul(SxxNegativeHalf.t(), Sxy), SyyNegativeHalf);
    // 3.4 Correlation
    INTELLI_INFO("Correlation");
    torch::Tensor U, S, Vh;
    std::tie(U, S, Vh) = torch::linalg::svd(M, false, c10::nullopt);
    torch::Tensor correlation = torch::clamp(S, -1.0, 1.0);
    pef.end();
    ConfigMapPtr elseMetrics = pef.resultToConfigMap();
    elseMetrics->addPrefixToKeys("else");
    elseMetrics->cloneInto(*allMetrics);

    // Step4. End to End error
    double CorrelationError = (correlation - checker.correlation).abs().max().item<double>();
    allMetrics->edit("CorrelationError", (double) CorrelationError);

    // Save results
    std::string ruName = "CCA";
    allMetrics->toFile(ruName + ".csv");
    INTELLI_INFO("Done. here is overall result");
    std::cout << allMetrics->toString() << endl;
}

int main(int argc, char **argv) {
    string configName, outPrefix = "";
    if (argc >= 2) {
        configName += argv[1];
    } else {
        configName = "config.csv";
    }
    benchmarkCCA(configName);
    return 0;
}
