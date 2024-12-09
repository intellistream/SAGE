# Docker Container Setup with Conda Environment

This Docker container is pre-configured to set up a Conda environment specifically for the `LLH` project, including
`Haystack` dependencies.

## 1. Setting up the Docker Container

To initialize this container, simply run the provided setup script:

```bash
bash start.sh
```

This script will build and start the Docker container with all necessary configurations.

## 2. Conda Environment Setup with `auto_env_setup.sh` in Docker Container

Once the Docker container is running, you can configure the Conda environment using `auto_env_setup.sh` inside the
docker instance. This script sets up the `llh` environment with all required dependencies.

### 2.1 Steps to Run `auto_env_setup.sh`

1. **Access the Running Container**: Connect to the container’s CLI either through Docker or SSH:
    - Docker CLI:
      ```bash
      docker exec -it <container_name> /bin/bash
      ```
    - SSH (if configured):
      ```bash
      ssh -p 2222 root@<CONTAINER_IP>
      ```
2. **Run the Setup Script**: Once connected, execute the script to set up the Conda environment:
   ```bash
   bash auto_env_setup.sh
   ```

The environment `llh` will then be ready for use, and you can configure it in PyCharm or other IDEs to start working
with `llh`.

> Files Included in `/workspace`
>   - `environment.yml`: Defines the Conda environment configuration for LLH.
>     - `auto_env_setup.sh`: Automates the Conda environment setup inside the container.

### 2.2 Compile CANDY and install pycandy

Go to the CANDY project directory, and find the `installation`.

In the directory, use the following command to auto install `pycandy`:

```bash
conda deactivate # ensure in non conda env
bash candy_build.sh
conda activate llh # install pycandy in llh env
bash install_pycandy.sh
```

## 3. Verify whether pycandy is installed

To verify whether the `pycandy` is installed in any env (including `non conda` or `flow`) env, you can try running the
CANDY `apps/Python/DBClient/db_client.py`:
Make sure you are in the CANDY project directory, then run:

```bash
cd api/Python/DBClient
python db_client.py
# Try whatever command you want for verification of CRUD.
```

### Try LLH (refactored)

Make sure you are in `llh` env.

And, make sure you have huggingface token.

```bash
# Log in to Hugging Face using token from the first argument
huggingface-cli login --token #your_token
```

Then, you can interact with the system through api/interactive_cli.py

### Known issues
1. 
> In case if "ImportError: /opt/conda/envs/llh/lib/python3.11/site-packages/torch/lib/../../../.././libstdc++.so.6:
version `GLIBCXX_3.4.30' not found (required by /root/.local/lib/python3.11/site-packages/libCANDY.so)
"
```bash
conda install -c conda-forge libstdcxx-ng
```

2.
> In case if "gdb error", you may use `conda install gdb`, and then `which gdb`. use this gdb instead of the default system gdb.

