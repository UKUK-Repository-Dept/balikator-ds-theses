#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from balikator.workflows.workflow_doc_setup import workflow_doc_setup
from balikator.workflows.workflow_doc_delete import workflow_doc_delete
from balikator.workflows.workflow_doc_package import workflow_doc_package
from balikator.workflows.workflow_doc_import import workflow_doc_import
from balikator.workflows.workflow_doc_ingest import workflow_doc_ingest
from balikator.workflows.workflow_doc_finish import workflow_doc_finish
from twisted.python import log
from datetime import datetime


class workflow_batch_processing(object):

    def __init__(self, db_int, db_sis, config, ssh, sftp, scp, dspace_api_key):
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.ssh = ssh
        self.sftp = sftp
        self.scp = scp
        self.dspace_api_key = dspace_api_key
        self.wf_doc_setup = workflow_doc_setup(self.db_int, self.db_sis, self.config, self.sftp, self.scp,
                                               self.dspace_api_key)
        self.wf_doc_package = workflow_doc_package(self.db_int, self.db_sis, self.config, self.sftp, self.scp)
        self.wf_doc_import = workflow_doc_import(self.db_int, self.db_sis, self.config, self.sftp, self.scp)
        self.wf_doc_ingest = workflow_doc_ingest(self.db_int, self.db_sis, self.config, self.ssh, self.sftp, self.scp,
                                                 self.dspace_api_key)
        self.wf_doc_finish = workflow_doc_finish(self.db_int, self.db_sis, self.config, self.ssh, self.sftp, self.scp)
        self.wf_doc_delete = workflow_doc_delete(self.db_int, self.config, self.ssh, self.sftp, self.scp)

    def run(self, batch):
        """
        For each document, try run a setup first, then if it's not failed, run a packager.
        :param batch:
        :return:
        """
        if batch.batch_process == 'doc_setup':
            try:
                finished_process = self.setup_documents(batch)
                batch.batch_process = finished_process
                batch.commit()
            except Exception as e:
                log.msg(e)
                batch.batch_state = 'failed'
                batch.errors.append(e)
                batch.error = str(e)
                batch.batch_finished_date = datetime.today()
                batch.commit()

        if batch.batch_process == 'doc_processing':
            try:
                state = self.process_documents(batch)
                batch.batch_state = state
                batch.batch_process = 'doc_import'
                batch.commit()
            except Exception as e:
                log.msg(e)
                batch.batch_state = 'failed'
                batch.errors.append(e)
                batch.error = str(e)
                batch.batch_finished_date = datetime.today()
                batch.commit()

        return batch.batch_state

    def setup_documents(self, batch):

        if len(batch.doc_objects_list) == 0:
            log.msg("SETUP DOCUMENTS:")
            log.msg("There are no documents in batch", batch.batch_uuid, "...")
            return 'doc_processing'

        for document in batch.doc_objects_list:

            log.msg("Setting up document", document.doc_id)

            log.msg("Setting document import folder...")
            document.import_folder = os.path.join(batch.import_folder, document.doc_id)

            log.msg("Setting document errors folder...")
            document.error_folder = os.path.join(batch.errors_folder, document.doc_id)

            try:
                state = self.wf_doc_setup.run(document)
                document.state = state
                document.commit()
            except Exception as e:
                document.state = 'failed'
                document.errors.append(e)
                document.finished = datetime.today()
                document.commit()

        return 'doc_processing'

    def process_documents(self, batch):
        """
        CREATE PACKAGES FOR IMPORT TO DSPACE
        Method starts document workflow processing for each document stored in batch array of documents to be processed.
        When document processing is done (e.g. the finished_package method returns some state, method checks in what
        state this document is and aither logs an error during document processing, informs about successfull
        processing or raises an exception if document finished with unexpected state.
        :param batch: batch object
        :return: 'batch_finish' - finished process indication
        """
        for document in batch.doc_objects_list:
            log.msg("Processing document", document.doc_id)

            if document.workflow_process not in ['insert', 'update', 'delete', None]:
                raise Exception(
                    'Invalid workflow process for document ' + document.doc_id + ': ' + document.workflow_process)

            if document.workflow_process is None:
                # DOCUMENT SKIPPING FOR DOCUMENTS WITH WORKFLOW PROCESS SET TO NONE #
                log.msg('Document has no assigned process - this means it cannot be processed in the workflow.')
                log.msg("Setting document to 'skipped' state.")
                document.state = 'skipped'
                log.msg("Setting document process to 'document_finish'...")
                document.current_process = 'document_finish'
                document.finished = datetime.today()
                document.commit()

            if document.workflow_process == 'delete':
                # DOCUMENT DELETING FOR DOCUMENTS WITH WORKFLOW PROCESS SET TO DELETE #
                log.msg("WORKFLOW_BATCH_PROCESSING: Trying to start workflow_doc_delete for document", document.doc_id)
                try:
                    state = self.wf_doc_delete.run(document)
                    document.state = state
                    document.commit()
                except Exception as e:
                    log.msg(e)
                    document.state = 'failed'
                    document.errors.append(e)
                    document.error = str(e)
                    document.finished = datetime.today()
                    # batch.batch_finished_date = datetime.today()
                    document.commit()

            if document.workflow_process != 'delete':
                # DOCUMENT PACKAGING FOR DOCUMENTS WITH WORKFLOW PROCESS SET TO INSERT OR UPDATE #
                log.msg("WORKFLOW_BATCH_PROCESSING: Trying to start workflow_doc_package for document", document.doc_id)
                if document.current_process == 'new':
                    try:
                        state = self.wf_doc_package.run(document)
                        document.state = state
                        document.commit()
                    except Exception as e:
                        log.msg(e)
                        document.state = 'failed'
                        document.errors.append(e)
                        document.error = str(e)
                        document.finished = datetime.today()
                        # batch.batch_finished_date = datetime.today()
                        document.commit()

                if document.current_process == 'import':
                    try:
                        state = self.wf_doc_import.run(document)
                        document.state = state
                        document.commit()
                    except Exception as e:
                        log.msg(e)
                        document.state = 'failed'
                        document.errors.append(e)
                        document.error = str(e)
                        document.finished = datetime.today()
                        # batch.batch_finished_date = datetime.today()
                        document.commit()

                if document.current_process == 'ingest':
                    try:
                        state = self.wf_doc_ingest.run(document)
                        document.state = state
                        document.commit()
                    except Exception as e:
                        log.msg(e)
                        document.state = 'failed'
                        document.error = str(e)
                        document.errors.append(e)
                        document.finished = datetime.today()
                        document.commit()

            # if document.current_process == 'document_finish':
            # run document finish workflow  on any document, regardless the documents' state
            try:
                state = self.wf_doc_finish.run(document)
                document.state = state
                document.commit()
            except Exception as e:
                log.msg(e)
                document.state = 'failed'
                document.errors.append(e)
                document.error = str(e)
                document.finished = datetime.today()
                document.commit()

        return "finished_processing"
