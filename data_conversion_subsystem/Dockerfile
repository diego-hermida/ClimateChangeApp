# Using PyPy 3 as the Python interpreter.
FROM pypy:latest

# Setting ENV variables from ARGs.
ARG API_IP
ARG API_PORT=5000
ARG DEPLOY_ARGS
ARG POSTGRES_IP
ARG POSTGRES_PORT=5432
ARG USER=1000

ENV API_IP=$API_IP
ENV API_PORT=$API_PORT
ENV DEPLOY_ARGS=$DEPLOY_ARGS
ENV POSTGRES_IP=$POSTGRES_IP
ENV POSTGRES_PORT=$POSTGRES_PORT

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
RUN pip3 install -r /ClimateChangeApp/code/data_conversion_subsystem/doc/requirements.txt

# Setting working directory.
WORKDIR /ClimateChangeApp/code/data_conversion_subsystem

# Adding project root folder to PYTHONPATH, to avoid raising ImportError.
ENV PYTHONPATH /ClimateChangeApp:/ClimateChangeApp/code

# Subsystem log files will be generated under this directory.
VOLUME /ClimateChangeApp/log

# Subsystem '.state' files will be generated under this directory.
VOLUME /ClimateChangeApp/state

# Deploy script which performs necessary operations before running the Subsystem for the first time.
RUN ["pypy3", "deploy.py"]

# Falling back to non-root user
USER $USER

# Subsystem executable.
ENTRYPOINT ["pypy3", "main.py"]
