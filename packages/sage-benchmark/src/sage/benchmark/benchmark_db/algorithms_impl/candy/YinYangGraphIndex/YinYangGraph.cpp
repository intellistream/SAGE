//
// Created by tony on 31/01/24.
//

#include <YinYangGraphIndex/YinYangGraph.h>
#include <cfloat>
#include <queue>
#include <Utils/IntelliLog.h>
using namespace CANDY;
/**
 * @brief handling the vertex
 */
void CANDY::YinYangVertex::init(torch::Tensor &ts,
                                int64_t _level,
                                int64_t maxNumOfNeighbor,
                                int64_t _containedTensors,
                                bool _isYang) {
  tensorSummary = newTensor(ts.clone());
  visno = 0;
//neighbors = std::vector<std::shared_ptr<YinYangVertex>>(maxNumOfNeighbor, nullptr);
  isYang = _isYang;
  containedTensors = _containedTensors;
  maxConnections = maxNumOfNeighbor;
  level = _level;
  containedTensors = 1;
}
void CANDY::YinYangVertex::attachTensor(torch::Tensor &ts) {
  containedTensors++;
  *tensorSummary = *tensorSummary + (ts - *tensorSummary) / containedTensors;
}

void CANDY::YinYangVertex::detachTensor(torch::Tensor &ts) {
  containedTensors--;
  *tensorSummary = *tensorSummary - (ts - *tensorSummary) / containedTensors;
}
std::string CANDY::YinYangVertex::toString(bool shortInfo) {
  auto tensor1 = tensorSummary->contiguous();
  auto A_size = tensor1.sizes();
  int64_t rows1 = A_size[0];
  int64_t cols1 = A_size[1];
  std::vector<float> matrix1(tensor1.data_ptr<float>(), tensor1.data_ptr<float>() + rows1 * cols1);
  std::string ru;
  ru += "(l=" + std::to_string(level);
  if (isYang) {
    ru += "yang,";
  } else {
    ru += "yin,";
  }
  ru += std::to_string(cols1) + "D:<";
  size_t showEle = cols1;
  if (shortInfo && showEle > 2) {
    showEle = 2;
  }
  for (size_t i = 0; i < showEle; i++) {
    ru += std::to_string(matrix1[i]) + ",";
  }
  if (shortInfo) {
    ru += "...";
  }
  ru += ">)";
  return ru;
}
CANDY::YinYangVertexPtr CANDY::YinYangVertex::greedySearchForNearestVertex(YinYangVertexPtr src,
                                                                           YinYangVertexPtr entryPoint,
                                                                           floatDistanceFunction_t df) {

  return greedySearchForNearestVertex(*src->tensorSummary, entryPoint, df);
}

