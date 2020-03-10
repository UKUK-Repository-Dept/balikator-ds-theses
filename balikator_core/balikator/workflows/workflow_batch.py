#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from twisted.python import log
from datetime import datetime
from subprocess import check_call, CalledProcessError
from balikator.workflows.workflow_batch_setup import workflow_batch_setup
from balikator.workflows.workflow_batch_processing import workflow_batch_processing
from balikator.workflows.workflow_batch_import import workflow_batch_import


class workflow_batch(object):
    """
    Objects of this class represent a batch workflow.
    """

    def __init__(self, db_int, db_sis, db_dspace, config, utility, ssh, sftp, scp, dspace_api_key):
        """
        Constructor for WorkflowBatch object.
        :param db_int: connection to internal database
        :param db_sis: connection to SIS database
        :param config: ConfigParser object with paresed balikator.ini configuration file
        :param utility: reference to instance of utility class
        :param ssh: reference to ssh client object
        :param sftp: reference to sftp client object
        :param scp: reference to scp client object
        """
        log.msg('Instantiating Workflow_Batch')
        self.db_int = db_int
        self.db_sis = db_sis
        self.db_dspace = db_dspace
        self.config = config
        self.utility = utility
        self.ssh = ssh
        self.sftp = sftp
        self.scp = scp
        self.dspace_api_key = dspace_api_key
        log.msg('Instantiating Workflow_Batch_Setup')
        self.workflow_batch_setup = workflow_batch_setup(self.db_int, self.db_sis, self.config, self.utility,
                                                         self.sftp, self.scp)
        log.msg('Instantiating Workflow_Batch_Processing')
        self.workflow_batch_processing = workflow_batch_processing(self.db_int, self.db_sis, self.config, self.ssh,
                                                                   self.sftp, self.scp, self.dspace_api_key)
        log.msg('Instantiating Workflow_Batch_Import')
        self.workflow_batch_import = workflow_batch_import(self.db_int, self.db_sis, self.config, self.ssh, self.sftp,
                                                           self.scp, self.dspace_api_key)
        log.msg('Instantiation finished')
    def run(self, batch):
        if batch.batch_state == 'planned':
            try:
                batch_state = self.workflow_batch_setup.run(batch)
                batch.batch_state = batch_state
                batch.commit()
            except Exception as e:
                log.msg(e)
                batch.batch_state = 'failed'
                batch.error = str(e)
                batch.batch_finished_date = datetime.today()
                batch.commit()

        if batch.batch_state == 'started':
            try:
                log.msg("WORKFLOW BATCH - Preparing to launch workflow for batch processing.")
                batch_state = self.workflow_batch_processing.run(batch)
                batch.batch_state = batch_state
                batch.commit()
            except Exception as e:
                log.msg(e)
                batch.batch_state = 'failed'
                batch.error = str(e)
                batch.batch_finished_date = datetime.today()
                batch.commit()

        if batch.batch_state == 'finished_processing':
            if batch.batch_process == 'doc_import':

                # FIXME: This is not ideal, but it might fix this issue temporarily:
                # FIXME: https://groups.google.com/d/msg/dspace-tech/c5i0awCKXBM/__z2EXvYAgAJ
                log.msg("STARTING FORCE REINDEX OF NEW ITEMS:")
                try:
                    self.dspace_index_discovery()
                except Exception as e:
                    log.msg(e)
                    log.err('Failed to update DSpace index.')
                    batch.error = 'Failed to update DSpace index'
                    batch.commit()

                log.msg("Starting create_mapfile() function...")
                # create map file after whole batch is processed
                try:
                    process = self.create_mapfile(batch)
                    batch.batch_process = process
                except Exception as e:
                    log.msg(e)
                    log.err('Failed to create mapfile.', str(e))
                    batch.batch_state = 'failed'
                    batch.error = str(e)
                    batch.batch_finished_date = datetime.today()
                    batch.commit()
            if batch.batch_process == 'create_mapfile':
                log.msg("Starting move_mapfile() function...")
                # move finished map file
                try:
                    process = self.move_mapfile(path=batch.aleph_mapfile)
                    batch.batch_process = process
                except Exception as e:
                    log.msg(e)
                    log.err('Failed to move mapfile.', str(e))
                    batch.batch_state = 'failed'
                    batch.error = str(e)
                    batch.batch_finished_date = datetime.today()
                    batch.commit()

            if batch.batch_process == 'move_mapfile':
                log.msg("Starting batches cleanup_finish() function...")
                try:
                    batch_state = self.cleanup_finish(batch)
                    batch.batch_state = batch_state
                    batch.commit()
                except Exception as e:
                    log.msg(e)
                    batch.batch_state = 'failed'
                    batch.error = str(e)
                    batch.batch_finished_date = datetime.today()
                    batch.commit()

        if batch.batch_state == 'cleanup':
            log.msg("Starting evaluate_batch() function...")
            try:
                batch_state = self.evaluate_batch(batch)
                batch.batch_state = batch_state
                batch.commit()
            except Exception as e:
                log.msg(e)
                batch.batch_state = 'failed'
                batch.error = str(e)
                batch.batch_finished_date = datetime.today()
                batch.commit()

        return batch.batch_state

    def dspace_index_discovery(self):

        if self.config.getboolean('dspace', 'is_remote') is True:
            command = self.config.get('index_discovery', 'command')
            try:
                log.msg("Document: Trying to execute the command over SSH.")
                stdin, stdout, stderr = self.ssh.exec_command(command)
            except Exception as e:
                log.msg(e)
                raise e

            log.msg("Remote remove finished with exit code:", stdout.channel.recv_exit_status())
            log.msg("Standard output:\n", stdout)
            log.msg("Error output:\n", stderr)

            if stdout.channel.recv_exit_status() != 0:
                raise Exception('Failed update DSpace index.')
        else:
            command_ds = self.config.get('index_discovery_local', 'command_ds')
            command_index = self.config.get('index_discovery_local', 'command_index_discovery')
            command = [command_ds, command_index]
            try:
                finished = check_call(command)
                log.msg("Command", command, "returned value:", finished)
            except CalledProcessError as e:
                log.msg(e)
                log.msg('Failed to unimport document from local DSpace.')
                raise Exception('Failed to unimport document from DSpace.')
            except Exception as ex:
                log.msg('Failed to unimport document from local DSpace due to the unexpected error')
                raise ex

    def create_mapfile(self, batch):
        """

        :param batch:
        :return:
        """

        def create_file():
            """

            :return:
            """
            b_name, b_suff = batch.batch_file_name.split(sep='.')
            temp_mapfile_dir = self.config.get('balikator', 'dspace_mapfile_temp_dir')
            mf_name = self.config.get('balikator', 'mapfile_name')
            # mf_suffix = self.config.get('balikator', 'aleph_map_suffix')
            # mf_name = mf_prefix + b_name + mf_suffix

            # set the mapfile location for batch
            batch.aleph_mapfile = os.path.join(temp_mapfile_dir, mf_name)
            try:
                file_handle = open(batch.aleph_mapfile, mode='w')
            except Exception as e:
                log.msg(e)
                raise Exception('Failed to create DSpace - ALEPH mapfile for batch ' + batch.batch_file_name +
                                ': uuid: ' + batch.batch_uuid)
            return file_handle

        def write_doc_map(file_handle, mapfile_info):
            """

            :param file_handle:
            :param mapfile_info: dict with information about each theses object currently in DSpace
            :return:
            """
            header = '#sysno;rep_id;dtl_id;handle'
            separator = ';'

            # write first line
            try:
                file_handle.write(header + '\n')
            except Exception as e:
                log.msg(e)
                raise Exception('Failed to write DSpace mapfile header.')

            for s_id, s_id_info in mapfile_info.items():
                if s_id_info['work_type'] not in ['bakalářská práce','diplomová práce','dizertační práce','rigorózní práce']:
                    log.msg("WRITE MAP FILE: found an illegal work type: ", s_id_info['work_type'], 'in document', s_id)
                    continue

                if s_id_info['dtl_id'] is not None:
                    dtl_id = s_id_info['dtl_id']
                else:
                    dtl_id = ''

                if s_id_info['aleph_sysno'] is not None:
                    aleph_id = s_id_info['aleph_sysno']
                else:
                    aleph_id = ''

                if s_id_info['sis_id'] is not None:
                    doc_did = s_id_info['sis_id']
                else:
                    doc_did = ''

                if s_id_info['handle'] is not None:
                    handle = s_id_info['handle']
                else:
                    handle = ''

                # create string from values in s_id_info and write it to the mapfile
                map_string = str(aleph_id) + separator + str(doc_did) + separator + str(dtl_id) + separator + str(handle)

                try:
                    file_handle.write(map_string + "\n")
                except Exception as e:
                    log.msg(e)
                    raise Exception("Failed to write to DSpace mapfile.")

        # TODO: Rewrite to get all theses from DSpace DB
        # get all finished documents in DSpace
        dspace_theses = self.db_dspace.execute("SELECT i.owning_collection, "
                                               "h.handle, "
                                               "(SELECT text_value AS sis_id FROM metadatavalue WHERE metadata_field_id=155 AND resource_id=m.resource_id GROUP BY text_value), "
                                               "(SELECT text_value AS aleph_id FROM metadatavalue WHERE metadata_field_id=159 AND resource_id=m.resource_id GROUP BY text_value), "
                                               "(SELECT text_value AS dtl_id FROM metadatavalue WHERE metadata_field_id=193 AND resource_id=m.resource_id GROUP BY text_value), "
                                               "(SELECT text_value AS work_type FROM metadatavalue WHERE metadata_field_id=66 AND resource_id=m.resource_id GROUP BY text_value) "
                                               "FROM item AS i, handle AS h, metadatavalue AS m "
                                               "WHERE m.resource_id=h.resource_id AND "
                                               "h.resource_type_id=2 AND "
                                               "i.item_id=h.resource_id AND "
                                               "i.owning_collection=("
                                               "SELECT i.owning_collection "
                                               "FROM item AS i "
                                               "WHERE i.item_id=h.resource_id GROUP BY i.owning_collection) AND "
                                               "(SELECT text_value AS work_type "
                                               "FROM metadatavalue WHERE metadata_field_id=66 AND "
                                               "resource_id=m.resource_id AND "
                                               "text_lang='cs_CZ') "
                                               "IN ('bakalářská práce','diplomová práce','dizertační práce','rigorózní práce') "
                                               "GROUP BY h.handle, m.resource_id, i.owning_collection;")

        mapfile_info = dict()
        for col, handle, sis_id, aleph_sysno, dtl_id, work_type in dspace_theses.fetchall():
            mapfile_info[handle] = {'collection': col,
                                    'handle': handle,
                                    'sis_id': sis_id,
                                    'aleph_sysno': aleph_sysno,
                                    'dtl_id': dtl_id,
                                    'work_type': work_type}
        try:
            fh = create_file()

            write_doc_map(fh, mapfile_info)

            fh.close()
        except Exception as e:
            log.msg("ERROR:")
            log.msg(e)
            raise e
        return 'create_mapfile'

    def move_mapfile(self, path):
        """

        :param path:
        :return:
        """
        if path is None:
            log.err('Cannot move batch map file.', 'Map file was not created.')
            return True

        is_remote = self.config.getboolean('aleph_mapfile_share', 'is_remote')
        file_name = os.path.basename(path)

        log.msg("DSPACE MAPFILE NAME:", file_name)
        # name, suff = file_name.split(sep='.')
        # mapfile_name = name + self.config.get('balikator', 'aleph_map_suffix')

        if is_remote:
            try:
                self.scp.put(path, remote_path=self.config.get('aleph_mapfile_share', 'path'))
            except Exception as e:
                log.msg(e)
                raise Exception("SCPClient: Failed to copy Aleph map file to remote shared folder.")
        else:
            try:
                shutil.move(src=path, dst=os.path.join(self.config.get('aleph_mapfile_share', 'path'), file_name))
            except Exception as e:
                log.msg(e)
                raise Exception('Failed to move Aleph mapfile to local shared folder.')
        return 'move_mapfile'

    def cleanup_finish(self, batch):
        """

        :param batch:
        :return:
        """

        def clean_batch_folder(folder, is_remote=False):
            """
            Removes batch folder on local or remote machine.
            :param folder: path to folder to be removed
            :param is_remote: True if folder in on remote machine, False if it's on local machine
            :return: None
            :raises Exception if folder cannot be removed
            """

            try:
                log.msg("Removing remote batch folder", folder, "...")
                self.utility.remove_folder(path=folder, is_remote=is_remote, sftp_client=self.sftp)
            except Exception as e:
                log.msg(str(e))
                log.err("Cannot remove folder {}".format(folder), str(e))
                raise Exception('Cannot remove batch folder, ' + folder)

        def remove_batch_folders():
            """
            Removes batch output directory and batch import directory if it exists.
            :return: None
            """
            if self.utility.folder_exists(path=batch.get_batch_out_path,
                                          is_remote=self.config.getboolean('batch', 'output_is_remote'),
                                          sftp_client=self.sftp):

                log.msg("Trying to remove batch output directory", batch.get_batch_out_path, "...")
                clean_batch_folder(batch.get_batch_out_path,
                                   is_remote=self.config.getboolean('batch','output_is_remote'))
            else:
                log.msg("Batch folder", batch.get_batch_out_path, "doesn't exist.")

            if self.utility.folder_exists(path=batch.import_folder,
                                          is_remote=self.config.getboolean('import', 'is_remote'),
                                          sftp_client=self.sftp):
                log.msg("Trying to remove batch import directory", )
                clean_batch_folder(batch.import_folder, is_remote=self.config.getboolean('import', 'is_remote'))
            else:
                log.msg("Batch import folder", batch.import_folder, "doesn't exist.")

        #############################
        #   REMOVE BATCH FOLDERS    #
        #############################
        try:
            remove_batch_folders()
        except Exception as e:
            raise e

        return 'cleanup'

    def evaluate_batch(self, batch):
        """

        :param batch:
        :return:
        """

        def document_errors():
            """

            :return:
            """
            doc_errors = self.db_int.errors_document.filter_by(batch_uuid=str(batch.batch_uuid)).all()

            if len(doc_errors) == 0:
                return None
            else:
                return doc_errors

        # check the database if there are some document errors for documents in this batch
        if document_errors() is None:
            # batch finished without document errors
            return 'finished'

        # batch has some documents that finished with error or batch itself encountered an error
        return 'finished with errors'
