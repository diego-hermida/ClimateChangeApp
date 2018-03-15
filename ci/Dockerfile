FROM jenkins:latest

USER root

RUN apt-get update && \
apt-get -y install apt-transport-https ca-certificates curl \
     gnupg2 software-properties-common && \
curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg > /tmp/dkey; apt-key add /tmp/dkey && \
add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") \
   $(lsb_release -cs) \
   stable" && \
apt-get update && \
apt-get -y install docker-ce

# Getting the last package updates.
RUN apt-get update -y
RUN apt-get -y install python-pip
RUN pip install --upgrade pip setuptools
RUN pip install --upgrade pip setuptools docker-compose