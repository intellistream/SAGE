# Docker Container Setup with Conda Environment for SAGE

This Docker container is pre-configured to set up a Conda environment specifically for the `SAGE` project, including  and `CANDY` dependencies.

---


## 0. (Optional) Build a new Docker Image

To build a new docker image for our project, you may access contents in `installation/build_image`.

## 1. Setting up the Docker Container

To use the prebuilt Docker image from Docker Hub, simply run the provided setup script in the `installation/container_setup` directory:

```bash
bash start.sh
```
This script will pull the image, set up the container, and mount the workspace for you.

---

## 2. Setting up the Conda Environment in the Docker Container

Once the Docker container is running, use the `auto_env_setup.sh` script inside the container to set up the `SAGE` Conda environment with all required dependencies.

### 2.1 Running `auto_env_setup.sh`

1. **Run the Setup Script**:
   Inside the container, run the setup script. Ensure you update the GitHub `username` and `token` for cloning the `CANDY` repository:
   ```bash
   bash auto_env_setup.sh $(your_user_name) $(your_token)
   ```

The environment `SAGE` is now ready to use. You can configure it in PyCharm or any IDE to start working on the `SAGE` project.

2. **Verify the Setup**:
   After the setup is complete, activate the environment and run the test suite:
   ```bash
   conda activate SAGE
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

## 3. Running SAGE Interactively

### 3.1 Hugging Face Authentication

Before running the SAGE system, ensure you log in to Hugging Face:
```bash
huggingface-cli login --token <your_huggingface_token>
```

### 3.2 Interactive CLI

You can interact with the SAGE system using the interactive CLI:
```bash
python api/interactive_cli.py
```

---

## 4. Known Issues and Troubleshooting
