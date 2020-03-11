FROM alpine:latest
MAINTAINER Jakub Řihák <jakub.rihak@ruk.cuni.cz>

#### packages from https://pkgs.alpinelinux.org/packages
# These are always installed. Notes:
#   * dumb-init: a proper init system for containers, to reap zombie children
#   * bash: For entrypoint, and debugging
#   * ca-certificates: for SSL verification during Pip and easy_install
#   * python: the binaries themselves
#   * openblas: required for numpy.
#   * libaio libnsl: for cx_Oracle
ENV PACKAGES="\
  dumb-init \
  bash vim tini
  ca-cetificates \
  python3==3.7.6 \
  libaio libnsl \
"

# These packages are not installed immediately, but are added at runtime or ONBUILD to shrink the image as much as possible. Notes:
#   * build-base: used so we include the basic development packages (gcc)
#   * linux-headers: commonly needed, and an unusual package name from Alpine.
ENV BUILD_PACKAGES="\
  build-base \
  linux-headers \
"

## for install oracle instant client
ENV ORACLE_HOME=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ORACLE_HOME

ENV OCI_HOME=/opt/oracle/instantclient
ENV OCI_LIB_DIR=/opt/oracle/instantclient
ENV OCI_INCLUDE_DIR=/opt/oracle/instantclient/sdk/include

# TODO: Contiue - use help from http://www.programmersought.com/article/6561944148/ - contiue from "RUN echo \"



# CREATE DIRECTORY STRUCTURE
RUN mkdir -p /opt/data/balikator/
RUN mkdir -p /opt/data/prerequisities/oracle/

RUN wget -P /opt/data/balikator/prerequisities/oracle/ "https://download.oracle.com/otn_software/linux/instantclient/instantclient-basic-linux.zip"
RUN wget -P /opt/data/balikator/prerequisities/oracle/ "https://download.oracle.com/otn_software/linux/instantclient/instantclient-sdk-linux.zip"

# ADD balikator code
ADD balikator_core /opt/data/balikator/balikator_core
ADD install-oracle-deps.sh /opt/data/balikator/prerequisities
WORKDIR /opt/data/balikator

ENV PREREQUISITIES=/opt/data/balikator/prerequisities

# INSTALL  ORACLE DEPENDENCIES
RUN ["chmod", "+x", "/opt/data/balikator/prerequisities/install-oracle-deps.sh"]
RUN ./prerequisities/install-oracle-deps.sh

# INSTALL BALIKATOR REQUIREMENTS
RUN pip install -r ./balikator_core/requirements.txt
