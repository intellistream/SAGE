This section is to run MADNESS evaluation on CIFAR datasets with our C++ AMM algorithms

If you just cloned LibAMM repo, remember to initialize the
**[bolt](https://github.com/dblalock/bolt)** submodule

```bash
# Assume you are at LibAMM/
git submodule init
git submodule update
```

Then follow **bolt** repo set up procedure

```bash
# Init submodule in bolt
cd benchmark/scripts/Downstream_Inference/bolt
git submodule init # Init submodule 'third_party/kmc2'
git submodule update

# Set up kmc2 submodule
cd third_party/kmc2
pip install numpy==1.23.1 cython numba zstandard seaborn # Some libraries are not for kmc2 but for Madness, just install all of them here. make sure numpy==1.23.1
python3 setup.py build_ext --build-lib=. # Compile cython to .so and save to current directory

```

Evaluate AMM

```
# Perform evaluation on AMM
cd ../../experiments
python3 -m python.amm_main # Reproduce Madness paper accuracy results
python3 -m python.amm_main -t cifar10 -c ../../config_dnn_inference.csv -m ../../metrics.csv # Interface to use intellistream AMM c++ API. After this you should see a metrics.csv, where you can check the AMM latency, AMM fro error, ending accuracy in it.
```
