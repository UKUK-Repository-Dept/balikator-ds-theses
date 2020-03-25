FROM alpine:3.7
ENV ALPINE_VERSION=3.7
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
  bash vim tini \
  ca-certificates \
  python3 \
  python3-dev \
  libaio libnsl \
"

# These packages are not installed immediately, but are added at runtime or ONBUILD to shrink the image as much as possible. Notes:
#   * build-base: used so we include the basic development packages (gcc)
#   * linux-headers: commonly needed, and an unusual package name from Alpine.
ENV BUILD_PACKAGES="\
  build-base \
  linux-headers \
  git \
"

ENV PYTHON3_PACKAGES="\
  postgresql-dev \
  libxslt-dev \
  libffi-dev \
"

## for install oracle instant client
ENV ORACLE_HOME=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ORACLE_HOME

ENV OCI_HOME=/opt/oracle/instantclient
ENV OCI_LIB_DIR=/opt/oracle/instantclient
ENV OCI_INCLUDE_DIR=/opt/oracle/instantclient/sdk/include

# TODO: Contiue - use help from http://www.programmersought.com/article/6561944148/ - contiue from "RUN echo \"

# REPLACE DEFAULT REPOSITORIES WITH EDGE ONES

# CREATE DIRECTORY STRUCTURE
RUN mkdir -p /opt/data/balikator/
RUN mkdir -p /opt/data/balikator/prerequisities/oracle/
RUN mkdir -p /opt/oracle/

RUN wget -P /opt/data/balikator/prerequisities/oracle/ "https://download.oracle.com/otn_software/linux/instantclient/instantclient-basic-linux.zip"
RUN wget -P /opt/data/balikator/prerequisities/oracle/ "https://download.oracle.com/otn_software/linux/instantclient/instantclient-sdk-linux.zip"

# ADD balikator code
ADD balikator_core /opt/data/balikator/balikator_core
ADD install-oracle-deps.sh /opt/data/balikator/prerequisities
WORKDIR /opt/data/balikator

ENV PREREQUISITIES=/opt/data/balikator/prerequisities

#RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories
#RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories
#RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories


# INSTALL ALPINE PACKAGES 
RUN apk add --no-cache --virtual=.build-deps $BUILD_PACKAGES

RUN apk add --no-cache $PACKAGES || \
    (sed -i -e 's/dl-cdn/dl-4/g' /etc/apk/repositories && apk add --no-cache $PACKAGES)

RUN apk add --no-cache $PYTHON3_PACKAGES

# INSTALL  ORACLE DEPENDENCIES
RUN ["chmod", "+x", "/opt/data/balikator/prerequisities/install-oracle-deps.sh"]
RUN ./prerequisities/install-oracle-deps.sh

RUN echo "**** install pip ****" && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools wheel && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi

# 5.make some useful symlinks that are expected to exist
RUN cd /usr/bin \
  && { [[ -e idle ]] || ln -s idle3 idle; } \
  && { [[ -e pydoc ]] || ln -s pydoc3 pydoc; } \
  && { [[ -e python ]] || ln -sf python3.6 python; } \
  && { [[ -e python-config ]] || ln -sf python3-config python-config; } \
  && { [[ -e pip ]] || ln -sf pip3 pip; } \
  && ls -l idle pydoc python* pip* \
  #&& python -m pip install --upgrade --no-cache-dir pip \
  && ls -l idle pydoc python* pip* \
  && cd /opt/data/balikator

# INSTALL BALIKATOR REQUIREMENTS
RUN pip install -r ./balikator_core/requirements.txt

RUN apk del .build-deps \
  && cd /usr/bin \
  && ls -l idle pydoc python* pip* \
  && echo \
  && cd /opt/data/balikator

ENTRYPOINT tail -f /dev/null

CMD ["/bin/bash"]