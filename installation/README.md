# Docker Container Setup with Conda Environment for LLH

This Docker container is pre-configured to set up a Conda environment specifically for the `LLH` project, including `Haystack` and `CANDY` dependencies.

---

## 1. Setting up the Docker Container

### Option 1: Using Prebuilt Docker Image
To use the prebuilt Docker image from Docker Hub, simply run the provided setup script in the `installation/simplified_docker_setup` directory:

```bash
bash start.sh
```

This script will pull the image, set up the container, and mount the workspace for you.

### Option 2: Build the Docker Image Locally
If you prefer to build the Docker image from scratch, you can also use the same `start.sh` script:

```bash
bash start.sh
```

The script will:
- Build the Docker image from your local `Dockerfile`.
- Set up the container with all necessary configurations.

---

## 2. Setting up the Conda Environment in the Docker Container

Once the Docker container is running, use the `auto_env_setup.sh` script inside the container to set up the `llh` Conda environment with all required dependencies.

### 2.1 Running `auto_env_setup.sh`

1. **Access the Running Container**:
   - Use Docker CLI:
     ```bash
     docker exec -it <container_name> /bin/bash
     ```
   - Alternatively, connect via SSH (if SSH is configured):
     ```bash
     ssh -p 2222 root@<CONTAINER_IP>
     ```

2. **Run the Setup Script**:
   Inside the container, run the setup script. Ensure you update the GitHub `username` and `token` for cloning the `CANDY` repository:
   ```bash
   bash auto_env_setup.sh
   ```

3. **Verify the Environment**:
   After the setup is complete, activate the environment and run the test suite:
   ```bash
   conda activate llh
   cd /workspace/
   pytest -v tests/
   ```

The environment `llh` is now ready to use. You can configure it in PyCharm or any IDE to start working on the `LLH` project.

---

## 3. CANDY and PyCANDY Setup

### 3.1 Compile CANDY and Install PyCANDY

1. **Clone the CANDY Repository**:
   ```bash
   cd deps
   git clone https://github.com/intellistream/CANDY.git
   ```

2. **Build and Install PyCANDY**:
   - Ensure you are outside the Conda environment:
     ```bash
     conda deactivate
     ```
   - Run the build script:
     ```bash
     bash candy_build.sh
     ```
   - Activate the `llh` Conda environment and install `pycandy`:
     ```bash
     conda activate llh
     bash install_pycandy.sh
     ```

---

## 4. Verifying PyCANDY Installation

To verify that `pycandy` is installed correctly, run the CANDY `DBClient` application:

1. Navigate to the `DBClient` directory:
   ```bash
   cd deps/CANDY/api/Python/DBClient
   ```

2. Run the client script:
   ```bash
   python db_client.py
   ```
   Test the script with your desired CRUD operations to confirm `pycandy` is working properly.

---

## 5. Running LLH Interactively

### 5.1 Hugging Face Authentication

Before running the LLH system, ensure you log in to Hugging Face:
```bash
huggingface-cli login --token <your_huggingface_token>
```

### 5.2 Interactive CLI

You can interact with the LLH system using the interactive CLI:
```bash
python api/interactive_cli.py
```

---

## 6. Known Issues and Troubleshooting

### Issue 1: GLIBCXX Version Mismatch
If you encounter the following error:
```plaintext
ImportError: /opt/conda/envs/llh/lib/python3.11/site-packages/torch/lib/../../../.././libstdc++.so.6: version `GLIBCXX_3.4.30' not found
```
Fix it by installing an updated `libstdcxx-ng` package:
```bash
conda install -c conda-forge libstdcxx-ng
```

### Issue 2: GDB Errors
If you experience GDB-related issues, install GDB via Conda and use the installed version instead of the system default:
```bash
conda install gdb
which gdb
```
Use the Conda-installed GDB path for debugging.
