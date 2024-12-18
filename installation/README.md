# Docker Container Setup with Conda Environment for LLH

This Docker container is pre-configured to set up a Conda environment specifically for the `LLH` project, including `Haystack` and `CANDY` dependencies.

---

## 1. Setting up the Docker Container

To use the prebuilt Docker image from Docker Hub, simply run the provided setup script in the `installation/simplified_docker_setup` directory:

```bash
bash start.sh
```
This script will pull the image, set up the container, and mount the workspace for you.

---

## 2. Setting up the Conda Environment in the Docker Container

Once the Docker container is running, use the `auto_env_setup.sh` script inside the container to set up the `llh` Conda environment with all required dependencies.

### 2.1 Running `auto_env_setup.sh`

1. **Run the Setup Script**:
   Inside the container, run the setup script. Ensure you update the GitHub `username` and `token` for cloning the `CANDY` repository:
   ```bash
   bash auto_env_setup.sh
   ```

The environment `llh` is now ready to use. You can configure it in PyCharm or any IDE to start working on the `LLH` project.

2. **Verify the Setup**:
   After the setup is complete, activate the environment and run the test suite:
   ```bash
   conda activate llh
   cd /workspace/
   pytest -v tests/
   ```

> NOTE: Step 1 will allow you to enter the docker bash by default. Otherwise, **Access the Running Container**:
>   - Use Docker CLI:
>     ```bash
>     docker exec -it <container_name> /bin/bash
>     ```
>   - Alternatively, connect via SSH (if SSH is configured):
>     ```bash
>     ssh -p 2222 root@<CONTAINER_IP>
>     ```
---

## 3. Running LLH Interactively

### 3.1 Hugging Face Authentication

Before running the LLH system, ensure you log in to Hugging Face:
```bash
huggingface-cli login --token <your_huggingface_token>
```

### 3.2 Interactive CLI

You can interact with the LLH system using the interactive CLI:
```bash
python api/interactive_cli.py
```

---

## 4. Known Issues and Troubleshooting
