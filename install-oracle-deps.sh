#!/usr/bin/env bash
unzip $PREREQUISITIES/oracle/instantclient-basic-linux.zip -d /opt/oracle
unzip $PREREQUISITIES/oracle/instantclient-sdk-linux.zip -d /opt/oracle
mv /opt/oracle/instantclient_* /opt/oracle/instantclient
ln -s /opt/oracle/instantclient/libclntsh.so.* /opt/oracle/instantclient/libclntsh.so
ln -s /opt/oracle/instantclient/libocci.so.* /opt/oracle/instantclient/libocci.so

export ORACLE_HOME="/opt/oracle/instantclient"
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ORACLE_HOME

export OCI_HOME="/opt/oracle/instantclient"
export OCI_LIB_DIR="/opt/oracle/instantclient"
export OCI_INCLUDE_DIR="/opt/oracle/instantclient/sdk/include"