#!/usr/bin/env python
# -*- coding: utf-8 -*-

from getopt import gnu_getopt
from sys import argv, stderr
# Configuration is stored in a simple ini file
from configparser import ConfigParser, ExtendedInterpolation
# import database classes
from balikator.db_int import reflect_internal
from balikator.db_dspace import reflect_dspace
# Data are accessed through  SQLSoup, using SQLAlchemy
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from sqlsoup import SQLSoup
# Synchronizer
from aleph_synchronizer.synchronize import Synchronize

if __name__ == '__main__':

    def do_start(pack_config, sync_config):

        # get database connection string
        sis_url = pack_config.get('database', 'sis_url')
        db_url_internal = pack_config.get('database', 'internal_url')
        dspace_url = pack_config.get('database', 'dspace_url')

        # default to much saner database query defaults and always
        # commit and/or flush statements explicitly
        factory = sessionmaker(autocommit=False, autoflush=False)

        # INTERNAL database
        engine_internal = create_engine(db_url_internal, encoding='utf-8')
        session_internal = scoped_session(factory)
        db_int_meta = reflect_internal(engine_internal)
        db_internal = SQLSoup(db_int_meta, session=session_internal)
    
        # Instatiate synchronizer class
        sync = Synchronize(pack_config, sync_config, db_internal)
        
        # start synchronizer
        sync.synchronize()



    def do_help(*args, **kwargs):
        pass

    def do_version(*args, **kwargs):
        pass


    # Parse command line arguments
    opts, args = gnu_getopt(argv, 'hVps:', ['help', 'version', 'packconfig=', 'syncconfig='])

    action = do_start
    pack_config_path = '../balikator/config/balikator.ini'
    sync_config_path = './aleph_synchronizer/config/synchronizer.ini'

    for k, v in opts:
        if k in ('--help', '-h'):
            action = do_help
        elif k in ('--version', '-V'):
            action = do_version
        elif k in ('--packconfig', '-p'):
            pack_config_path = v
        elif k in ('--syncconfig', '-s'):
            sync_config_path = v

    # Load the configuration from file.
    pack_config = ConfigParser(interpolation=ExtendedInterpolation())
    pack_config.read(pack_config_path)

    sync_config = ConfigParser(interpolation=ExtendedInterpolation())
    sync_config.read(sync_config_path)

    # Perform selected action.
    action(pack_config=pack_config, sync_config=sync_config)
    