#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.python import log
from balikator.workflows.workflow_doc_import import workflow_doc_import
from balikator.workflows.workflow_doc_ingest import workflow_doc_ingest
from balikator.utility.utils import utility
from datetime import datetime
import os


class workflow_batch_import(object):

    def __init__(self, db_int, db_sis, config, ssh, sftp, scp, dspace_api_key):
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.ssh = ssh
        self.sftp = sftp
        self.scp = scp
        self.dspace_api_key = dspace_api_key
        self.utility = utility(self.config)
        self.wf_doc_import = workflow_doc_import(self.db_int, self.db_sis, self.config, self.sftp, self.scp)
        self.wf_doc_ingest = workflow_doc_ingest(self.db_int, self.db_sis, self.config, self.ssh, self.sftp, self.scp,
                                                 self.dspace_api_key)

        if self.config.get('dspace', 'is_remote') is True:
            self.ssh = self.utility.create_ssh_client(server=self.config.get("storage", "server"),
                                                      port=self.config.getint("storage", "port"),
                                                      user=self.config.get("storage", "username"),
                                                      password=self.config.get("storage", "password"))
            self.sftp = self.utility.create_sftp_client(self.ssh)

    def run(self, batch):
        if batch.batch_process == 'doc_import':
            try:
                finished_process = self.import_batch(batch)
                batch.batch_process = finished_process
                batch.commit()
            except Exception as e:
                log.msg(e)
                batch.batch_state = 'failed'
                batch.errors.append(e)
                batch.error = str(e)
                batch.batch_finished_date = datetime.today()
                batch.commit()

        if batch.batch_process == 'doc_ingest':
            try:
                state = self.ingest_batch(batch)
                log.msg("INGEST BATCH RETURNED STATE: ", state)
                batch.batch_state = state
                batch.commit()
            except Exception as e:
                log.msg(e)
                batch.batch_state = 'failed'
                batch.errors.append(e)
                batch.error = str(e)
                batch.batch_finished_date = datetime.today()
                batch.commit()

        return batch.batch_state

    def import_batch(self, batch):
        # get all documents in this batch from database and import those that didn't fail during previous steps of
        # the workflow.
        # def get_documents_db():
        #     where = and_(self.db_int.document.batch_uuid == str(batch.batch_uuid),
        #                  self.db_int.document.state == 'finished_package')
        #     documents = self.db_int.document.filter(where).all()
        #     return documents

        def create_batch_import_dir_remote(sftp, remote_directory):
            """Change to this directory, recursively making new folders if needed.
            Returns True if any folders were created."""

            if remote_directory == '/':
                # absolute path so change directory to root
                sftp.chdir('/')
                return
            if remote_directory == '':
                # top-level relative directory must exist
                return
            try:
                sftp.chdir(remote_directory)  # sub-directory exists
            except IOError:
                dirname, basename = os.path.split(remote_directory.rstrip('/'))
                create_batch_import_dir_remote(sftp, dirname)  # make parent directories
                sftp.mkdir(basename)  # sub-directory missing, so created it
                sftp.chdir(basename)
                return True

        def create_batch_import_dir_local(local_path):
            try:
                # try to create document directory in the document root working directory
                if not os.path.exists(local_path):
                    os.makedirs(local_path)
                else:
                    pass
                return local_path
            except:
                raise Exception("Failed to create batch output directory.")

        def create_import_folder(folder_path):
            try:
                # create a package folder in the DSpace import folder (remote or local)
                # this folder will have the same name as the package folder copied into it
                if self.config.get('import', 'is_remote'):
                    create_batch_import_dir_remote(self.sftp, folder_path)
                else:
                    create_batch_import_dir_local(folder_path)
                return True
            except Exception as e:
                # fail gracefully if the batch import directory cannot be created
                raise e

        # we have the list of all documents from database, that were processed within this batch
        # and have a correct state, now we have to get to the actual document objects stored within the batch,
        # to be able to work with them
        log.msg("Getting documents marked for processing...")
        docs_process = batch.doc_objects_list

        log.msg("Getting processed documents from the database...")
        docs_database = batch.docs_with_state(state='finished_package')

        log.msg("Getting documents that can be imported...")
        docs_import = self.match_objects_by_did(docs_process, docs_database)

        log.msg("Number of documents from batch:", len(docs_process))
        log.msg("Number of documents from database:", len(docs_database))
        log.msg("Number of documents for import:", len(docs_import))

        for document in docs_import:
            log.msg("Creating package folder in the DSpace import directory...")

            folder_path = os.path.join(self.config.get('import', 'folder'), str(batch.batch_uuid), document.doc_id)

            # create import folder for document or fail with error
            if create_import_folder(folder_path=folder_path) is not True:
                raise Exception('Failed to create import folder.')

            # store the import folder in the document object
            document.import_folder = folder_path

            log.msg("Starting import workflow for document", document.doc_id)

            # start a import workflow of the document
            try:
                state = self.wf_doc_import.run(document)
                document.state = state
                document.commit()
            except Exception as e:
                document.state = 'failed'
                document.finished = datetime.today()
                document.error = str(e)
                document.commit()

        return 'doc_ingest'

    def ingest_batch(self, batch):
        docs_process = batch.doc_objects_list
        docs_db = batch.docs_with_state(state='finished_import')
        docs_ingest = self.match_objects_by_did(docs_process, docs_db)

        for document in docs_ingest:
            log.msg("Starting ingest workflow for document", document.doc_id)
            try:
                state = self.wf_doc_ingest.run(document)
                document.state = state
                document.finished = datetime.today()
                document.commit()
            except Exception as e:
                document.state = 'failed'
                document.finished = datetime.today()
                document.error = str(e)
                document.commit()

        return 'finished_import'

    def match_objects_by_did(self, docs_batch, docs_db):
        docs = list()
        for doc in docs_db:
            did = doc.did

            for doc_batch in docs_batch:
                log.msg("DOC DB DID:", did, "DOC BATCH ID:", doc_batch.doc_id)
                if int(doc_batch.doc_id) == int(did):
                    log.msg('FOUND A MATCH IN DID AND BATCH DOC ID:!', doc_batch.doc_id, did)
                    docs.append(doc_batch)

        return docs
