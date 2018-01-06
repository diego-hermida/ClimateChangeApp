# Using PyPy 3 as the Python interpreter.
FROM pypy:latest

# Provisional solution to [BUG-015]
ARG LOCALHOST_IP
ENV LOCALHOST_IP=$LOCALHOST_IP

# Allows skipping deploy operations by setting an environment variable. Use --build-arg SKIP_DEPLOY=true when building
# the Subsystem service with docker-compose.
ARG SKIP_DEPLOY=false
ENV SKIP_DEPLOY=$SKIP_DEPLOY

# Getting the last package updates.
RUN apt-get update
RUN pip install --upgrade pip setuptools
RUN pip3 install --upgrade pip setuptools

# Reading configuration from 'docker_global_config.config' instead of 'dev_global_config.config'
ENV DOCKER_MODE=true

# Adding project code to the image.
ADD . /DataGatheringSubsystem/code

# Installing all project dependencies.
RUN pip3 install -r /DataGatheringSubsystem/code/doc/requirements.txt

# Setting working directory.
WORKDIR /DataGatheringSubsystem/code/exec

# Adding project root folder to PYTHONPATH, to avoid raising ImportError.
ENV PYTHONPATH /DataGatheringSubsystem:/DataGatheringSubsystem/code

# Subsystem log files will be generated under this directory.
VOLUME /DataGatheringSubsystem/log

# Subsystem '.state' files will be generated under this directory.
VOLUME /DataGatheringSubsystem/state

# Deployment script which performs necessary operations before running the Subsystem for the first time.
# Tests are also executed.
RUN ["pypy3", "deploy.py", "--all", "--with-tests"]

# Subsystem executable.
ENTRYPOINT ["pypy3", "main.py"]
