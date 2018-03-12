# Using PyPy 3 as the Python interpreter.
FROM pypy:latest

# Setting environment variables.
ARG MONGODB_IP
ARG POSTGRES_IP
ARG MONGODB_PORT=27017
ARG POSTGRES_PORT=5432

ENV MONGODB_IP=$MONGODB_IP
ENV POSTGRES_IP=$POSTGRES_IP
ENV MONGODB_PORT=$MONGODB_PORT
ENV POSTGRES_PORT=$POSTGRES_PORT

# Allows setting custom args to execute the deploy script. Use --build-arg DEPLOY_ARGS=<args> when building the Subsystem
# service with docker-compose.
ARG DEPLOY_ARGS
ENV DEPLOY_ARGS=$DEPLOY_ARGS

# Getting the last package updates.
RUN apt-get update
RUN pip install --upgrade pip setuptools
RUN pip3 install --upgrade pip setuptools

# Reading configuration from 'docker_config.config' instead of 'dev_config.config'
ENV DOCKER_MODE=true

# Adding project code to the image.
ADD . /ClimateChangeApp/code

# Installing all project dependencies.
RUN pip3 install -r /ClimateChangeApp/code/utilities/doc/requirements.txt

# Setting working directory.
WORKDIR /ClimateChangeApp/code/utilities

# Adding project root folder to PYTHONPATH, to avoid raising ImportError.
ENV PYTHONPATH /ClimateChangeApp:/ClimateChangeApp/code

# Component executable.
RUN ["pypy3", "deploy.py"]

ENTRYPOINT ['']