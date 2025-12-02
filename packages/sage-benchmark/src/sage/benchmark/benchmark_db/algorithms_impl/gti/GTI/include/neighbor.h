// Neighbor
// Created by Ruiyao Ma on 24-03-05

#pragma once
#include <iostream>
#include <vector>
#include <string.h>

// Neighbor
typedef struct Neighbor
{
    int id;       // Id
    float dis;    // Distance
    unsigned nid; // Node id
    bool flag;
    unsigned oid; // Object id

    Neighbor() = default;
    Neighbor(int id, float dis, bool f) : id{id}, dis{dis}, nid(0), flag(f), oid(0) {}
    Neighbor(int id, float dis, unsigned nid, bool f, unsigned oid) : id{id}, dis{dis}, nid(nid), flag(f), oid(oid) {}

    inline bool operator<(const Neighbor &other) const
    {
        return dis < other.dis;
    }
    inline bool operator>(const Neighbor &other) const
    {
        return dis > other.dis;
    }
    inline bool operator==(const Neighbor &other) const
    {
        return id == other.id;
    }
} Neighbor;

typedef std::vector<std::vector<Neighbor>> NN; // Neighbor candidates

static inline int InsertIntoPool(Neighbor *addr, unsigned K, Neighbor nn)
{
    // find the location to insert
    int left = 0, right = K - 1;
    if (addr[left].dis > nn.dis)
    {
        memmove((char *)&addr[left + 1], &addr[left], K * sizeof(Neighbor));
        addr[left] = nn;
        return left;
    }
    if (addr[right].dis < nn.dis)
    {
        addr[K] = nn;
        return K;
    }
    while (left < right - 1)
    {
        int mid = (left + right) / 2;
        if (addr[mid].dis > nn.dis)
            right = mid;
        else
            left = mid;
    }
    // check equal ID

    while (left > 0)
    {
        if (addr[left].dis < nn.dis)
            break;
        if (addr[left].id == nn.id)
            return K + 1;
        left--;
    }
    if (addr[left].id == nn.id || addr[right].id == nn.id)
        return K + 1;
    memmove((char *)&addr[right + 1], &addr[right], (K - right) * sizeof(Neighbor));
    addr[right] = nn;
    return right;
}
