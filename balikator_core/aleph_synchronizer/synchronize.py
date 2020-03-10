#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import pyjq
from balikator.handlers.db_handler import db_handler
from balikator.utility.utils import utility
from aleph_synchronizer.mapfile.mapfile import Mapfile

class Synchronize(object):

    def __init__(self, pack_config, sync_config, db_int):
        self.__pack_config = pack_config
        self.__sync_config = sync_config
        self.__db_int = db_int
        self.__db_handler = None
        self.__utility = None
        self.__sync_candidates = None
        self.__mapfile_dirpath = self.__sync_config.get('mapfiles','sis')
        self.__mapfile = None
        self.__dspace_changed = False
    
    def synchronize(self):

        # Initialize db handler
        self.__db_handler = self.__initialize_handlers()

        # Initialize utility class
        self.__utility = self.__initialize_utility()
        
        # Get records in DATABASE that do not have ALEPH sysno stored (meaning it was not available at the time of the creation)
        self.__sync_candidates = self.__get_sync_candidates()

        # Get the instance of a mapfile generated for IS as JSON
        self.__mapfile = self.__create_mapfile()

        # For each record previously selected from DB, check if there's a sysno in mapfile
        #   If yes:
        #       call __do_sync()
        #   If no:
        #       move on to the next record
        i = 1
        for record in self.__sync_candidates:
            print("{}/{}: Searching for repID: {}".format(i, len(self.__sync_candidates), record.repId))
            found_record = self.__sysno_in_mapfile(record)
            
            if isinstance(found_record, dict):
                print(found_record)
                
                # Sync it!
                self.__do_sync(found_record, str(record.handle).rstrip())
            else:
                continue

            i += 1

        # If there's at least one marked change in DSpace, generate mapfile for Aleph again and rewrite the existing one
        

    def __initialize_handlers(self):
        db_handler_instance = db_handler(self.__pack_config, self.__db_int)
        return db_handler_instance

    def __initialize_utility(self):
        utility_instance = utility(self.__pack_config)
        return utility_instance

    def __get_sync_candidates(self):
        records = self.__db_handler.get_docs_without_sysno()
        return records

    def __create_mapfile(self):
        mapfiles = [f for f in os.listdir(self.__mapfile_dirpath) if re.match(self.__sync_config.get('mapfiles_names','sis'),f)]
        
        if len(mapfiles) == 0:
            raise Exception ('No mapfile was found at ' + self.__mapfile_dirpath)
        
        if len(mapfiles) > 1:
            raise Exception ('Multiple mapfiles were found at ' + self.__mapfile_dirpath)

        filepath = os.path.join(self.__mapfile_dirpath, mapfiles[0])

        if self.__utility.file_exists(filepath, is_remote=False):
            mapfile = Mapfile(filepath)
            
            mapfile.create()

            return mapfile

    def __sysno_in_mapfile(self, record):
        
        # TODO: Valid CSV headers that could be used in JQ should be defined in sync_config and validated
        # TODO: Check if standard python dict method .values() would be quicker than pyjq
        
        # selects only alephID from found record
        #jq_string = '.records[] | select(.repId == $repId) | .alephId'

        # selects whole dict of the found record
        jq_string = '.records[] | select(.repId == $repId)'
        
        repId = record.repId
        
        #jq_string = '.records[] | select(.repId == ' + '"' + str(repId) + '"' + ')'
            
        response = pyjq.one(script=jq_string, value=self.__mapfile.mapfile, vars={"repId": str(repId)})
            
        return response
    
    def __do_sync(self, mapfile_record, record_handle):
        #       store sysno in database
        #       add sysno to DSpace record
        #       add sisId to DSpace record
        #       reindex DSpace object identified by handle
        #       mark change in DSpace
        print("Synchronizing record {} (HANDLE: {})!".format(mapfile_record['repId'], record_handle))


        pass

    def __store_sysno_db(self):
        pass
    
    def __add_sysno_dspace(self):
        pass

    def add_sisid_dspace(self):
        pass

    