# Base image with CUDA 11.7 and Python 3.10
FROM nvidia/cuda:11.7.1-cudnn8-devel-ubuntu22.04

# Environment variables
ENV USER=llh
ENV PASSWD=llh

# 设置环境变量，防止apt-get进行交互式操作
ENV DEBIAN_FRONTEND=noninteractive

# Install essential packages and dependencies
RUN apt-get update && apt-get install -y --fix-missing --allow-change-held-packages \
    sudo \
    build-essential \
    cmake \
    curl \
    unzip \
    liblapack-dev \
    libblas-dev \
    libboost-dev \
    rsync \
    nano \
    libcudnn8 \
    libcudnn8-dev \
    graphviz \
    openssh-server \
    gdb \
    liblog4cxx-dev \
    git \
    libcupti-dev \
    libgmp-dev \
    libmpfr-dev \
    libmpc-dev \
    clang-format \
    cuda-toolkit-11-7 \
    software-properties-common && \
    apt-get clean

# Add deadsnakes PPA, remove Python 3.10, and install Python 3.11
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get purge -y python3.10 python3.10-dev python3.10-minimal && \
    apt-get install -y python3.11 python3.11-distutils python3.11-venv python3-pip python3.11-dev && \
    apt-get autoremove -y && rm -rf /usr/bin/python3.10* /usr/lib/python3.10*

# Set Python 3.11 as the default system Python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python

# Verify Python installation
RUN python3 --version && python --version && python3.11 -m pip install --upgrade pip

# Install Python dependencies for the native Python environment
RUN python3.11 -m pip install --no-cache-dir torch matplotlib pandas==2.0.0 transformers

# Add Conda to the PATH
ENV PATH="/opt/conda/bin:$PATH"
ENV PATH="/usr/bin:$PATH"

# Set up a workspace directory, defaulted to root for debugging
WORKDIR /workspace

## Copy the Conda environment setup scripts
#COPY environment.yml auto_env_setup.sh /workspace/

# Install Conda and create llh venv
RUN curl -o ~/miniconda.sh -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    chmod +x ~/miniconda.sh && ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda init bash && \
    conda create -n llh python=3.11 -y

# Set up a new user and configure password
RUN useradd -m ${USER} && echo "${USER}:${PASSWD}" | chpasswd && usermod -G sudo ${USER}

# Configure SSH
RUN mkdir /var/run/sshd && \
    echo 'root:root' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Expose SSH port
EXPOSE 22

# Default command to run SSH server
CMD ["/usr/sbin/sshd", "-D"]

