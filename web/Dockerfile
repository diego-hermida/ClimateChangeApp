# Using PyPy 3 as the Python interpreter.
FROM pypy:latest

# Setting ENV variables from ARGs.
ARG CACHE_SERVER_IP
ARG CACHE_SERVER_PORT=11211
ARG DEPLOY_ARGS
ARG POSTGRES_IP
ARG POSTGRES_PORT=5432
ARG SUPERUSER_USERNAME
ARG SUPERUSER_PASSWORD
ARG USER=1000

ENV CACHE_SERVER_IP=$CACHE_SERVER_IP
ENV CACHE_SERVER_PORT=$CACHE_SERVER_PORT
ENV DEPLOY_ARGS=$DEPLOY_ARGS
ENV POSTGRES_IP=$POSTGRES_IP
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV SUPERUSER_USERNAME=$SUPERUSER_USERNAME
ENV SUPERUSER_PASSWORD=$SUPERUSER_PASSWORD
ENV DJANGO_SETTINGS_MODULE="web.settings"

# Adding user and group: avoiding running containers as root
RUN useradd -r -N -u $USER climatechange || true

# Getting the last package updates.
RUN apt-get update
RUN apt-get install -y swig libssl-dev dpkg-dev netcat
RUN pip install --upgrade pip setuptools
RUN pip3 install --upgrade pip setuptools

# Reading configuration from 'docker_config.config' instead of 'dev_config.config'
ENV DOCKER_MODE=true

# Adding project code to the image.
ADD . /ClimateChangeApp/code

# Installing all project dependencies.
RUN pip3 install -r /ClimateChangeApp/code/web/doc/requirements.txt

# Setting working directory.
WORKDIR /ClimateChangeApp/code/web

# Adding project root folder to PYTHONPATH, to avoid raising ImportError.
ENV PYTHONPATH /ClimateChangeApp:/ClimateChangeApp/code:/ClimateChangeApp/code/web/web:/ClimateChangeApp/code/web/climate

# Subsystem log files will be generated under this directory.
VOLUME /ClimateChangeApp/log

# Deploy script which performs necessary operations before running the Subsystem for the first time.
RUN ["pypy3", "deploy.py"]

# Adding HEALTHCHECK
COPY ./web/healthcheck /usr/local/bin/healthcheck
RUN chmod +x /usr/local/bin/healthcheck
HEALTHCHECK --start-period=120s CMD ["/usr/local/bin/healthcheck"]

# Subsystem executable.
COPY ./web/entrypoint /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

# Falling back to non-root user
USER $USER

# Application entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint"]
