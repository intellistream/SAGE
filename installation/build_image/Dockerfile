# Base image
FROM nvidia/cuda:12.5.1-cudnn-devel-ubuntu22.04

# Environment variables
ENV USER=sage
ENV PASSWD=sage

# 设置环境变量，防止apt-get进行交互式操作
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/bin:$PATH"

# Set LDFLAGS globally for sage_runtime and shell environments
RUN echo 'export LDFLAGS="-L/usr/local/cuda-12.5/lib64"' >> /etc/profile && \
    echo 'export LDFLAGS="-L/usr/local/cuda-12.5/lib64"' >> /root/.bashrc

# Install essential packages and dependencies
RUN apt-get update && apt-get install -y --fix-missing --allow-change-held-packages \
    sudo \
    build-essential \
    curl \
    unzip \
    liblapack-dev \
    libblas-dev \
    libboost-dev \
    rsync \
    nano \
    vim \
    graphviz \
    openssh-server \
    liblog4cxx-dev \
    git \
    libcupti-dev \
    libgmp-dev \
    libmpfr-dev \
    libmpc-dev \
    clang-format \
    software-properties-common \
    texinfo \
    zlib1g-dev && \
    apt-get clean

# Install latest CMake
RUN curl -o cmake.sh -L https://github.com/Kitware/CMake/releases/download/v3.27.7/cmake-3.27.7-linux-x86_64.sh && \ 
    chmod +x cmake.sh && \
    ./cmake.sh --skip-license --prefix=/usr/local && \
    rm cmake.sh && \
    cmake --version

# Add deadsnakes PPA, remove Python 3.10, and install Python 3.11
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get purge -y python3.10 python3.10-dev python3.10-minimal && \
    apt-get install -y python3.11 python3.11-distutils python3.11-venv python3-pip python3.11-dev libpython3.11-dev && \
    apt-get autoremove -y && rm -rf /usr/bin/python3.10* /usr/sage_common_funs/python3.10*

# Set Python 3.11 as the default system Python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python

# Remove default GDB
RUN apt-get purge -y gdb && apt-get autoremove -y

# Compile GDB from source with Python 3.11 support
RUN curl -o gdb.tar.gz -L http://ftp.gnu.org/gnu/gdb/gdb-13.2.tar.gz && \
    tar -xzf gdb.tar.gz && \
    cd gdb-13.2 && \
    ./configure --with-python=/usr/bin/python3.11 && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf gdb-13.2 gdb.tar.gz && \
    gdb --version

# Verify Python installation
RUN python3 --version && python --version && python3.11 -m pip install --upgrade pip

# Install Python dependencies for the native Python environment
RUN python3 -m pip install --no-cache-dir torch matplotlib pandas==2.0.0 transformers

# Add Conda to the PATH
ENV PATH="/opt/conda/bin:$PATH"
ENV PATH="/usr/bin:$PATH"

# Set up a workspace directory, defaulted to root for debugging # DO NOT CHANGE THIS!
WORKDIR /workspace

# Install Conda and create sage venv
RUN curl -o ~/miniconda.sh -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    chmod +x ~/miniconda.sh && ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda init bash && \
    conda config --set auto_activate_base false

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
# CMD ["/workspace/installation/auto_env_setup.sh", "-D"]

