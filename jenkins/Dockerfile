FROM jenkins/jenkins:lts-jdk17

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    jq \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python tools globally for pipeline use
RUN pip3 install --no-cache-dir --break-system-packages \
    semgrep \
    detect-secrets \
    pip-licenses \
    pytest \
    pytest-cov \
    pytest-asyncio \
    fastapi \
    httpx \
    uvicorn \
    pydantic

# Install Jenkins plugins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Create reports directory
RUN mkdir -p /var/jenkins_home/reports

USER jenkins

ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
