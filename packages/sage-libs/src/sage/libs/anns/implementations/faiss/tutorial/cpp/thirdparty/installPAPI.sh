#!/bin/bash
sh ./makeClean.sh
cp -r papi_7_0_1 papi_temp
cd papi_temp/src
./configure --prefix=$PWD/../../papi_build 
make -j24
make install
cd ../..
rm -rf papi_temp
