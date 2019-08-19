#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.python import log
from sqlalchemy import and_
from datetime import datetime
from balikator.items.document import Document
from xml.sax.saxutils import escape
import pymarc
import os
import re


class workflow_batch_setup(object):

    def __init__(self, db_int, db_sis, config, utility, sftp, scp):
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.utility = utility
        self.sftp = sftp
        self.scp = scp

    def run(self, batch):
        if batch.batch_process == 'new':
            # TODO: Create method that will go through whole batch and escape all invalid XML characters: &, <, >, etc.
            # TODO: in the MARC fields. This has to be done prior to actual batch parsing done by pymarc module
            try:
                done = self.escape_batch_file(batch)
                log.msg("Batch escape done:", done)
            except Exception as e:
                log.msg("BATCH ESCAPE ERROR:")
                log.msg(e)
                batch.errors.append(str(e))
                batch.error = str(e)
                batch.batch_state = 'failed'
                batch.batch_finished_date = datetime.today()
                batch.commit()

            try:
                finished_process = self.parse_batch_file(batch)
                batch.batch_process = finished_process
                batch.commit()
            except Exception as e:
                batch.errors.append(str(e))
                batch.error = str(e)
                batch.batch_state = 'failed'
                batch.batch_finished_date = datetime.today()
                batch.commit()

        if batch.batch_process == 'record_parsing':
            try:
                finished_process = self.create_doc_objects(batch)
                batch.batch_process = finished_process
                batch.commit()
            except Exception as e:
                batch.errors.append(str(e))
                batch.error = str(e)
                batch.batch_state = 'failed'
                batch.batch_finished_date = datetime.today()
                batch.commit()

        if batch.batch_process == 'doc_creation':
            try:
                finished_process = self.docs_to_db(batch)
                batch.batch_process = finished_process
                batch.commit()
            except Exception as e:
                batch.errors.append(str(e))
                batch.error = str(e)
                batch.batch_state = 'failed'
                batch.batch_finished_date = datetime.today()
                batch.commit()

        if batch.batch_process == 'doc_database':
            try:
                state = self.create_batch_folders(batch)
                batch.batch_state = state
                batch.batch_process = 'doc_setup'
                batch.commit()
            except Exception as e:
                batch.errors.append(str(e))
                batch.error = str(e)
                batch.batch_state = 'failed'
                batch.batch_finished_date = datetime.today()
                batch.commit()

        return batch.batch_state

    def escape_batch_file(self, batch):
        """
        Method gets a path to XML file of a batch, parses each line from batch file and escapes XML-invalid charaters
        from element contents. Escaped string is imediately written to a temporary batch file. After every line
        is escaped, batch file is deleted and temporary file is renamed to match the original batch file name.
        :param batch: batch object
        :return: path to a newly created batch file
        """

        xml_orig = batch.get_batch_file()
        xml_preprocessed = os.path.join(self.config.get('batch', 'work_input_path'),
                                        'preprocessed.xml')
        # open xml_preprocessed file
        new_file = open(xml_preprocessed, 'w', encoding='utf-8')
        log.msg("Escaping XML-invalid characters in batch file", xml_orig)
        with open(xml_orig, 'r') as orig_file:
            for line in orig_file:
                subf_match = re.search('(<subfield .*>)(.*)(</subfield>)', line)
                controlf_match = re.search('(<controlfield .*>)(.*)(</controlfield>)', line)

                if subf_match:
                    content = subf_match.group(2)
                    # escape all XML-invalid character from element's content
                    content_parsed = escape(content, {"\"": "&quot;", "\'": "&apos;", "<": "&lt;", ">": "&gt;",
                                                      "&lt;": "&lt;", "&gt;": "&gt;"})
                    line = subf_match.group(1) + content_parsed + subf_match.group(3)

                elif controlf_match:
                    content = controlf_match.group(2)
                    # escape all XML-invalid character from element's content
                    content_parsed = escape(content, {"\"": "&quot;", "\'": "&apos;", "<": "&lt;", ">": "&gt;",
                                                      "&lt;": "&lt;", "&gt;": "&gt;"})
                    line = controlf_match.group(1) + content_parsed + controlf_match.group(3)

                else:
                    line = line

                new_file.write(line + "\n")

        # close xml_preprocessed file and orig_file
        new_file.close()
        orig_file.close()

        log.msg("Removing original batch file:", xml_orig)
        # remove original file
        os.remove(xml_orig)

        log.msg("Renaming preprocessed file:", xml_preprocessed, "to:", xml_orig)
        # rename xml_preprocessed file to xml_orig file
        os.rename(src=xml_preprocessed, dst=xml_orig)

        return True

    def parse_batch_file(self, batch):
        """
        Method gets a path to XML file of a batch and parses all records from batch file.
        :param batch: batch object
        :return: 'record_parsing' - finished process description (name)
        """
        # parses XML file
        # file should be located somewhere on the batch_path and should be named according to batch_id (folder name)

        xml_file = batch.get_batch_file()

        log.msg("WORKFLOW BATCH: parse_batch_file - batch file location:", xml_file)
        try:
            record_data = pymarc.parse_xml_to_array(xml_file=xml_file, strict=False)
            batch.batch_record_data = record_data
        except Exception as e:
            log.msg(e)
            log.msg('Failed to parse MARC XML to array')
            raise Exception("Failed to parse MARC XML to array")

        return 'record_parsing'

    def create_doc_objects(self, batch):
        """
        Method creates document object for every record parsed from batch file and stores the reference to created
        document object in an array in batch object. If there are no parsed records stored in batch object, method
        raises an Exception.
        :param batch: batch object
        :return: 'doc_creation' - finished process identification
        """
        # create a doc object for each record in batch_record_data array, where records from batch are stored

        if batch.batch_record_data is None:
            raise Exception("Batch has no record data.")

        log.msg("CREATE DOC OBJECTS: batch_old_batch_uuid:", batch.old_batch_uuid)
        record_no = 1
        for record in batch.batch_record_data:
            record_no += 1
            d_id = record['repId'].data
            # direction = str(record['func'].data)
            doc_kind = 'theses'
            last_processed_doc = self.db_int.document_audit.filter_by(did=d_id).order_by(
                self.db_int.document_audit.finished.desc()).first()

            where = and_(self.db_int.document.batch_uuid == str(batch.old_batch_uuid),
                         self.db_int.document.did == d_id)
            # if we should process only failed documents, skip all that not failed
            if batch.only_failed_docs:
                failed_document = self.db_int.document.filter(where).first()
                if failed_document is None:
                    log.msg("CREATE DOC OBJECTS: doc_did", d_id, "not in db for batch", batch.old_batch_uuid, ".")
                    continue

                if self.db_int.document.filter(where).one().state == 'failed':
                    log.msg("CREATE DOC OBJECTS: doc_did", d_id)
                    document = Document(doc_id=d_id, batch_uuid=str(batch.batch_uuid), doc_kind=doc_kind,
                                        record_object=record, db_int=self.db_int, config=self.config,
                                        utility=self.utility)
                    document.last_processed = last_processed_doc  # set a reference to last processed document or to None
                    batch.doc_objects_list.append(document)
                else:
                    # ignore files from batch, that are not failed
                    continue

            if batch.only_failed_docs is False:
                log.msg("CREATE DOC OBJECTS: batch should be processed as a whole.")
                # create document object
                document = Document(doc_id=d_id, batch_uuid=str(batch.batch_uuid), doc_kind=doc_kind,
                                    record_object=record, db_int=self.db_int, config=self.config, utility=self.utility)
                document.last_processed = last_processed_doc  # set a reference to last processed document or to None
                batch.doc_objects_list.append(document)

        if len(batch.doc_objects_list) == 0:
            log.err('No document objects were created')
            raise Exception('No document objects were created')

        return 'doc_creation'

    def docs_to_db(self, batch):
        """
        Method inserts information from created document objects to the internal database. In case there are
        no document objects stored in a batch object, it raises an Exception. Otherwise, for every created document
        object, information is extracted from it and either inserted into the internal database or used to update
        an existing already processed document. If document already present in the internal database an is not finished,
        method inserts an error to the internal database to table errors_document.
        :param batch: batch_object
        :return: 'doc_database' - finished process indication
        """
        for document in batch.doc_objects_list:
            doc_db = self.db_int.document.filter_by(did=document.doc_id).first()
            if doc_db is None:
                log.msg("WORKFLOW_BATCH - docs_to_db: Document", document.doc_id, "is not in the 'document' table.")
                log.msg("WORKFLOW_BATCH - docs_to_db: Inserting document", document.doc_id, "to 'document' table.")
                document.insert(state='planned')
                # insert did to handle table. This is new document, so it has no handle created, insert NULL instead.
                document.insert_to_handle_tab(handle=None)
            else:
                log.msg("WORKFLOW_BATCH - docs_to_db: Document", document.doc_id, "found in 'document' table.")
                if doc_db.state == 'planned' or doc_db.state == 'started':
                    # document is in db but is 'planned' or 'started'
                    log.msg('Document', document.doc_id, "is still in processing.")
                    msg = "Document is being processed. Failed to start processing."
                    # # log document error into the db table "errors_document", add document to docs_error list (maybe?)
                    document.error = msg
                else:
                    # document is in db, but is either 'finished' or 'failed' - new processing
                    # update document in db table "document"
                    log.msg('Document', document.doc_id, 'is not in processing.')
                    log.msg("WORKFLOW_BATCH - docs_to_db: Updating document", document.doc_id, "in 'document' table.")
                    document.update(state='planned', process='new', c_time=datetime.today(), f_time=None)

        return 'doc_database'

    def create_batch_folders(self, batch):

        # create batch import directory, store it in batch property
        def create_import_folder():
            if self.config.getboolean('import', 'is_remote') is True:
                self.utility.create_dir_remote(remote_directory=batch.import_folder, sftp=self.sftp)
            else:
                self.utility.create_dir_local(local_path=batch.import_folder)

            return batch.import_folder

        # create batch error folder, store it in batch property
        def create_errors_folder():
            if self.config.getboolean('document_errors', 'is_remote') is True:
                self.utility.create_dir_remote(remote_directory=batch.errors_folder, sftp=self.sftp)
            else:
                self.utility.create_dir_local(local_path=batch.errors_folder)

            return batch.errors_folder

        try:
            import_folder = create_import_folder()
            log.msg('Import folder', import_folder, 'created.')
        except Exception as e:
            log.msg(e)
            log.msg('Failed to create import folder', batch.import_folder)
            raise e

        try:
            errors_folder = create_errors_folder()
            log.msg('Errors folder', errors_folder, 'created.')
        except Exception as e:
            log.msg(e)
            log.msg('Failed to create errors folder', batch.errors_folder)
            raise e

        return 'started'
