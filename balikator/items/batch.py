#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from sqlalchemy import and_


class Batch(object):
    """
    Class responsible for batch handling.
    """

    def __init__(self, config, db_int, uuid, batch_file_path, only_failed_docs=False):
        """
        Batch constructor. Creates a batch object. Accepts two parameters, instance o configuration file and
        string representing batch id.
        :param config: configuration file - parsed configuration file stored in configParser object
        :param db_int: internal database connection
        :param uuid: batch uuid
        :param batch_file_path: path to a batch XML file
        :param only_failed_docs: bool indicating whether we want to process only failed documents in this batch
        """
        self.config = config
        self.db_int = db_int
        self.only_failed_docs = only_failed_docs
        self.batch_file_path = batch_file_path  # file representing a batch and its contents
        self.uuid = uuid
        self.old_uuid = None
        self.batch_file_name = os.path.basename(batch_file_path)
        # construct a batch output path - based on config setting and uuid of the batch
        self.output_path = os.path.join(self.config.get('balikator', 'output_path'), str(self.batch_uuid))
        self.import_folder_path = os.path.join(self.config.get('import', 'folder'), str(self.batch_uuid))
        self.errors_folder_path = os.path.join(self.config.get('document_errors', 'path'), str(self.batch_uuid))
        self.batch_doc_output_paths = None  # dict of document id -> document output path mapping
        self.record_data = None     # array holding individual record objects parsed from batch MARC XML file
        self.errors = []  # dictionary of errors in the batch
        self.contents_status = None
        self.docs_process = []  # list of document objects that will be processed withing a batch

        self.docs_skip = []  # list of document objects that will be skipped in processing
        self.doc_objects_list = []  # list of document objects in the batch
        self.doc_errors = []
        self.previously_processed = None    # set to True if batch with the same name has been processed previously,
                                            # else set to False
        self.aleph_mapfile_path = None

    def docs_with_state(self, state):
        where = and_(self.db_int.document.batch_uuid == str(self.batch_uuid),
                     self.db_int.document.state == state)
        documents = self.db_int.document.filter(where).all()
        return documents

    def docs_with_state_process(self, state, process):
        where = and_(self.db_int.document.batch_uuid == str(self.batch_uuid),
                     self.db_int.document.state == state,
                     self.db_int.document.workflow_process == process)
        documents = self.db_int.document.filter(where).all()
        return documents

    @property
    def aleph_mapfile(self):
        return self.aleph_mapfile_path

    @aleph_mapfile.setter
    def aleph_mapfile(self, value):
        self.aleph_mapfile_path = value

    @property
    def batch_docs_db(self):
        return self.db_int.document.filter_by(batch_uuid=str(self.batch_uuid)).all()

    @property
    def old_batch_uuid(self):
        return self.old_uuid

    @old_batch_uuid.setter
    def old_batch_uuid(self, value):
        self.old_uuid = value

    @property
    def batch_uuid(self):
        return self.uuid

    @property
    def batch_started_date(self):
        return self.db_int.batch.filter_by(uuid=str(self.batch_uuid)).first().created

    @property
    def batch_finished_date(self):
        return self.db_int.batch.filter_by(uuid=str(self.batch_uuid)).first().finished

    @batch_finished_date.setter
    def batch_finished_date(self, date_time):
        self.db_int.batch.filter_by(uuid=str(self.batch_uuid)).first().finished = date_time

    @property
    def batch_obj(self):
        return self.db_int.batch.filter_by(uuid=str(self.batch_uuid)).first()     # batch object from internal DB

    @property
    def batch_state(self):
        return self.db_int.batch.filter_by(uuid=str(self.batch_uuid)).first().state

    @batch_state.setter
    def batch_state(self, value):
        self.db_int.batch.filter_by(uuid=str(self.batch_uuid)).first().state = value

    @property
    def batch_process(self):
        return self.db_int.batch.filter_by(uuid=str(self.batch_uuid)).first().batch_process

    @batch_process.setter
    def batch_process(self, value):
        self.db_int.batch.filter_by(uuid=str(self.batch_uuid)).first().batch_process = value

    def get_batch_file(self):
        return self.batch_file_path

    @property
    def batch_record_data(self):
        return self.record_data

    @batch_record_data.setter
    def batch_record_data(self, value):
        self.record_data = value

    @property
    def doc_objects(self):
        """
        Getter for doc_objects_list. Gets a list of document objects in the batch.
        :return: doc_objects_list - list of document objects in the batch
        """
        return self.doc_objects_list

    @property
    def get_batch_out_path(self):
        """
        Getter for output_path. Gets a path to the batch 'output' directory.
        :return: output_path - string representing a path to batch 'output' directory
        """
        return self.output_path

    @property
    def import_folder(self):
        """
        Getter for import_folder_path. Gets a path to batch 'import' folder.
        :return: import_folder_path - string representing a path to batch 'import' folder
        """
        return self.import_folder_path

    @property
    def errors_folder(self):
        """
        Getter form errors_folder_path. Gets a path to batch 'document errors' folder. This is a folder in which all
        failed documents in this bath will be stored.
        :return: errors_folder_path: string representing a path to batch 'document errors' folder
        """
        return self.errors_folder_path

    @property
    def doc_out_paths(self):
        """
        Getter for batch_doc_output_paths. Gets a dict with mapped document output paths and document ids belonging
        to batch.
        :return: batch_doc_output_paths - dict with mapped document output paths and document ids
        """
        return self.batch_doc_output_paths

    @doc_out_paths.setter
    def doc_out_paths(self, value):
        """
        Sets a dict as value of batch_doc_output_paths.
        :param value: dict containing mapped document output paths and document ids
        :return: None
        """
        self.batch_doc_output_paths = value

    @property
    def error(self):
        return self.db_int.errors_batch.filter_by(batch_uuid=str(self.batch_uuid)).first()

    @error.setter
    def error(self, value):
        self.db_int.errors_batch.insert(batch_uuid=str(self.batch_uuid), error_message=value)

    def commit(self):
        self.db_int.commit()