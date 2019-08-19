#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from twisted.python import log
from balikator.utility.utils import utility
from datetime import datetime
from time import sleep


class workflow_doc_ingest(object):

    def __init__(self, db_int, db_sis, config, ssh, sftp, scp, dspace_api_key):
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.ssh = ssh
        self.sftp = sftp
        self.scp = scp
        self.dspace_api_key = dspace_api_key
        self.utility = utility(config=self.config)

    def run(self, document):

        if document.current_process == 'ingest':
            # ingest package or unimport already existing object and ingest a new one with
            # already assigned handle
            try:
                log.msg('WORKFLOW_DOC_IMPORT: Starting document_ingest() function...')
                new_process = self.document_ingest(document)
                document.current_process = new_process
                document.commit()
            except Exception as e:
                log.msg(e)
                document.error = str(e)
                document.errors.append(e)
                document.finished = datetime.today()
                document.state = 'failed'
                document.commit()

        # sleep after ingest to prevent too many HTTP requests
        sleep(2)

        if document.current_process == 'handle':
            # get document handle from mapfile and store it in the database
            try:
                log.msg('WORKFLOW_DOC_INGEST: Starting handle_acquisition() function...')
                new_process = self.handle_acquisition(document)
                document.current_process = new_process
                document.commit()
            except Exception as e:
                log.msg(e)
                document.error = str(e)
                document.errors.append(e)
                document.finished = datetime.today()
                document.state = 'failed'
                document.commit()

        if document.current_process == 'ingest_check':
            # check if document is ingested to DSpace (use DSpace API and search for handle)
            try:
                log.msg("WORKFLOW_DOC_INGEST: Starting ingest_check() function...")
                new_process = self.ingest_check(document)
                document.current_process = new_process
                document.state = 'finished'
                document.finished = datetime.today()
                document.commit()
            except Exception as e:
                log.msg(e)
                document.error = str(e)
                document.errors.append(e)
                document.finished = datetime.today()
                document.state = 'failed'
                document.commit()

        # sleep after ingest check to prevent too many HTTP requests
        sleep(2)

        return document.state

    def document_ingest(self, document):

        # check if document should be first unimported or not
        #   ==> document has direction set to "update"
        #   and
        #   ==> document is in DSpace repository (has a handle in database?)
        #   and
        #   ==> document package should already have a handle file inside
        #
        # Document, that should be removed from DSpace do not enter this workflow at all
        if document.workflow_process == 'update':
            if document.handle is not None:
                log.msg("Document", document.doc_id, "has to be updated.")
                log.msg("Replacing previous version of document", document.doc_id, "in DSpace.")
                # this document should be updated - removed and inserted again
                if self.config.getboolean('import', 'is_remote') is True:
                    log.msg('Document should be replace in remote DSpace server...')
                    if document.replace_remote(ssh=self.ssh):
                        log.msg("Document", document.doc_id, "replaced.")
                    else:
                        raise Exception('Failed to replace document ' + document.doc_id)
                    # if document.unimport_remote(ssh=self.ssh, sftp=self.sftp):
                    #     log.msg("Document", document.doc_id, "unimported.")
                    #     # delete mapfile after deleting document, should prevent failure when importing document with
                    #     # the same mapfile
                    #     if document.delete_mapfile_remote(sftp_client=self.sftp):
                    #         log.msg("Mapfile removed.")
                    #     else:
                    #         log.msg("No mapfile found.")
                    # else:
                    #     raise Exception('Failed to unimport document ' + document.doc_id)
                else:
                    log.msg('Document should be replace in local DSpace...')
                    if document.replace_local():
                        log.msg("Document", document.doc_id, "replaced.")
                    else:
                        raise Exception('Failed to replace document ' + document.doc_id)
            else:
                # document should be updated but doesn't have a handle in the database
                raise Exception('Document should be updated but has no handle in the database.')

            return 'handle'

        if self.config.getboolean('import', 'is_remote') is True:
            if document.delete_mapfile_remote(sftp_client=self.sftp):
                log.msg("Mapfile from previous import found and deleted.")
            else:
                log.msg("Mapfile from previous import not found.")

            if document.ingest_remote(ssh=self.ssh):
                log.msg("Document", document.doc_id, "ingested.")
            else:
                raise Exception('Failed to ingest document ' + document.doc_id)
        else:
            if document.delete_mapfile_local():
                log.msg("Mapfile from previous import found and deleted.")
            else:
                log.msg("Mapfile from previous import not found.")

            if document.ingest_local():
                log.msg("Document", document.doc_id, "ingested.")
            else:
                raise Exception('Failed to ingest document ' + document.doc_id)

        return 'handle'

    def handle_acquisition(self, document):

        def parse_handle_remote():
            mapfile_name = document.doc_id + self.config.get('dspace', 'mapfile_suff')
            mapfile_path = os.path.join(self.config.get('dspace', 'mapfile_path'), mapfile_name)

            mapfile = self.sftp.open(mapfile_path)

            try:
                # read line from mapfile, remove newline characters
                line = mapfile.readline()

            except Exception as e:
                log.err(e)
                raise Exception('Failed to read a line from mapfile.')
            finally:
                mapfile.close()

            return str(line).rstrip()

        def parse_handle_local():
            mapfile_name = document.doc_id + self.config.get('dspace', 'mapfile_suff')
            mapfile_path = os.path.join(self.config.get('dspace', 'mapfile_path'), mapfile_name)

            mapfile = open(mapfile_path)

            try:
                # read line from mapfile, remove newline characters
                line = mapfile.readline()
            except Exception as e:
                log.err(e)
                raise Exception('Failed to read a line from mapfile.')
            finally:
                mapfile.close()

            return str(line).rstrip()

        def insert_handle(handle_id):
            log.msg("Inserting handle", handle_id, "to database.")
            try:
                document.handle = handle_id
            except Exception as e:
                log.err(e)
                raise Exception('Failed to insert handle to document_handles table.')

            try:
                document.document_handle = handle_id
            except:
                raise Exception('Failed to insert handle to document table.')

            return True

        # if document already has a handle assigned, there is no need to parse it and store it again
        if document.handle is not None:
            log.msg("Document already has a handle:\n", "Document DID:", document.doc_id, "handle:", document.handle)
            return 'ingest_check'

        # just get the handle file from remote or local folder and parse the handle to the database tables:
        #   document_handles
        #   document
        if self.config.get('dspace', 'is_remote') is True:
            handle_line = parse_handle_remote()
        else:
            handle_line = parse_handle_local()

        # create array from handle line, handle should be stored in second place of the array
        line_array = handle_line.split(sep=' ')

        try:
            line_array[1]
        except IndexError as e:
            raise Exception('Failed to acquire document handle.')

        handle = line_array[1]
        handle_postprocess = str(handle).rstrip()

        if insert_handle(handle_postprocess):
            document.commit()
            log.msg('Handle', handle_postprocess, 'inserted to database.')
        else:
            self.db_int.rollback()
            raise Exception('Failed to insert handle to the database.')

        # return 'document_finish'
        return 'ingest_check'

    def ingest_check(self, document):

        # checking if document was indeed ingested, e.g. DSpace API reports it is in DSpace
        if document.document_in_dspace(handle=document.handle) is True:
            return 'document_finish'
        else:
            raise Exception('Document not found in DSpace after ingest.')