CANDY::YinYangVertexPtr CANDY::YinYangVertex::greedySearchForNearestVertex(torch::Tensor &src,
                                                                           YinYangVertexPtr entryPoint,
                                                                           floatDistanceFunction_t df) {
  //auto ru = greedySearchForKNearestVertex(src,entryPoint,1, false,false,df);
  //return ru[0];
  float minDistance = df(src, (*entryPoint->tensorSummary));
  float minDistanceOfNeighbors = minDistance;
  YinYangVertexPtr currentVertex = entryPoint;
  YinYangVertexPtr neighborWithMinDistance = nullptr;
  size_t maxTry = 65536;
  size_t tryCnt = 0;
  YinYangVertexMap visitedMap;
  while (currentVertex != nullptr && tryCnt < maxTry) {
    // size_t neighborSize=currentVertex->neighborMap.size();
    if (currentVertex->neighborMap.size() == 0) {
      return currentVertex;
    }
    /**
     * @brief 1. scan the distance of neighbors
     */
    for (auto &iter : currentVertex->neighborMap) {
      auto visitingVertex = iter.second;
      if (visitingVertex == nullptr) {
        continue;
      }
      if (!visitedMap.exist(visitingVertex)) {
        float distance = df((*visitingVertex->tensorSummary), src);
        if (distance < minDistanceOfNeighbors) {
          minDistanceOfNeighbors = distance;
          neighborWithMinDistance = visitingVertex;
        }
        tryCnt++;
        visitedMap.edit(visitingVertex);
      }

    }
    /**
    * @brief 2. if this one is optimal, return
    */
    if (minDistanceOfNeighbors >= minDistance) {
      return currentVertex;
    }
      /**
       * @brief switch into the new optimal ones
       */
    else {
      minDistance = minDistanceOfNeighbors;
      currentVertex = neighborWithMinDistance;
    }
  }
  return currentVertex;
}
struct VertexComparison {
  bool operator()(const std::pair<double, YinYangVertexPtr> &a, const std::pair<double, YinYangVertexPtr> &b) const {
    // Min heap based on distance
    return a.first > b.first;
  }
};
/*std::vector<YinYangVertexPtr> CANDY::YinYangVertex::greedySearchForKNearestVertex(CANDY::YinYangVertexPtr src,
                                                                                  CANDY::YinYangVertexPtr entryPoint,
                                                                                  int64_t k,
                                                                                  bool ignoreYin,
                                                                                  bool forceTheSameLevel,
                                                                                  CANDY::floatDistanceFunction_t df) {
  auto queryTensor=*src->tensorSummary;
  std::vector<YinYangVertexPtr> result ((size_t)k, nullptr);

  YinYangVertexPtr startVertex=CANDY::YinYangVertex::greedySearchForNearestVertex(src,entryPoint,df);
  size_t sizeToBeFilled=k-1;
  if(ignoreYin&&(startVertex->isYang== false)) {
    sizeToBeFilled=k;
  }
  else {
    result[0]=startVertex;
  }
  size_t i=k-sizeToBeFilled;

  std::priority_queue<std::pair<double, YinYangVertexPtr>,std::vector<std::pair<double, YinYangVertexPtr>>,VertexComparison> pq; // Min heap

  double startDistance = df(queryTensor, *(startVertex->tensorSummary));
  pq.emplace(startDistance, startVertex);

  while (!pq.empty() && i < k) {
    // Get the vertex with the maximum similarity
    YinYangVertexPtr currentVertex = pq.top().second;
    pq.pop();
    result[i]=currentVertex;
    i++;
    for (const auto& iter : currentVertex->neighborMap) {
      auto neighbor=iter.second;
      double distance = df(queryTensor, (*neighbor->tensorSummary));
      pq.emplace(distance, neighbor);
    }
  }
  return result;
}*/
std::vector<YinYangVertexPtr> CANDY::YinYangVertex::greedySearchForKNearestVertex(torch::Tensor &src,
                                                                                  CANDY::YinYangVertexPtr entryPoint,
                                                                                  int64_t k,
                                                                                  bool ignoreYin,
                                                                                  bool forceTheSameLevel,
                                                                                  CANDY::floatDistanceFunction_t df) {
  YinYangVertexMap visitedMap;
  std::priority_queue<std::pair<float, YinYangVertexPtr>,
                      std::vector<std::pair<float, YinYangVertexPtr>>,
                      VertexComparison> candidateMinHeap; // Min heap of candidate
  std::priority_queue<std::pair<float, YinYangVertexPtr>> resultMaxHeap; // Max heap of result
  std::vector<YinYangVertexPtr> result((size_t) k, nullptr);
  visitedMap.edit(entryPoint);
  float tempDistance = df(*entryPoint->tensorSummary, src);
  candidateMinHeap.emplace(tempDistance, entryPoint);
  resultMaxHeap.emplace(tempDistance, entryPoint);
  YinYangVertexPtr c = nullptr, f = nullptr;
  while (!candidateMinHeap.empty()) {
    c = candidateMinHeap.top().second;
    candidateMinHeap.pop();
    f = resultMaxHeap.top().second;
    //resultMaxHeap.pop();
    float distanceCq = df(*c->tensorSummary, src);
    float distanceFq = df(*f->tensorSummary, src);
    if (distanceCq > distanceFq) {
      //INTELLI_INFO("Min in candidate is"+c->toString()+"max in temp result is"+f->toString());
      break; // all elements in W are evaluated
    }
    for (const auto &iter : c->neighborMap) {
      auto e = iter.second;
      if (visitedMap.exist(e) == false) {
        visitedMap.edit(e);
        f = resultMaxHeap.top().second;
        //resultMaxHeap.pop();
        float distanceEq = df(*f->tensorSummary, src);
        distanceFq = df(*f->tensorSummary, src);
        if (distanceEq < distanceFq || resultMaxHeap.size() < (size_t) k) {
          candidateMinHeap.emplace(distanceEq, e);
          resultMaxHeap.emplace(distanceEq, e);
          if (resultMaxHeap.size() > (size_t) k) {
            resultMaxHeap.pop();
          }
        }
      }
    }
  }
  size_t i = 0;
  while (!resultMaxHeap.empty()) {
    auto rui = resultMaxHeap.top().second;
    resultMaxHeap.pop();
    result[i] = rui;
    i++;
  }
  return result;
}
std::vector<YinYangVertexPtr> CANDY::YinYangVertex::greedySearchForKNearestVertex(YinYangVertexPtr src,
                                                                                  YinYangVertexPtr entryPoint,
                                                                                  int64_t k,
                                                                                  bool ignoreYin,
                                                                                  bool forceTheSameLevel,
                                                                                  floatDistanceFunction_t df) {
  return greedySearchForKNearestVertex(*src->tensorSummary, entryPoint, k, ignoreYin, forceTheSameLevel, df);
}
torch::Tensor CANDY::YinYangVertex::greedySearchForKNearestTensor(torch::Tensor &src,
                                                                  CANDY::YinYangVertexPtr entryPoint,
                                                                  int64_t k,
                                                                  CANDY::floatDistanceFunction_t df) {
  torch::Tensor ru = torch::zeros({(int64_t) k, src.size(1)});
  //bool ignoreYin=true;
  int64_t lastNNZ = -1;
  auto queryTensor = src;
  YinYangVertexMap visitedMap;
  //std::vector<YinYangVertexPtr> result ((size_t)k, nullptr);
  YinYangVertexPtr startVertex = CANDY::YinYangVertex::greedySearchForNearestVertex(src, entryPoint, df);
  visitedMap.edit(startVertex);
  //INTELLI_INFO(startVertex->toString());
  //exit(-1);
  size_t i = 0;
  //std::priority_queue<std::pair<double, YinYangVertexPtr>> pq; // Max heap
  std::priority_queue<std::pair<double, YinYangVertexPtr>,
                      std::vector<std::pair<double, YinYangVertexPtr>>,
                      VertexComparison> pq; // Min heap
  // Calculate distance to the start vertex
  double startDistance = df(queryTensor, *startVertex->tensorSummary);
  pq.emplace(startDistance, startVertex);

  while (!pq.empty() && i < (size_t) k) {
    // Get the vertex with the maximum similarity
    YinYangVertexPtr currentVertex = pq.top().second;
    // while(!pq.empty()) {
    auto sortedVertex = pq.top().second;
    pq.pop();
    /*if(currentVertex->isYang) {
      INTELLI_INFO(currentVertex->toString());
      INTELLI_INFO(std::to_string(visitedMap.exist(currentVertex)));
    }*/
    //INTELLI_INFO(currentVertex->toString());
    if (sortedVertex->isYang) {
      i++;
      // INTELLI_INFO("Append" + sortedVertex->toString());
      INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, sortedVertex->tensorSummary.get(), &lastNNZ);
      // break;
    } else {
      float minDistanceOfYang = FLT_MAX;
      YinYangVertexPtr closestYang = nullptr;
      for (const auto &iter : sortedVertex->neighborMap) {
        auto neighbor = iter.second;
        if (neighbor->isYang) {
          //INTELLI_INFO("This yin at min"+sortedVertex->toString()+ ",get yang neighbor"+neighbor->toString());
          float tempDistance = df(*neighbor->tensorSummary, src);
          if (tempDistance < minDistanceOfYang) {
            minDistanceOfYang = tempDistance;
            closestYang = neighbor;
          }
        }
      }
      if (closestYang != nullptr) {
        if (visitedMap.exist(closestYang) == false) {
          double distance = minDistanceOfYang;
          pq.emplace(distance, closestYang);
          visitedMap.edit(closestYang);
        }
      }
      /* while (!pqYin.empty()) {
         auto sortedVertexYin= pqYin.top().second;
         pqYin.pop();
         if(sortedVertexYin->isYang) {
           i++;
           INTELLI_INFO("Append"+sortedVertexYin->toString());
           INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru,sortedVertexYin->tensorSummary.get(),&lastNNZ);
           break;
         }
       }*/
    }
    //}
    // Add the current vertex to the result
    // Explore neighbors and add to the priority queue
    for (const auto &iter : currentVertex->neighborMap) {
      auto neighbor = iter.second;
      //INTELLI_INFO(neighbor->toString());
      if (visitedMap.exist(neighbor) == false) {
        double distance = df(queryTensor, *neighbor->tensorSummary);
        pq.emplace(distance, neighbor);
        visitedMap.edit(neighbor);
      }
      // INTELLI_INFO("neighbor of "+currentVertex->toString()+":"+neighbor->toString());


      /*if(neighbor->isYang) {
        i++;
        INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru,neighbor->tensorSummary.get(),&lastNNZ);
      }*/
    }
  }
  return ru;
}
bool CANDY::YinYangVertex::tryToConnect(CANDY::YinYangVertexPtr a,
                                        CANDY::YinYangVertexPtr b,
                                        std::vector<YinYangVertexMap> &vertexMapGe1Vec,
                                        CANDY::floatDistanceFunction_t df) {
  if (a == nullptr || b == nullptr) {
    return false;
  }
  if (a->connectedNeighbors >= a->maxConnections) {
    INTELLI_WARNING(a->toString() + "is full");
    return false;
  }
  /**
   * @brief 1. if b is not fully connected, than just connect
   */
  if (b->connectedNeighbors < b->maxConnections) {
    // INTELLI_WARNING(a->toString()+" CONNECT WITH "+b->toString()+", directly");
    b->neighborMap[a] = a;
    a->neighborMap[b] = b;
    a->connectedNeighbors++;
    b->connectedNeighbors++;
    if ((b->isYang == false) && (b->level == a->level + 1) && (a->upperLayerVertex == nullptr)) {
      b->attachTensor(*a->tensorSummary);
      a->upperLayerVertex = b;
    }
    return true;
  }
  /**
   * @brief 3. try to create an upper layer of b
   */
  /*if(b->upperLayerVertex== nullptr) {
    int64_t newMaxCon;
    if(b->isYang) {
      newMaxCon=b->maxConnections*2;
    }
    else {
      newMaxCon=b->maxConnections;
    }
    torch::Tensor newSummary=b->tensorSummary->clone();
    auto newConVertex=newYinYangVertex();
    newConVertex->init(newSummary,b->level+1,newMaxCon,1, false);
    //INTELLI_INFO("create "+newConVertex->toString(true)+"due to"+a->toString(true));
    //tryToConnect(b,newConVertex,vertexMapGe1Vec,df);
    int64_t numberOfTensors = b->neighborMap.size();
    int64_t summedTensors=1;
    YinYangVertexPtr furthestAtTheSameLayer=nullptr;
    float maxDistance=0;
    for(auto  &iter:b->neighborMap) {
      YinYangVertexPtr vp=iter.second;
      if(vp->level==b->level) {
        summedTensors++;
        vp->upperLayerVertex=newConVertex;
        float tempDis=df(*b->tensorSummary,*vp->tensorSummary);
        if(tempDis>maxDistance) {
          maxDistance=tempDis;
          furthestAtTheSameLayer=vp;
        }
       if(tryToConnect(newConVertex,vp,vertexMapGe1Vec,df)) {
          newConVertex->attachTensor(*vp->tensorSummary);
        }
      }
      if(summedTensors>=numberOfTensors) {
        break;
      }
    }
    if(furthestAtTheSameLayer!= nullptr) {
      //INTELLI_INFO("The furthest vertex of "+b->toString(true)+" is"+furthestAtTheSameLayer->toString(true));
      //INTELLI_INFO(b->toString(true)+"has "+std::to_string(b->connectedNeighbors)+"/"+std::to_string(b->maxConnections));
      b->neighborMap.erase(furthestAtTheSameLayer);
      b->connectedNeighbors--;
     // //INTELLI_INFO(b->toString(true)+"has "+std::to_string(b->connectedNeighbors)+"/"+std::to_string(b->maxConnections));
      furthestAtTheSameLayer->neighborMap.erase(b);
      furthestAtTheSameLayer->connectedNeighbors--;
      tryToConnect(b,newConVertex,vertexMapGe1Vec,df);
      b->upperLayerVertex=newConVertex;
    }
    else {
      //INTELLI_INFO("I can not find the furthest vertex of "+b->toString(true));
    }*/
  /**
   * @brief 2.1 create upper layer links
  */
  /* if(vertexMapGe1Vec.size()>(size_t)newConVertex->level-1) {
     auto &layerMap=vertexMapGe1Vec[newConVertex->level-1].vertexMap;
     auto startPoint=layerMap.begin()->second;
     int64_t k= newMaxCon/2-1;
     if(k>0) {
       auto closestInNewConVertexLv=greedySearchForKNearestVertex(newConVertex,startPoint,k, false, true,df);
       for(auto &iter:closestInNewConVertexLv) {
         tryToConnect(newConVertex,iter,vertexMapGe1Vec,df);
       }
     }
     vertexMapGe1Vec[newConVertex->level-1].edit(newConVertex);

   }
   else {
     INTELLI_INFO("Increase global level to "+std::to_string(newConVertex->level)+"due to"+a->toString());
     YinYangVertexMap m1;
     m1.edit(newConVertex);
     vertexMapGe1Vec.push_back(std::move(m1));
   }
   //INTELLI_INFO("create new upper tier vertex"+newConVertex->toString()+", linked "+std::to_string(newConVertex->neighborMap.size())+"neighbors");
 }*/
  /**
   * @brief 3. shrink connection of b
   */
  for (auto &iter : b->neighborMap) {
    auto bn = iter.second;
    if (df(*bn->tensorSummary, *b->tensorSummary) > df(*a->tensorSummary, *b->tensorSummary)) {
      bn->neighborMap.erase(b);
      bn->connectedNeighbors--;
      b->neighborMap.erase(bn);
      b->neighborMap[a] = a;
      a->neighborMap[b] = b;
      a->connectedNeighbors++;
      return true;
    }
  }
  return false;
}
CANDY::YinYangVertexPtr CANDY::YinYangVertexMap::nearestVertexWithinMap(CANDY::YinYangVertexPtr src,
                                                                        CANDY::YinYangVertexMap &vmap,
                                                                        floatDistanceFunction_t df) {
  float minDistance = FLT_MAX;
  YinYangVertexPtr ru = nullptr;
  for (auto &iter : vmap.vertexMap) {
    YinYangVertexPtr vp = iter.second;
    float distance = df(*vp->tensorSummary, *src->tensorSummary);
    if (distance < minDistance) {
      minDistance = distance;
      ru = vp;
    }
  }
  return ru;
}

