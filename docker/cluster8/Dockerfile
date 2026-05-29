ARG SAGE_BASE_IMAGE=sage-cluster-runtime-base:current
FROM ${SAGE_BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
ARG SAGE_RUNTIME_ENV_NAME=sagellm
ARG SAGE_RUNTIME_ENV_FILE=generated/sagellm-linux-64.lock.yml
ARG SAGE_RUNTIME_PIP_FILE=generated/sagellm-linux-64.lock.pip.txt

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PATH=/root/miniconda3/bin:/root/miniconda3/envs/${SAGE_RUNTIME_ENV_NAME}/bin:${PATH}

RUN if ! command -v sshd >/dev/null 2>&1 \
    || ! command -v rsync >/dev/null 2>&1 \
    || ! command -v git >/dev/null 2>&1; then \
        apt-get update && apt-get install -y --no-install-recommends \
            bash \
            build-essential \
            ca-certificates \
            curl \
            git \
            iproute2 \
            iputils-ping \
            netcat-traditional \
            openssh-client \
            openssh-server \
            procps \
                rsync \
            && rm -rf /var/lib/apt/lists/*; \
    fi

RUN mkdir -p \
    /opt/sage-cluster/bin \
    /shared/cache \
    /shared/datasets \
    /shared/logs \
    /shared/results \
    /var/run/sshd \
    /workspace

COPY scripts/container-entrypoint.sh /opt/sage-cluster/bin/container-entrypoint.sh

RUN chmod 0755 /opt/sage-cluster/bin/container-entrypoint.sh \
    && if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then ssh-keygen -A; fi

WORKDIR /workspace/SAGE

ENTRYPOINT ["/opt/sage-cluster/bin/container-entrypoint.sh"]
