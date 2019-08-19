#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
from urllib.parse import urljoin
from twisted.python import log
from datetime import datetime
from time import sleep


class workflow_doc_setup(object):

    def __init__(self, db_int, db_sis, config, sftp, scp, dspace_api_key):
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.sftp = sftp
        self.scp = scp
        self.dspace_api_key = dspace_api_key

    def run(self, document):

        if document.state == 'planned':

            try:
                wf_process = self.determine_wf_process(document)
                log.msg("Document:", document.doc_id, "Workflow process:", wf_process)
                document.commit()
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

            try:
                aleph_sysno = self.store_aleph_sysno(document)
                log.msg("Document:", document.doc_id, "Aleph returned SYSNO:", aleph_sysno)
                document.commit()
                log.msg("Document:", document.doc_id, "Aleph DB SYSNO:", document.aleph_id)
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

            try:
                work_type = self.store_document_type(document)
                log.msg("Document:", document.doc_id, "WORK TYPE FROM RECORD:", work_type)
                document.commit()
                log.msg("Document:", document.doc_id, "WORK TYPE FROM DB:", document.work_type)
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

            try:
                availability = self.store_work_availability(document)
                log.msg("Document:", document.doc_id, "WORK AVAILABILITY FROM RECORD:", availability)
                log.msg("Document:", document.doc_id, "WORK AVAILABILITY FROM OBJECT:", document.work_avalability)
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

            # TODO: Check if document has package in document_errors folder - if so, check if it's complete. If so,
            # TODO: skip right to document import, updating the document record in database beforehand.
            # TODO: Skipping to import means:
            # TODO:     -> moving complete folder to document.out_dir
            # TODO:     -> setting document.current_process to 'import'

            try:
                state = self.start_document_processing(document)
                document.state = state
                document.commit()
            except Exception as e:
                log.msg(e)
                document.errors.append(e)
                document.error = str(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        return document.state

    def start_document_processing(self, doc):
        """
        Tries to create a document output directory if it doesn't exist and sets an output path to it
        or sets the document output directory path to be a path to already existing directory. Raises an exception if
        output directory cannot be created or set to an existing one.
        :param doc: document object
        :return: string('stated'): string representing new state of the document
        """
        try:
            # try to create document directory in the document root working directory
            if not os.path.exists(doc.out_dir):
                os.makedirs(doc.out_dir)
            else:
                log.msg("Directory", doc.out_dir, "already exists...")
                pass
        except:
            raise Exception("Failed to create document output directory.")

        return 'started'

    def store_aleph_sysno(self, doc):

        try:
            if doc.record_object['001'] is None:
                doc.aleph_id = None
                return None
            else:
                doc.aleph_id = doc.record_object['001'].data
            return doc.record_object['001'].data
        except Exception as e:
            raise e

    def store_document_type(self, doc):

        try:
            if doc.record_object['ds_workType'] is None:
                doc.work_type = None
                return None
            else:
                doc.work_type = doc.record_object['ds_workType'].data
            return doc.record_object['ds_workType'].data
        except Exception as e:
            raise e

    def store_work_availability(self, doc):

        try:
            # THIS SHOULD NOT CHECK FOR DOCUMENT AVAILABILITY IN RECORDS OF DOCUMENTS
            # THAT ARE MEANT TO BE DELETED
            if doc.record_direction == 'delete':
                return None

            if doc.record_object['ds_work_availability'] is None:
                raise Exception("META PROTO: Field ds_work_availability not present in a record!")

            availability_code = doc.record_object['ds_work_availability'].data

            log.msg("WORK AVAILABILITY CODE:", availability_code)

            if availability_code is None:
                raise Exception("META PROTO: Work availability code not found in ds_work_availability field.")

            doc.work_availability = availability_code
            return availability_code

        except Exception as e:
            raise e

    def determine_wf_process(self, doc):
        # FIXME: This should probably be a method of a document object?
        # FIXME: USE DSPACE API!!!
        # get record direction, check if document was processed before (using document or document_audit table?)
        # and determine, what is the 'correct' process in which a document enters a workflow
        # (insert, update, delete, None - document won't be processed at all)

        def get_right_process(curr_doc, found_doc=None):

            log.msg("get_right_process - FOUND DOC: ", found_doc)
            if found_doc is None:
                if curr_doc.record_direction not in ['insert', 'update', 'delete']:
                    raise Exception('Unknown direction process ' + curr_doc.record_direction)

                # document was not found in database, therefore, there is no previous process
                if curr_doc.record_direction == 'delete':
                    return None
                if curr_doc.record_direction == 'update' or curr_doc.record_direction == 'insert':
                    return 'insert'

            else:
                # we found, that document was processed before
                if found_doc.handle is None:
                    log.msg("get_right_process - FOUND DOC DOES NOT HAVE A HANDLE: ", found_doc.handle)
                    # we cannot check status of the document if it has no handle
                    log.msg("Document doesn't have a handle in database. We cannot check if it's in DSpace.")
                    if found_doc.direction_process == curr_doc.record_direction:
                        log.msg("Current document's direction: {}, \n",
                                "Found document's direction {}".format(curr_doc.record_direction,
                                                                       found_doc.direction_process))
                        if curr_doc.record_direction == 'delete':
                            log.msg("Setting document direction to 'None'")
                            return None

                        log.msg("Setting document direction to 'insert'...")
                        return 'insert'
                    else:
                        log.msg("Current documents direction: {}, \n"
                                "Found document direction {}".format(curr_doc.record_direction,
                                                                     found_doc.direction_process))
                        log.msg("Setting document direction to 'insert'...")
                        return 'insert'
                else:
                    log.msg("get_right_process - FOUND DOC HAS HANDLE: ", found_doc.handle)
                    log.msg("get_right_process - Current documents direction: {}".format(curr_doc.record_direction))
                    if curr_doc.document_in_dspace(handle=found_doc.handle) is True:
                        log.msg("get_right_process - document in DSpace: True")
                        if curr_doc.record_direction == 'insert':
                            log.msg("get_right_process - RIGHT PROCESS: 'update'")
                            return 'update'
                        elif curr_doc.record_direction == 'update':
                            log.msg("get_right_process - RIGHT PROCESS: 'update'")
                            return 'update'
                        elif curr_doc.record_direction == 'delete':
                            log.msg("get_right_process - RIGHT PROCESS: 'delete'")
                            return 'delete'
                        else:
                            raise Exception('Unknown current doc record direction ' + curr_doc.record_direction)
                    else:
                        log.msg("get_right_process - document in DSpace: False")
                        if curr_doc.record_direction == 'insert':
                            log.msg("get_right_process - RIGHT PROCESS: 'insert'")
                            return 'insert'
                        elif curr_doc.record_direction == 'update':
                            log.msg("Current doc has an 'update' directiron - checking form document in DSpace again.")
                            if curr_doc.document_in_dspace(handle=found_doc.handle) is True:
                                log.msg("get_right_process - RIGHT PROCESS: 'update'")
                                return 'update'
                            else:
                                return 'insert'
                        elif curr_doc.record_direction == 'delete':
                            log.msg("get_right_process - RIGHT PROCESS: 'None'")
                            return None
                        else:
                            raise Exception('Unknown current doc record direction ' + curr_doc.record_direction)

        # GET THE LAST DOCUMENT DIRECTION FIRST #
        # document is searched in document_audit table #
        last_processed_doc = self.db_int.document_audit.filter_by(did=doc.doc_id).order_by(
            self.db_int.document_audit.finished.desc()).first()

        workflow_process = None
        if last_processed_doc is None:
            # there is no processed doc with this did in database, document was not processed before
            workflow_process = get_right_process(curr_doc=doc, found_doc=None)
            doc.workflow_process = workflow_process
        else:
            workflow_process = get_right_process(curr_doc=doc, found_doc=last_processed_doc)
            doc.workflow_process = workflow_process

        if doc.workflow_process not in [None, 'insert', 'update', 'delete']:
            raise Exception('Failed to determine a workflow process for document.')

        return doc.workflow_process
