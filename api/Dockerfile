# Using PyPy 3 as the Python interpreter.
FROM pypy:latest

# Provisional solution to [BUG-015]
ARG LOCALHOST_IP
ENV LOCALHOST_IP=$LOCALHOST_IP

# Allows setting custom args to execute the deploy script. Use --build-arg DEPLOY_ARGS=<args> when building the API
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
RUN pip3 install -r /ClimateChangeApp/code/api/doc/requirements.txt

# Setting working directory.
WORKDIR /ClimateChangeApp/code/api

# Adding project root folder to PYTHONPATH, to avoid raising ImportError.
ENV PYTHONPATH /ClimateChangeApp:/ClimateChangeApp/code

# API log files will be generated under this directory.
VOLUME /ClimateChangeApp/log

# Deployment script which performs necessary operations before running the Subsystem for the first time.
RUN ["pypy3", "deploy.py"]

# API executable.
ENTRYPOINT ["pypy3", "main.py"]
