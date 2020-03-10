FROM python:3.7
MAINTAINER Jakub Řihák <jakub.rihak@ruk.cuni.cz>

# INSTALL TOOLS
RUN apt-get update 
RUN apt-get -yqq install unzip
RUN apt-get -yqq install libaio-dev

# CREATE DIRECTORY STRUCTURE
RUN mkdir -p /opt/data/balikator/
RUN mkdir -p /opt/data/prerequisities/oracle/

RUN wget -P /opt/data/balikator/prerequisities/oracle/ "https://download.oracle.com/otn_software/linux/instantclient/instantclient-basic-linux.zip"
RUN wget -P /opt/data/balikator/prerequisities/oracle/ "https://download.oracle.com/otn_software/linux/instantclient/instantclient-sdk-linux.zip"

# ADD balikator code
ADD balikator_core /opt/data/balikator/balikator_core
ADD install-oracle-deps.sh /opt/data/balikator/prerequisities
WORKDIR /opt/data/balikator

# SET ENVIRONMENT VARIABLES
ENV ORACLE_HOME=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ORACLE_HOME

ENV OCI_HOME=/opt/oracle/instantclient
ENV OCI_LIB_DIR=/opt/oracle/instantclient
ENV OCI_INCLUDE_DIR=/opt/oracle/instantclient/sdk/include

ENV PREREQUISITIES=/opt/data/balikator/prerequisities

# INSTALL  ORACLE DEPENDENCIES
RUN ["chmod", "+x", "/opt/data/balikator/prerequisities/install-oracle-deps.sh"]
RUN ./prerequisities/install-oracle-deps.sh

# INSTALL BALIKATOR REQUIREMENTS
RUN pip install -r ./balikator_core/requirements.txt
