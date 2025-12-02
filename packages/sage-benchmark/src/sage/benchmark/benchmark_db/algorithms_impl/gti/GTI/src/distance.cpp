#include "distance.h"

float Distance::getDis(float *a, float *b, unsigned type, unsigned dim)
{
    float dis = 0;

    switch (type)
    {
    case 0: // L2 distance
        for (unsigned i = 0; i < dim; i++)
        {
            dis += pow(a[i] - b[i], 2);
        }
        dis = pow(dis, 0.5);
        break;
    case 1: // L1 distance
        for (unsigned i = 0; i < dim; i++)
        {
            dis += abs(a[i] - b[i]);
        }
        break;
    default: // L2 distance
        for (unsigned i = 0; i < dim; i++)
        {
            dis += pow(a[i] - b[i], 2);
        }
        dis = pow(dis, 0.5);
        break;
    }

    return dis;
}

float Distance::getDisP(float *a, float *b, unsigned type, unsigned dim)
{
    float dis = 0;

    switch (type)
    {
    case 0: // L2 distance
    {
        Eigen::Map<const Eigen::VectorXf, Eigen::Unaligned> p(a, dim, 1), q(b, dim, 1);
        dis = sqrt((p - q).squaredNorm());
    }
    break;
    case 1: // L1 distance
        for (unsigned i = 0; i < dim; i++)
        {
            dis += abs(a[i] - b[i]);
        }
        break;
    default: // L2 distance
        for (unsigned i = 0; i < dim; i++)
        {
            dis += pow(a[i] - b[i], 2);
        }
        dis = pow(dis, 0.5);
        break;
    }

    return dis;
}
