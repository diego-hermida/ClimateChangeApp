# Using PyPy 3 as the Python interpreter.
FROM pypy:latest

# Provisional solution to [BUG-015]
ARG LOCALHOST_IP
ENV LOCALHOST_IP=$LOCALHOST_IP

# Allows setting custom args to execute the deploy script. Use --build-arg DEPLOY_ARGS=<args> when building the Subsystem
# service with docker-compose.
ARG DEPLOY_ARGS
ENV DEPLOY_ARGS=$DEPLOY_ARGS

# Getting the last package updates.
RUN apt-get update
RUN pip install --upgrade pip setuptools
RUN pip3 install --upgrade pip setuptools

# Reading configuration from 'docker_global_config.config' instead of 'dev_global_config.config'
ENV DOCKER_MODE=true

# Adding project code to the image.
ADD . /DataSubsystems/code

# Installing all project dependencies.
RUN pip3 install -r /DataSubsystems/code/data_gathering_subsystem/doc/requirements.txt

# Setting working directory.
WORKDIR /DataSubsystems/code/data_gathering_subsystem

# Adding project root folder to PYTHONPATH, to avoid raising ImportError.
ENV PYTHONPATH /DataSubsystems:/DataSubsystems/code

# Subsystem log files will be generated under this directory.
VOLUME /DataSubsystems/log

# Subsystem '.state' files will be generated under this directory.
VOLUME /DataSubsystems/state/data_gathering_subsystem

# Deploy script which performs necessary operations before running the Subsystem for the first time.
RUN ["pypy3", "deploy.py"]

# Subsystem executable.
ENTRYPOINT ["pypy3", "main.py"]
