#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.python import log
from balikator.utility.utils import utility
from datetime import datetime


class workflow_doc_delete(object):

    def __init__(self, db_int, config, ssh, sftp, scp):
        self.db_int = db_int
        self.config = config
        self.utility = utility(config=self.config)
        self.ssh = ssh
        self.sftp = sftp
        self.scp = scp

    def run(self, document):
        log.msg("WORKFLOW DELETE - Document state:", document.state)
        # runs document deletion workflow
        if document.state == 'started':
            log.msg("Trying to run unimport_document() function...")
            try:
                state = self.unimport_document(document)
                document.state = state
                document.current_process = 'document_finish' # set document_finish as a current process of the document
                document.finished = datetime.today()
                document.commit()
            except Exception as e:
                log.msg(e)
                document.errors.append(e)
                document.error = str(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        return document.state

    def unimport_document(self, document):
        log.msg("Document", document.doc_id, "has to be deleted.")
        log.msg("Removing document", document.doc_id, "from DSpace.")
        if self.config.get('import', 'is_remote') is True:
            if document.unimport_remote(ssh=self.ssh, sftp=self.sftp):
                log.msg("Document", document.doc_id, "unimported.")
                # delete mapfile after deleting document, should prevent failure when importing document with
                # the same mapfile
                # WE DO NOT WANT TO DELETE MAPFILES!
                # if document.delete_mapfile_remote(sftp_client=self.sftp):
                #     log.msg("Mapfile removed.")
                # else:
                #     log.msg("No mapfile found.")
            else:
                raise Exception('Failed to unimport document ' + document.doc_id)
        else:
            if document.unimport_local():
                log.msg("Document", document.doc_id, "unimported.")
                # delete mapfile after deleting document, should prevent failure when importing document with
                # the same mapfile
                # WE DO NOT WANT TO DELETE MAPFILES!
                # if document.delete_mapfile_local():
                #     log.msg("Mapfile removed.")
                # else:
                #     log.msg("No mapfile found.")
            else:
                raise Exception('Failed to unimport document ' + document.doc_id)

        return 'finished'


