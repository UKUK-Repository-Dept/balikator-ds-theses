#!/usr/bin/env bash
unzip $PREREQUISITIES/oracle/instantclient-basic-linux.x64-19.6.0.0.0dbru.zip -d /opt/oracle
unzip $PREREQUISITIES/oracle/instantclient-sdk-linux.x64-19.6.0.0.0dbru.zip -d /opt/oracle
mv /opt/oracle/instantclient_* /opt/oracle/instantclient

export ORACLE_DIR="/opt/oracle/instantclient"
export LD_LIBRARY_PATH=$ORACLE_DIR:$LD_LIBRARY_PATH

export OCI_HOME="/opt/oracle/instantclient"
export OCI_LIB_DIR="/opt/oracle/instantclient"
export OCI_INCLUDE_DIR="/opt/oracle/instantclient/sdk/include"