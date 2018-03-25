# Using PyPy 3 as the Python interpreter.
FROM pypy:latest

# Setting ENV variables from ARGs.
ARG API_MASK
ARG API_PORT=5000
ARG DEPLOY_ARGS
ARG MONGODB_IP
ARG MONGODB_PORT=27017
ARG USER=1000

ENV API_MASK=$API_MASK
ENV API_PORT=$API_PORT
ENV DEPLOY_ARGS=$DEPLOY_ARGS
ENV MONGODB_IP=$MONGODB_IP
ENV MONGODB_PORT=$MONGODB_PORT

# Adding user and group: avoiding running containers as root
RUN useradd -r -N -u $USER climatechange || true

# Getting the last package updates.
RUN apt-get update
RUN pip install --upgrade pip setuptools
RUN pip3 install --upgrade pip setuptools

# Reading configuration from 'docker_config.config' instead of 'dev_config.config'
ENV DOCKER_MODE=true

# Adding project code to the image.
ADD . /ClimateChangeApp/code

# Installing all project dependencies.
RUN pip3 install -r /ClimateChangeApp/code/api/doc/requirements.txt

# Setting working directory.
WORKDIR /ClimateChangeApp/code/api

# Adding project root folder to PYTHONPATH, to avoid raising ImportError.
ENV PYTHONPATH /ClimateChangeApp:/ClimateChangeApp/code

# API log files will be generated under this directory.
VOLUME /ClimateChangeApp/log/api

# Adding HEALTHCHECK
RUN chmod +x /ClimateChangeApp/code/api/docker-healthcheck
HEALTHCHECK CMD ["/ClimateChangeApp/code/api/docker-healthcheck"]

# Deploy script which performs necessary operations before running the Subsystem for the first time.
RUN ["pypy3", "deploy.py"]

# Falling back to non-root user
USER climatechange

# API executable.
ENTRYPOINT ["pypy3", "main.py"]
