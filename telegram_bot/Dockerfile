# Using PyPy 3 as the Python interpreter.
FROM pypy:latest

# Adding user and group: avoiding running containers as root
RUN groupadd -g 999 climatechange && useradd -r -u 999 -g climatechange climatechange

# Setting ENV variables from ARGs.
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
RUN pip3 install -r /ClimateChangeApp/code/telegram_bot/doc/requirements.txt

# Setting working directory.
WORKDIR /ClimateChangeApp/code/telegram_bot

# Adding project root folder to PYTHONPATH, to avoid raising ImportError.
ENV PYTHONPATH /ClimateChangeApp:/ClimateChangeApp/code

# Deploy script which performs necessary operations before running the Subsystem for the first time.
RUN ["pypy3", "deploy.py"]

# Falling back to non-root user
USER climatechange

# Subsystem executable.
ENTRYPOINT ["pypy3", "main.py"]
