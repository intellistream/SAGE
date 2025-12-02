// GTI entry
// Created by Ruiyao Ma on 24-02-22

#pragma once
#include <iostream>
#include "gti_node.h"

#define INF_DIS 999999

class GTI_Node; // Pre-declaration

// Entry of GTI
class GTI_Entry
{
public:
    unsigned oid;    // Id of object
    float dis_p;     // Distance from parent
    float radius;    // Covering radius; INF_DIS for leaf entry
    GTI_Node *child; // Pointer to the child node; NULL for leaf entry

    GTI_Entry() {};
    ~GTI_Entry()
    {
        if (child != nullptr)
        {
            child = nullptr;
        }
    };
};
