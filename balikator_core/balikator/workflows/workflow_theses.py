#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.python import log
from balikator.workflows.workflow_batch import workflow_batch
from balikator.items.batch import Batch
from balikator.utility.utils import utility
from balikator.reports import log_info
from sqlalchemy import exc
import os
import re
import uuid
import requests
from datetime import datetime
import shutil


# __all__ = ['WorkflowTheses']


class workflow_theses(object):

    __all__ = ['WorkflowTheses']

    def __init__(self, db_int, db_sis, db_dspace, config):
        self.db_int = db_int
        self.db_sis = db_sis
        self.db_dspace = db_dspace
        self.config = config
        self.utility = utility(self.config)
        self.workflow = self.db_int.workflow.filter_by(id=self.config.get('workflow_theses', 'id')).first()
        self.errors_tab = self.db_int.errors_workflow
        self.setup_batches_list = list()
        self.batches_processing = list()
        self.batches_ok = list()
        self.batches_errors = list()
        self.batches_failed = list()
        self.ssh = None
        self.scp = None
        self.sftp = None
        self.dspace_api_key = None
        self.workflow_batch = None

    @property
    def id(self):
        return self.workflow.id

    @property
    def name(self):
        return self.workflow.name

    @property
    def state(self):
        return self.workflow.state

    @state.setter
    def state(self, value):
        self.workflow.state = value

    @property
    def started(self):
        return self.workflow.started

    @started.setter
    def started(self, value):
        self.workflow.started = value

    @property
    def stopped(self):
        return self.workflow.stopped

    @stopped.setter
    def stopped(self, value):
        self.workflow.stopped = value

    @property
    def error(self):
        return self.errors_tab.all()

    @error.setter
    def error(self, value):
        self.errors_tab.insert(workflow_id=int(self.config.get('workflow_theses', 'id')),
                               name=self.config.get('workflow_theses', 'name'),
                               error_message=value)

    def store_connections(self, ssh, scp, sftp):
        log.msg("STORE CONNECTIONS:")
        log.msg("SSH:", self.ssh, "SCP:", self.scp, "SFTP:", self.sftp)
        self.ssh = ssh
        self.scp = scp
        self.sftp = sftp
        log.msg("STORE CONNECTIONS - AFTER STORING:")
        log.msg("SSH:", self.ssh, "SCP:", self.scp, "SFTP:", self.sftp)

    def try_reconnect_sis(self, db_sis):
        # NOTE: OH MY GOD THIS WORKS!
        try:
            # suppose the database has been restarted.
            db_sis.execute("SELECT * FROM batch LIMIT 1")
            db_sis.close()
        except exc.DBAPIError as e:
            # an exception is raised, Connection is invalidated.
            if e.connection_invalidated:
                log.msg("Connection was invalidated!")
                try:
                    db_sis.rollback()
                except:
                    raise Exception('Connection to SIS DB lost and reconnect failed.')

    def try_reconnect_dspace(self, db_dspace):
        log.msg("Reconnecting to reconnect to DSpace DB...")
        try:
            log.msg("Trying test SELECT...")
            db_dspace.execute("SELECT * from handle LIMIT 1")
            #db_dspace.close()
        except exc.DBAPIError as e:
            log.msg('DBAPI Error when trying to recconect to DSpace DB...')
            log.msg(e)
            if e.connection_invalidated:
                log.msg("Connection to DSpace database was invalidated!")
                try:
                    log.msg("Trying rollback.")
                    db_dspace.rollback()
                except:
                    raise Exception('Connection to DSpace DB lost and reconnect failed.')
            else:
                log.msg(e)
                raise e
        except Exception as e:
            log.msg('Another type of exception occured...')
            log.msg(e)

    def initialize_workflows(self):

        # TODO: create workflow for batch running
        self.workflow_batch = workflow_batch(self.db_int, self.db_sis, self.db_dspace, self.config, self.utility, self.ssh, self.sftp,
                                             self.scp, self.dspace_api_key)

    def run(self, ssh, scp, sftp):
        log.msg("WORKFLOW THESES RUN:")
        log.msg("SSH:", self.ssh, "SCP:", self.scp, "SFTP:", self.sftp)
        # store connection information if there is any
        self.store_connections(ssh, scp, sftp)

        # login to DSpace API
        try:
            log.msg("Trying to login to DSpace API...")
            self.dspace_api_key = self.login_dspace_api()
        except Exception as e:
            log.msg(e)
            self.error = str(e)
            self.state = 'failed'
            self.db_int.commit()

        try:
            log.msg("Trying to reconnect to SIS DB...")
            self.try_reconnect_sis(db_sis=self.db_sis)
        except exc.DisconnectionError as e:
            log.msg(e)
            log.msg("SIS DB ERROR")
            self.error = 'Failed to reconnect to SIS database.'
            self.state = 'failed'
            self.db_int.commit()

        try:
            log.msg("Trying to reconnect to DSpace DB...")
            self.try_reconnect_dspace(db_dspace=self.db_dspace)
            log.msg("Reconnecting finished...")
        except exc.DisconnectionError as e:
            log.msg(e)
            log.msg("DSpace DB ERROR")
            self.error = 'Failed to reconnect to DSpace database.'
            self.state = 'failed'
            self.db_int.commit()

        # initialize workflows
        log.msg("Initializing workflows...")
        self.initialize_workflows()

        # clean up batches list at the beginning of the batch processing
        self.batches_processing = list()
        self.setup_batches_list = list()

        try:
            log.msg("Fetching batch files...")
            batch_files = self.fetch_batch_files()
        except Exception as e:
            raise e

        try:
            self.setup_batches(batch_files=batch_files)
        except Exception as e:
            log.msg(e)
            raise e

        log.msg("Number of batch files:", len(batch_files))
        log.msg("Batches set up:", len(self.setup_batches_list), "of", len(batch_files))
        i = 1

        for batch in self.setup_batches_list:
            log.msg("Processing batch", i, "from", len(self.setup_batches_list))
            # For every batch, run a workflow_batch.run() method, which runs different parts of the batch workflow
            # depending on the state of the batch.

            # Store batch in batch_processing list to evaluate the whole workflow after they are processed
            self.batches_processing.append(batch)

            # run workflow_batch.run() method and gather the output
            try:
                batch_state = self.workflow_batch.run(batch)
                log.msg("Current batch state:", batch_state)
                batch.batch_finished_date = datetime.today()
                batch.commit()
            except Exception as e:
                log.msg(e)
                batch.batch_state = 'failed'
                batch.batch_finished_date = datetime.today()
                batch.commit()
                raise e

            i += 1

        # TODO: Create a report file for every batch containing information about:
        # TODO:     batch state
        # TODO:     number of correctly finished documents (with all states - insert, update, delete)
        # TODO:     number of failed documents (with all states - insert, update, delete)
        # TODO:     number of skipped documents (with all states - insert, update, delete)

        # when all batches are processed, end the Theses workflow
        try:
            self.finish_workflow()
            self.db_int.commit()
        except Exception as e:
            log.msg(e)
            raise e

        return self.state

    def login_dspace_api(self):
        # http://stackoverflow.com/questions/32585800/convert-curl-request-to-python-requests-request
        # OR MAYBE http://stackoverflow.com/questions/25491090/how-to-use-python-to-execute-a-curl-command

        headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
        admin_mail=self.config.get('dspace','admin_mail')
        admin_pass=self.config.get('admin','password')
        ds_base_url = self.config.get('dspace','base_url')
        data = '{"email":"'+admin_mail+'", "password":"'+admin_pass+'"}'
        url = str(ds_base_url) + '/rest/login'
        r = requests.post(url, data=data, headers=headers)

        # FIXME: Try: if r.ok: 
        # source: https://stackoverflow.com/questions/47144606/requests-how-to-tell-if-youre-getting-a-success-message
        if r.ok:
            return r.text
        else:
            raise Exception('Failed to login to DSpace API')

    def fetch_batch_files(self):
        """
        Fetches batch file/files from batch input folder to batch working folder. If there are no batch files in input
        folder, return empty list.
        :return: list of batch file paths
        """

        def get_input_f_contents():
            """
            Gets all batch files from batch input folder (local or remote).
            :return:
            """
            batch_files = [os.path.join(input_dir_path, b_file)
                           for b_file in self.utility.listdir(input_dir_path, is_remote, sftp_client=self.sftp) if
                           b_file.endswith('.xml') and re.match(self.config.get('balikator', 'batch_name_pattern'),
                                                                b_file)]

            # Sort the list of files alphabeticaly
            batch_files = sorted(batch_files)
            log.msg("Sorted batches:\n{}".format(batch_files))
            
            return batch_files

        def create_work_path():
            """
            Creates path to batch file in working folder.
            :return: w_path: path to batch file in working folder
            """
            name = os.path.basename(file_path)
            return os.path.join(self.config.get('batch', 'work_input_path'), name)

        def b_files_to_workfolder(pth, remote=False):
            """
            Copies batch file from input folder to working folder
            :param pth: new path to batch file in working folder
            :param remote: True if copying from remote to local, False if copying from local to local
            :return: path to the copied file in working folder
            """
            log.msg("Copying file", file_path, "to working folder", pth, "...")
            if remote is True:
                self.scp.get(remote_path=file_path, local_path=pth)
            else:
                shutil.copy(src=file_path, dst=pth)

            return pth

        log.msg("\n\nFETCHING BATCHES FROM INPUT FOLDER:")

        batch_files_work = list()
        input_dir_path = self.config.get('batch', 'input_path')
        is_remote = self.config.getboolean('batch', 'input_is_remote')

        if self.utility.folder_exists(input_dir_path, is_remote, self.sftp) is False:
            raise Exception("Input directory doesn't exist.")

        # get batch input folder contents
        b_files = get_input_f_contents()

        if len(b_files) == 0:
            # there are no batch files to fetch, return empty list
            log.msg("There are no batch files to process.")
            return b_files

        for file_path in b_files:
            batch_in_db = self.batch_in_db(batch_name=os.path.basename(file_path))

            # skip batch files that belong to previously processed batches, that finished with state 'finished'
            if batch_in_db is not None and batch_in_db.state == 'finished':
                log.msg("This batch has already been processed with final state:", batch_in_db.state,
                        "Won't copy it to working folder again.")
            else:
                # copy batch files of batches that were not finished with state 'finished' or not processed at all
                try:
                    w_path = b_files_to_workfolder(pth=create_work_path(), remote=is_remote)
                    batch_files_work.append(w_path)
                except Exception as e:
                    log.msg(e)
                    raise Exception('Failed to copy batch file from batch input folder to batch working folder...')

        return batch_files_work

    def setup_batches(self, batch_files):
        """
        Method sets up batch for processing  for each batch file in input directory, if the batch file can be processed.
        Set up batches are appended to the list of batches scheduled for processing.
        :param batch_files: list of batch files in the input directory
        :return: None
        """

        def can_process_batch(batch_db_obj):
            """
            Returns True if batch is finished with errors or failed and can be processed again withing the workflow.
            Returns False if batch is finished, planned or started.
            :param batch_db_obj: batch object from the internal database
            :return: bool: True if batch can be processed, False if it cannot be processed
            """
            can_process = False
            if batch_db_obj.state == 'finished':
                log.msg("Batch", os.path.basename(b_path), "in the database:", "status:", batch_db.state)
            elif batch_db_obj.state == 'finished with errors':
                log.msg("Batch", os.path.basename(b_path), "is in the database but finished with errors.")
                log.msg("Processing failed documents from batch", os.path.basename(b_path), "in a new batch...")
                can_process = True
            elif batch_db_obj.state == 'failed':
                log.msg("Batch", os.path.basename(b_path), "is in the database but failed.")
                log.msg("Processing batch as a new one.")
                can_process = True
            else:
                log.msg("Batch", os.path.basename(b_path), "is in the database:", "status:", batch_db.state)

            return can_process

        def process_only_failed_docs(batch_obj):
            """
            # Checks state of batch in database. I batch state is finished with errors, it checks if there are some
            # failed documents in this batch. If not, it means that batch should be processed from scratch
            # (every document in batch should be processed). Otherwise, only failed documents should be processed.
            Returns True if anly failed documents from batch should be processed, returns False otherwise.
            :param batch_obj: instance of batch class
            :return: bool(True/False)
            """
            if batch_obj.state == 'finished with errors':
                return True
            # elif batch_obj.state == 'finished with errors' and
            elif batch_obj.state == 'failed':
                return False

        def construct_batch(batch_path, existing_batch=None):
            """
            Creates batch object.
            :param batch_path:
            :param existing_batch:
            :return:
            """
            batch_uuid = uuid.uuid4()

            if existing_batch is None:
                batch_obj = Batch(config=self.config, db_int=self.db_int, uuid=batch_uuid, batch_file_path=batch_path)
            else:
                batch_obj = Batch(config=self.config, db_int=self.db_int, uuid=batch_uuid, batch_file_path=batch_path,
                                  only_failed_docs=process_only_failed_docs(batch_obj=existing_batch))
            return batch_obj

        def create_batch_object(batch_db_obj):
            """

            :param batch_db_obj:
            :return:
            """
            # create new batch object and insert it to database
            log.msg("Previous batch with the same name", batch_db_obj.state)
            log.msg("Creating a new batch.")
            if batch_db_obj.state == 'failed':
                # batch doesn't have an existing uuid
                batch_obj = construct_batch(batch_path=b_path)
            elif batch_db_obj.state == 'finished with errors':
                # batch does have an existing UUID
                batch_obj = construct_batch(batch_path=b_path, existing_batch=batch_db)
                # set batch_old_uuid variable in batch to be the value of uuid of the previously processed batch
                batch_obj.old_batch_uuid = batch_db.uuid
            else:
                raise Exception("Batch should be created but previous batch with the same name has invalid state.")

            return batch_obj

        def create_batch_directory(batch_obj):
            """

            :param batch_obj:
            :return:
            """
            try:
                out_dir = batch_obj.output_path
                # try to create document directory in the document root working directory
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
                else:
                    pass
            except Exception as e:
                raise e

        def insert_batch_to_table(batch_obj):
            """
            Method inserts batch to batch table with default state (planned) and flushes changes to the database.
            :param batch_obj: batch object
            :return: None
            """
            self.db_int.batch.insert(uuid=str(batch_obj.batch_uuid), state='planned', name=batch_obj.batch_file_name)
            self.db_int.flush()

        log.msg("\n\nSETTING UP BATCHES TO WORK WITH:")

        try:
            for b_path in batch_files:
                batch_db = self.batch_in_db(os.path.basename(b_path))
                if batch_db is not None:
                    if can_process_batch(batch_db):
                        log.msg("can process batch:", can_process_batch(batch_db))
                        # create batch using old batch object from db
                        batch = create_batch_object(batch_db)
                    else:
                        # ignore planned or started or finished batches in db at the time can_process_batch is evaluated
                        log.msg("batch db state:", batch_db.state)
                        continue
                else:
                    log.msg("Batch", os.path.basename(b_path), "not yet processed.")
                    log.msg("Setting up batch...")
                    # create a new batch
                    batch = construct_batch(batch_path=b_path)

                create_batch_directory(batch)
                log.msg("SETUP BATCHES: Inserting batch", batch.batch_uuid, "in the table.")
                insert_batch_to_table(batch)
                log.msg("SETUP BATCHES: Appending batch", batch.batch_uuid, "to batches list.")
                self.setup_batches_list.append(batch)
        except Exception as e:
            raise e

    def batch_in_db(self, batch_name):
        """
        Get batch with the same name as current batch from DB or return None.
        :param batch_name: name of the currently processed batch
        :return: batch database object or None
        """
        # check existence of previously processed batches with the same name - get only batch processed last
        batch_db = self.db_int.batch.filter_by(name=batch_name).order_by(
            self.db_int.batch.finished.desc()
        ).first()

        if batch_db is not None:
            log.msg("SETUP BATCHES: Last processed batch with name", batch_name,
                    "processed with uuid", batch_db.uuid, "found in DB.")
        else:
            log.msg("SETUP BATCHES: Batch with name", batch_name, "not found in the database.")

        return batch_db

    def finish_workflow(self):
        """

        :return:
        """
        def check_finish_state():
            """

            :return:
            """
            # reset lists
            self.batches_ok = list()
            self.batches_errors = list()
            self.batches_failed = list()

            for batch in self.batches_processing:
                b_state = batch.batch_state
                log.msg('Batch has state: ', b_state)
                if b_state == 'finished':
                    self.batches_ok.append(batch)
                elif b_state == 'finished with errors':
                    self.batches_errors.append(batch)
                    store_error_batchfile(batch)
                elif b_state == 'failed':
                    self.batches_failed.append(batch)
                    store_error_batchfile(batch)
                else:
                    raise Exception('Batch ' + str(batch.batch_uuid) + ' finshed with wrong state: ' + b_state)

        def store_error_batchfile(batch):
            """
            Moves batch file to a given batches_error location if batch is failed or finished with errors.
            :return: None
            """
            b_error_folder = self.config.get('batch_errors', 'path')
            new_path = os.path.join(b_error_folder, os.path.basename(batch.batch_file_path))
            try:
                if self.config.getboolean('batch_errors', 'is_remote') is True:
                    self.sftp.rename(batch.batch_file_path, new_path)
                else:
                    shutil.move(batch.batch_file_path, new_path)
            except Exception as e:
                raise Exception('Failed to move batch XML file to batches_errors folder.')

        def set_workflow_state():
            """

            :return:
            """
            if len(self.batches_processing) == 0:
                self.state = 'stopped'
            else:
                if len(self.batches_failed) == len(self.batches_processing):
                    # if all the batches failed, it's better to set workflow as failed to prevent running it again
                    self.state = 'failed'
                else:
                    self.state = 'stopped'

        check_finish_state()
        log_info.log_workflow_info(self)
        set_workflow_state()
        return self.state
