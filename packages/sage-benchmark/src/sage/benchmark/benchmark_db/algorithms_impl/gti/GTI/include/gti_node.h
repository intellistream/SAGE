// GTI node
// Created by Ruiyao Ma on 24-02-22

#pragma once
#include <iostream>
#include <vector>
#include "gti_entry.h"

class GTI_Entry;                                  // Pre-declaration
typedef std::vector<std::vector<unsigned>> Graph; // Adjacency list of graph

// Node of GTI
class GTI_Node
{
public:
    std::vector<GTI_Entry *> entries; // Entries of the node
    unsigned type;                    // 0 for internal node; 1 for leaf node
    GTI_Node *parent_node;            // Parent node
    unsigned level;                   // Level of the node in the tree

    GTI_Node() {};
    ~GTI_Node() { std::vector<GTI_Entry *>().swap(entries); }
};

// Node with distance
typedef struct NodeDis
{
    GTI_Node *node; // Node
    float dis;      // Distance
    float dis_p_q;  // Distance between parent and query

    NodeDis() = default;
    NodeDis(GTI_Node *node, float dis, float dis_p_q) : node{node}, dis{dis}, dis_p_q{dis_p_q} {}

    inline bool operator<(const NodeDis &other) const
    {
        return dis < other.dis;
    }
    inline bool operator>(const NodeDis &other) const
    {
        return dis > other.dis;
    }
} ND;
