// GTI
// Created by Ruiyao Ma on 24-02-22

#pragma once
#include <iostream>
#include <algorithm>
#include <unistd.h>
#include <chrono>
#include <queue>
#include <stack>
#include <thread>
#include <omp.h>
#include "gti_entry.h"
#include "gti_node.h"
#include "objects.h"
#include "distance.h"
#include "neighbor.h"
#include "n2/hnsw.h"

bool compareEnDisp(GTI_Entry *e1, GTI_Entry *e2); // Comparison function for two entries

class GTI
{
public:
    Objects *data; // Data

    unsigned capacity_up_l; // Upper node capacity for leaf node
    unsigned capacity_up_i; // Upper node capacity for internal node
    GTI_Node *root;         // Root node
    unsigned height;        // Tree height
    double tree_size = 0;   // Size of the tree

    std::vector<GTI_Entry *> entries_sec; // Entries of second layer
    std::vector<int> map;                 // Map object id to entry id in second layer
    n2::Hnsw *index_hnsw;                 // HNSW Graph at second level
    int m;
    int max_m0;
    int ef_construction;
    int n_threads; // Number of threads to build graph

    float time_split = 0;

    GTI() {};
    ~GTI() {};

    void buildGTI(unsigned capacity_up_i, unsigned capacity_up_l, int m, Objects *data);                                        // Build GTI
    void init(unsigned capacity_up_i, unsigned capacity_up_l, int m, Objects *data);                                            // Initialize GTI
    GTI_Node *findParentNode(GTI_Node *N, GTI_Node *node);                                                                      // Find parent node
    int findParentEntry(GTI_Node *parent, GTI_Node *node);                                                                      // Find parent entry
    int findEntry(GTI_Node *node, unsigned oid);                                                                                // Find entry id in the node
    void insertAll();                                                                                                           // Insert all objects to tree
    void insert(GTI_Node *node, GTI_Entry *entry, std::vector<unsigned> &entries_in, std::vector<float> &dists, float dis_p2o); // Insert objects
    void split(GTI_Node *node, GTI_Entry *entry);                                                                               // Split node
    // M_LB_DIST1 methods to choose two new routing objects
    void promoteLb(std::vector<GTI_Entry *> &entries,
                   int *min_oid,
                   GTI_Node *parent_node,
                   GTI_Node *node,
                   std::vector<float> &dists_split);
    // Divide the entries into two nodes using generalized hyperplane
    void partitionGh(std::vector<GTI_Entry *> &entries,
                     GTI_Node *node1,
                     GTI_Node *node2,
                     GTI_Entry *entry1,
                     GTI_Entry *entry2,
                     int oid1,
                     int oid2,
                     std::vector<float> dists_split);
    void buildGraphSec(); // Build graph at second level

    void insertGTI(Objects *insert_data);     // Insert data into GTI
    void insertTree(unsigned old_data_size);  // Insert data into tree
    void insertGraph(unsigned old_data_size); // Insert data into graph

    void deleteGTI(Objects *delete_data);                                       // Delete data from GTI
    void deleteTree(Objects *delete_data, std::vector<unsigned> &delete_oids);  // Delete data from tree
    void deleteGraph(Objects *delete_data, std::vector<unsigned> &delete_oids); // Delete data from graph
    void deleteEntry(GTI_Node *node, unsigned eid);                             // Delete entry
    void findLeaf(float *query, GTI_Node *&node, unsigned &eid);                // Find the leaf of the data

    void searchTreeKnn(float *query,
                       unsigned k,
                       std::priority_queue<Neighbor, std::vector<Neighbor>, std::less<Neighbor>> &res); // k-NN search for tree
    void searchTreeRange(float *query, float r, std::vector<Neighbor> &results);                        // Range search for tree
    void search(float *query, unsigned L, unsigned K, std::vector<Neighbor> &results);                  // Search
    void searchExactKnn(float *query,
                        unsigned L,
                        unsigned K,
                        std::vector<Neighbor> &results,
                        std::priority_queue<Neighbor, std::vector<Neighbor>, std::less<Neighbor>> &res); // Exact k-NN search
    void searchTree(float *query,
                    unsigned k,
                    std::priority_queue<Neighbor, std::vector<Neighbor>, std::less<Neighbor>> &res); // Search tree using graph results

    void getTreeSize(); // Get the size of tree
};