static std::vector<size_t> argsortFloat(const std::vector<float> &vec) {
  // Initialize an index vector with the same size as the input vector
  std::vector<size_t> indices(vec.size());
  std::iota(indices.begin(), indices.end(), 0);  // Fill with 0, 1, 2, ...

  // Sort indices based on the values in the vector
  std::sort(indices.begin(), indices.end(), [&vec](size_t i, size_t j) {
    return vec[i] < vec[j];
  });

  return indices;
}

std::vector<CANDY::YinYangVertexPtr> CANDY::YinYangVertexMap::nearestKVertexWithinMap(CANDY::YinYangVertexPtr src,
                                                                                      CANDY::YinYangVertexMap &vmap,
                                                                                      int64_t k,
                                                                                      CANDY::floatDistanceFunction_t df) {
  size_t ruLen = (vmap.vertexMap.size() > (size_t) k) ? k : vmap.vertexMap.size();
  std::vector<CANDY::YinYangVertexPtr> ruTemp(vmap.vertexMap.size(), nullptr);
  std::vector<CANDY::YinYangVertexPtr> ru(ruLen, nullptr);
  std::vector<float> distanceVec(vmap.vertexMap.size(), FLT_MAX);
  size_t i = 0;
  /**
   * @brief 1. traverse
   */
  for (auto &iter : vmap.vertexMap) {
    YinYangVertexPtr vp = iter.second;
    float distance = df(*vp->tensorSummary, *src->tensorSummary);
    distanceVec[i] = distance;
    if (i < ruLen) {
      ruTemp[i] = vp;
    }
    i++;
  }
  if (ruLen == vmap.vertexMap.size()) {
    return ruTemp;
  }
  /**
   * @brief 2. sort
   */
  auto sortedIdx = argsortFloat(distanceVec);
  for (i = 0; i < ruLen; i++) {
    ru[i] = ruTemp[sortedIdx[i]];
  }
  return ru;

}
static std::string yy_encodeToString(std::vector<uint8_t> &encode) {
  std::string str;
  for (size_t i = 0; i < encode.size(); i++) {
    str += std::to_string((int) encode[i]);
    str += "-";
  }
  return str;
}
/**
* @brief handling the listcell
*/
void CANDY::YinYangGraph_ListCell::insertTensor(torch::Tensor &t,
                                                int64_t maxNeighborCnt,
                                                YinYangVertexMap &yin0Map,
                                                std::vector<YinYangVertexMap> &vertexMapGe1Vec) {
  /**
   * @brief 1. a new vertex if vertex==nullptr, create a yin vertex
   */
  auto dataPoint = newYinYangVertex();
  dataPoint->init(t, 0, maxNeighborCnt, 1, true);
  //INTELLI_INFO("Create data vertex "+dataPoint->toString(true));
  if (vertex == nullptr) {
    vertex = newYinYangVertex();
    vertex->init(t, 0, 2 * maxNeighborCnt, 1, false);
    CANDY::YinYangVertex::tryToConnect(dataPoint, vertex, vertexMapGe1Vec);

    //INTELLI_INFO("Create start vertex for"+ yy_encodeToString(encode)+":"+vertex->toString(true));
    /**
     * @broef to connect it with other level 0 yin vertex
     */
    if (yin0Map.vertexMap.size() == 0) {
      yin0Map.edit(vertex);
    } else {
      int64_t nnk = (yin0Map.vertexMap.size() > (size_t) maxNeighborCnt) ? maxNeighborCnt : yin0Map.vertexMap.size();
      auto yin0Neighbors = CANDY::YinYangVertexMap::nearestKVertexWithinMap(vertex, yin0Map, nnk);
      for (auto &iter : yin0Neighbors) {
        CANDY::YinYangVertex::tryToConnect(vertex, iter, vertexMapGe1Vec);
      }
      yin0Map.edit(vertex);
    }
  } else {
    /**
     * @brief to create a new yang vertex and connect it with vertex member
   */
    auto closestInNewConVertexLv =
        CANDY::YinYangVertex::greedySearchForKNearestVertex(dataPoint, vertex, maxNeighborCnt / 2, false, false);
    for (auto &iter : closestInNewConVertexLv) {
      CANDY::YinYangVertex::tryToConnect(dataPoint, iter, vertexMapGe1Vec);
    }
    if (dataPoint->neighborMap.count(vertex) > 0) {
      vertex->attachTensor(t);
    }
  }

}
YinYangVertexPtr CANDY::YinYangGraph_ListBucket::getVertexWithEncode(std::vector<uint8_t> &encode) {
  for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
    if ((*ele)->getEncode() == encode) { return (*ele)->getVertex(); }
  }
  if (cellPtrs.size() > 0) {
    return (*cellPtrs.begin())->getVertex();
  }
  return nullptr;
}
void CANDY::YinYangGraph_ListBucket::insertTensorWithEncode(torch::Tensor &t,
                                                            int64_t maxNeighborCnt,
                                                            std::vector<uint8_t> &encode,
                                                            CANDY::YinYangVertexMap &yin0Map,
                                                            std::vector<YinYangVertexMap> &vertexMapGe1Vec,
                                                            bool isConcurrent) {
  if (isConcurrent) {
    lock();
    tensors++;
    unlock();
    for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
      auto celPtr = *ele;
      if (celPtr->getEncode() == encode) {
        celPtr->lock();
        celPtr->insertTensor(t, maxNeighborCnt, yin0Map, vertexMapGe1Vec);
        celPtr->unlock();
        return;
      }
    }
    YinYangGraph_ListCellPtr cellNew = newYinYangGraph_ListCell();
    cellNew->setEncode(encode);
    cellNew->insertTensor(t, maxNeighborCnt, yin0Map, vertexMapGe1Vec);
    cellPtrs.push_back(cellNew);
    return;
  } else {
    tensors++;
    for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
      auto celPtr = *ele;
      if (celPtr->getEncode() == encode) {
        celPtr->insertTensor(t, maxNeighborCnt, yin0Map, vertexMapGe1Vec);
        return;
      }
    }
    YinYangGraph_ListCellPtr cellNew = newYinYangGraph_ListCell();
    cellNew->setEncode(encode);
    cellNew->insertTensor(t, maxNeighborCnt, yin0Map, vertexMapGe1Vec);
    cellPtrs.push_back(cellNew);
    return;
  }
}
void CANDY::YinYangGraph::init(size_t bkts, size_t _encodeLen, int64_t _maxCon) {
  bucketPtrs = std::vector<YinYangGraph_ListBucketPtr>(bkts);
  for (size_t i = 0; i < bkts; i++) {
    bucketPtrs[i] = newYinYangGraph_ListBucket();
  }
  encodeLen = _encodeLen;
  maxConnections = _maxCon;
}
void CANDY::YinYangGraph::insertTensorWithEncode(torch::Tensor &t,
                                                 std::vector<uint8_t> &encode,
                                                 uint64_t bktIdx,
                                                 bool isConcurrent) {
  size_t bkts = bucketPtrs.size();
  if (bktIdx >= bkts) { return; }
  bucketPtrs[bktIdx]->insertTensorWithEncode(t, maxConnections, encode, yin0Map, vertexMapGe1Vec, isConcurrent);
}
torch::Tensor CANDY::YinYangGraph::getMinimumNumOfTensors(torch::Tensor &t,
                                                          std::vector<uint8_t> &encode,
                                                          uint64_t bktIdx,
                                                          int64_t minimumNum) {
  YinYangVertexPtr startPoint = nullptr;
  YinYangVertexPtr startPointIvf = nullptr;
  /**
   * @brief 1. set to the top tier like HNSW
   */
  if (vertexMapGe1Vec.size() > 0) {
    startPoint = vertexMapGe1Vec[vertexMapGe1Vec.size() - 1].vertexMap.begin()->second;
  }
  //size_t testTensors = 0;
  size_t bkts = bucketPtrs.size();
  if (bktIdx < bkts) {
    startPointIvf = bucketPtrs[bktIdx]->getVertexWithEncode(encode);
  }
  /**
   * @brief 2. set to the related cell
   */
  if (startPointIvf != nullptr) {
    startPoint = startPointIvf;
  }
  if (startPoint == nullptr) {
    startPoint = yin0Map.vertexMap.begin()->first;
    //exit(-1);
  }
  //startPoint=yin0Map.vertexMap.begin()->first;
  //INTELLI_INFO("The nearest vertex is"+startPoint->toString()+",has "+std::to_string(startPoint->connectedNeighbors)+" neighbors");
  return CANDY::YinYangVertex::greedySearchForKNearestTensor(t, startPoint, minimumNum);
}
