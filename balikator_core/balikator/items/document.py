#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from sqlalchemy import and_
from twisted.python import log
from subprocess import check_call, CalledProcessError
import requests
import urllib.parse
from urllib.parse import urljoin


class Document(object):

    def __init__(self, doc_id, batch_uuid, doc_kind, record_object, db_int, config, utility):
        self.batch_uuid = batch_uuid
        self.doc_id = doc_id
        self.doc_kind = doc_kind
        self.record_object = record_object
        self.db_int = db_int
        self.config = config
        self.utility = utility
        self.batch_path = os.path.join(self.config.get('batch', 'output_path'), str(self.batch_uuid))
        self.out_dir_path = os.path.join(self.batch_path, self.doc_id)
        self.import_folder_path = None
        self.error_folder_path = None
        # self.doc_direction = self.record_object['func'].data
        self.rec_direction = self.record_object['func'].data # record direction
        self.file_info = list()
        self.dc_meta_proto = None
        self.dcterms_meta_proto = None
        self.thesis_meta_proto = None
        self.uk_meta_proto = None
        self.in_live_table = False
        self.can_change = False
        self.document_files = []
        self.contents_file_loc = None
        self.thmb_file_loc = None
        self.errors = []
        self.record = None
        self.last_processed_doc = None
        self.work_avalability = None

    def commit(self):
        """
        Commits changes in the document record to the internal database.
        :return:
        """
        self.db_int.commit()

    def insert(self, state):
        """Inserts document into the document table."""
        self.db_int.document.insert(did=self.doc_id, state=state, kind=self.doc_kind, repId=self.doc_id,
                                    batch_uuid=str(self.batch_uuid), direction_process=self.record_object['func'].data)
        self.db_int.commit()

    def update(self, state, process, c_time, f_time):
        """
        Updates document in the document table.
        :return:
        """
        params = {'did': self.doc_id, 'state': state, 'kind': self.doc_kind, 'repId': self.doc_id,
                  'batch_uuid': str(self.batch_uuid), 'direction_process': self.record_object['func'].data,
                  'current_process': process, 'created': c_time, 'finished': f_time}
        self.db_int.document.filter_by(did=self.doc_id).update(params)
        self.db_int.commit()

    def insert_to_handle_tab(self, handle=None):
        self.db_int.document_handles.insert(did=self.doc_id, handle=handle)
        self.db_int.commit()

    @property
    def import_folder(self):
        return self.import_folder_path

    @import_folder.setter
    def import_folder(self, value):
        self.import_folder_path = value

    @property
    def error_folder(self):
        return self.error_folder_path

    @error_folder.setter
    def error_folder(self, value):
        self.error_folder_path = value

    @property
    def error(self):
        where = and_(self.db_int.errors_document.doc_id == self.doc_id,
                     self.db_int.errors_document.batch_uuid == self.batch_uuid)
        return self.db_int.errors_document.filter(where).all()

    @error.setter
    def error(self, value):
        self.db_int.errors_document.insert(doc_id=self.doc_id, batch_uuid=str(self.batch_uuid), error_message=value)


    @property
    def aleph_id(self):
        return self.db_int.document.filter_by(did=self.doc_id).first().aleph_id

    @aleph_id.setter
    def aleph_id(self, value):
        self.db_int.document.filter_by(did=self.doc_id).first().aleph_id = value

    @property
    def work_type(self):
        return self.db_int.document.filter_by(did=self.doc_id).first().work_type

    @work_type.setter
    def work_type(self, value):
        self.db_int.document.filter_by(did=self.doc_id).first().work_type = value

    @property
    def rep_id(self):
        return self.db_int.document.filter_by(did=self.doc_id).first().repId

    @property
    def handle(self):
        # FIXME: We need to insert document did to handle table if there is none first, otherwise this won't work
        return self.db_int.document_handles.filter_by(did=self.doc_id).first().handle

    @handle.setter
    def handle(self, handle):
        self.db_int.document_handles.filter_by(did=self.doc_id).first().handle = handle

    @property
    def document_handle(self):
        return self.db_int.document.filter_by(did=self.doc_id).first().handle

    @document_handle.setter
    def document_handle(self, handle):
        self.db_int.document.filter_by(did=self.doc_id).first().handle = handle

    def audit_document(self):
        self.db_int.document_audit.insert(did=self.doc_id, repId=self.rep_id, aleph_id=self.aleph_id,
                                          batch_uuid=str(self.batch_uuid), handle=self.document_handle,
                                          direction_process=self.record_direction,
                                          workflow_process=self.workflow_process, kind=self.kind, created=self.created,
                                          finished=self.finished, state=self.state, work_type=self.work_type)

    @property
    def kind(self):
        # return self.db_int.document.filter_by(did=self.doc_id).first().kind
        return self.doc_kind

    @property
    def created(self):
        return self.db_int.document.filter_by(did=self.doc_id).first().created

    @property
    def finished(self):
        return self.db_int.document.filter_by(did=self.doc_id).first().finished

    @finished.setter
    def finished(self, value):
        self.db_int.document.filter_by(did=self.doc_id).first().finished = value

    @property
    def last_processed(self):
        return self.last_processed_doc

    @last_processed.setter
    def last_processed(self, doc_db):
        self.last_processed_doc = doc_db

    @property
    def cf_location(self):
        return self.contents_file_loc

    @cf_location.setter
    def cf_location(self, path):
        self.contents_file_loc = path

    @property
    def thmb_file(self):
        return self.thmb_file_loc

    @thmb_file.setter
    def thmb_file(self, value):
        self.thmb_file_loc = value

    @property
    def work_files(self):
        """
        Returns a list of dictionaries containing information on all document (work) files from the SIS database.
        Dictionaries contain this information: did': work identifier in SIS DB, 'fid': file identifier in storage,
        'ftyp': type of the file according to given standards, 'fnazev': name of the file
        :return: list(dictionaries): list of dictionaries containing information about all document files from SIS
        """
        return self.file_info

    @work_files.setter
    def work_files(self, value):
        """
        Stores a list of dictionaries containing information on all document (work) files from the SIS database.
        :param value: list(dictionaries): list of dictionaries containing information about all document files from SIS
        :return: None
        """
        self.file_info = value

    @property
    def record_direction(self):
        """
        Returns a direction in which the document (work) enters the workflow. It could be an "insert", "update" or
        "delete" direction. Documents with different direction are processed differently withing the document workflow.
        :return: string(doc_direction): string representing a direction in which document enters document workflow
        """
        return self.rec_direction

    @property
    def workflow_process(self):
        """
        Workflow direction - might be different from the record direction.
        :return:
        """
        return self.db_int.document.filter_by(did=self.doc_id).first().workflow_process

    @workflow_process.setter
    def workflow_process(self, value):
        self.db_int.document.filter_by(did=self.doc_id).first().workflow_process = value

    @property
    def dc_proto(self):
        """
        Returns a dc metadata object stored within the document object.
        :return: dc_meta_proto: dc_proto object containing all metadata in DC format/namespace
        """
        return self.dc_meta_proto

    @dc_proto.setter
    def dc_proto(self, meta_obj):
        """
        Sets a reference to dc_proto metadata object on the document object.
        :param meta_obj: dc_proto object containing all metadata in DC format/namespace
        :return:
        """
        self.dc_meta_proto = meta_obj

    @property
    def dcterms_proto(self):
        """
        Returns a dcterms metadata object stored within the document object.
        :return: dcterms_meta_proto: dcterms_proto object containing all metadata in DCTERMS format/namespace
        """
        return self.dcterms_meta_proto

    @dcterms_proto.setter
    def dcterms_proto(self, meta_obj):
        """
        Sets a reference to dcterms_proto metadata object on the document object.
        :param meta_obj: dcterms_proto object containing all metadata in DCTERMS format/namespace
        :return:
        """
        self.dcterms_meta_proto = meta_obj

    @property
    def thesis_proto(self):
        """
        Returns an thesis metadata object stored within the document object.
        :return: thesis_meta_proto: thesis_proto object containing all metadata in THESIS format/namespace
        """
        return self.thesis_meta_proto

    @thesis_proto.setter
    def thesis_proto(self, meta_obj):
        """
        Sets a reference to thesis metadata object on the document object.
        :param meta_obj: thesis_proto object containing all metadata in THESIS format/namespace
        :return:
        """
        self.thesis_meta_proto = meta_obj

    @property
    def uk_proto(self):
        """
        Returns uk metadata object stored within the document object.
        :return: uk_meta_proto: uk_proto object containing all metadata in UK format/namespace
        """
        return self.uk_meta_proto

    @uk_proto.setter
    def uk_proto(self, meta_obj):
        """
        Sets a reference to uk metadata object on the document object.
        :param meta_obj: uk_proto object containing all metadata in UK format/namespace
        :return: None
        """
        self.uk_meta_proto = meta_obj

    @property
    def out_dir(self):
        """
        Returns a current output directory of the document (work).
        :return: path: path to document (work) output directory
        """
        return self.out_dir_path

    @out_dir.setter
    def out_dir(self, path):
        """
        Sets an output directory of the document.
        :param path: path to a document (work) output directory.
        :return: None
        """
        self.out_dir_path = path

    @property
    def state(self):
        """
        Returns a current state of the document from the database.
        :return: string(current_state) - string representing current state of the document in database
        """
        return self.db_int.document.filter_by(did=self.doc_id).first().state

    @state.setter
    def state(self, value):
        """
        Sets a new state of the document in database.
        :param value: string(state) - string representing a new state of the document in database
        :return: None
        """
        self.db_int.document.filter_by(did=self.doc_id).first().state = value

    @property
    def current_process(self):
        """
        Returns a current process of the document.
        :return: string(current_process) - string representing current process of the document
        """
        return self.db_int.document.filter_by(did=self.doc_id).first().current_process

    @current_process.setter
    def current_process(self, value):
        """
        Sets a new current process of the document in database.
        :param value: string(process_name) - string representing current document process
        :return:
        """
        self.db_int.document.filter_by(did=self.doc_id).first().current_process = value

    @property
    def doc_files(self):
        """
        Returns a list of document (work) files.
        :return: list: list of document files
        """
        return self.document_files

    @doc_files.setter
    def doc_files(self, value):
        """
        Stores a list of files to appropriate variable.
        :param value: list(files) - list of files belonging to one document (work)
        :return:
        """
        self.document_files = value

    @property
    def path_to_batch(self):
        """
        Getter for package_path variable. Gets the string value from package_path variable, containing full path to
        package directory of the document.
        :return: string: full path to package directory
        """
        return self.batch_path

    @path_to_batch.setter
    def path_to_batch(self, value):
        """
        Setter for package_path variable. Assigns string value containing path the package directory of the document.
        :param value: string: full path to the package directory
        :return:
        """
        self.batch_path = value

    @property
    def doc_record(self):
        """
        Getter for document record variable.
        :return: record: instance of documents' record object
        """
        return self.record

    @doc_record.setter
    def doc_record(self, value):
        """
        Setter for document record. Assigns instance of record object to record variable.
        :param value: instance of record object
        :return:
        """
        self.record = value

    @property
    def doc_collection(self):
        """

        :return:
        """
        faculty_collection_id = None
        faculty_name_list = self.dc_proto.get_description_faculty(lang='cs')
        faculty_name = None
        for faculty_dict in faculty_name_list:
            faculty_name = faculty_dict['content']

        for (col_id, faculty_col_name) in self.config.items('import_collections_map'):
            if faculty_name == faculty_col_name:
                faculty_collection_id = col_id

        if faculty_collection_id is None:
            raise Exception('Cannot assign collection ID. Faculty ' + faculty_name + ' is not in the config file.')

        return faculty_collection_id

    def create_command_ingest(self, mapfile_path):
        """

        :param mapfile_path:
        :return:
        """
        if self.config.getboolean('dspace', 'is_remote') is True:
            command_part = self.config.get('import', 'command')
            collection = self.config.get('import', 'collection') + ' ' + self.doc_collection
            package_path = self.config.get('import', 'package_path') + ' ' + self.import_folder
            eperson = self.config.get('dspace', 'eperson')
            mapfile = self.config.get('dspace', 'mapfile') + ' ' + mapfile_path
            command = command_part + ' ' + eperson + ' ' + collection + ' ' + package_path + ' ' + mapfile
        else:
            command_part = self.config.get('import_local', 'command_ds')
            command_part_import = self.config.get('import_local', 'command_import')
            command_import_flag = self.config.get('import_local', 'command_import_flag')
            command_eperson_flag = self.config.get('import', 'eperson')
            command_eperson = self.config.get('dspace', 'admin_mail')
            command_mapfile_flag = self.config.get('import', 'mapfile_path')
            command_mapfile = mapfile_path
            command_collection_flag = self.config.get('import', 'collection')
            command_collection = self.doc_collection
            command_package_flag = self.config.get('import', 'package_path')
            command_package = self.import_folder
            command = [command_part, command_part_import, command_import_flag, command_eperson_flag, command_eperson,
                       command_collection_flag, command_collection, command_package_flag, command_package,
                       command_mapfile_flag, command_mapfile]

        return command

    def create_command_replace(self, mapfile_path):
        if self.config.getboolean('dspace', 'is_remote') is True:
            command_part = self.config.get('replace', 'command')
            collection = self.config.get('import', 'collection') + ' ' + self.doc_collection
            package_path = self.config.get('import', 'package_path') + ' ' + self.import_folder
            eperson = self.config.get('dspace', 'eperson')
            mapfile = self.config.get('dspace', 'mapfile') + ' ' + mapfile_path
            command = command_part + ' ' + eperson + ' ' + collection + ' ' + package_path + ' ' + mapfile
        else:
            command_part = self.config.get('replace_local', 'command_ds')
            command_part_import = self.config.get('replace_local', 'command_replace')
            command_import_flag = self.config.get('replace_local', 'command_replace_flag')
            command_eperson_flag = self.config.get('import', 'eperson')
            command_eperson = self.config.get('dspace', 'admin_mail')
            command_mapfile_flag = self.config.get('import', 'mapfile_path')
            command_mapfile = mapfile_path
            command_collection_flag = self.config.get('import', 'collection')
            command_collection = self.doc_collection
            command_package_flag = self.config.get('import', 'package_path')
            command_package = self.import_folder
            command = [command_part, command_part_import, command_import_flag, command_eperson_flag, command_eperson,
                       command_collection_flag, command_collection, command_package_flag, command_package,
                       command_mapfile_flag, command_mapfile]

        return command

    def create_command_delete(self, mapfile_path):
        """

        :param mapfile_path:
        :return:
        """
        if self.config.getboolean('dspace', 'is_remote') is True:
            mapfile_remote = True
            command_part = self.config.get('delete', 'command')
            eperson = self.config.get('dspace', 'eperson')
            mapfile = self.config.get('dspace', 'mapfile') + ' ' + mapfile_path
            command = command_part + ' ' + eperson + ' ' + mapfile
        else:
            mapfile_remote = False
            command_part = self.config.get('delete_local', 'command_ds')
            command_part_delete = self.config.get('delete_local', 'command_delete')
            command_delete_flag = self.config.get('delete_local', 'command_delete_flag')
            command_eperson_flag = self.config.get('delete', 'eperson')
            command_eperson = self.config.get('dspace', 'admin_mail')
            command_mapfile_flag = self.config.get('delete', 'mapfile_path')
            command_mapfile = mapfile_path
            command = [command_part, command_part_delete, command_delete_flag, command_eperson_flag, command_eperson,
                       command_mapfile_flag, command_mapfile]
        return command

    def construct_command(self, comm_type='ingest', sftp_client=None):
        """

        :param comm_type:
        :param sftp_client:
        :return:
        """
        mapfile_name = self.doc_id + self.config.get('dspace', 'mapfile_suff')
        mapfile_path = os.path.join(self.config.get('dspace', 'mapfile_path'), mapfile_name)

        if self.config.getboolean('dspace', 'is_remote') is True:
            mapfile_remote = True
        else:
            mapfile_remote = False

        if comm_type == 'ingest':
            command = self.create_command_ingest(mapfile_path=mapfile_path)

        elif comm_type == 'update':
            if not self.utility.file_exists(mapfile_path, is_remote=mapfile_remote, sftp_client=sftp_client):
                log.msg("Mapfile doesn't exist. Cannot construct", comm_type, "command")
                raise Exception("Exception: Mapfile doesn't exist. Cannot construct " + comm_type + " command.")

            if self.utility.file_empty(mapfile_path, is_remote=mapfile_remote, sftp_client=sftp_client) is True:
                log.msg("Mapfile  is empty, cannot unimport document.")
                raise Exception("Mapfile is empty, cannot unimport document.")

            command = self.create_command_replace(mapfile_path=mapfile_path)
                
        elif comm_type == 'delete':
            if not self.utility.file_exists(mapfile_path, is_remote=mapfile_remote, sftp_client=sftp_client):
                log.msg("Mapfile doesn't exist. Cannot construct", comm_type, "command")
                raise Exception("Mapfile doesn't exist. Cannot construct " + comm_type + " command.")

            if self.utility.file_empty(mapfile_path, is_remote=mapfile_remote, sftp_client=sftp_client) is True:
                log.msg("Mapfile  is empty, cannot unimport document.")
                raise Exception("Mapfile is empty, cannot unimport document.")

            command = self.create_command_delete(mapfile_path=mapfile_path)

        else:
            raise Exception('Unknown DSpace command type.')

        log.msg('DSPACE IS REMOTE:', self.config.get('dspace', 'is_remote'))
        log.msg('DSPACE COMMAND:', command)

        return command

    def ingest_remote(self, ssh):
        """

        :param ssh:
        :return:
        """
        command = self.construct_command()
        # try:

        #     #stdin, stdout, stderr = ssh.exec_command('sudo -i -u ' + self.config.get('dspace', 'ds_user_username'))
        #     stdin, stdout, stderr = ssh.exec_command('sudo -i -u dspace')
        # except Exception as e:
        #     raise e 
        
        #FIXME: This returns error code: 126 (not executable - perhaps because we are trying to execute the command as user without sufficient privileges?)
        try:
            stdin, stdout, stderr = ssh.exec_command(command)
        except Exception as e:
            raise e

        log.msg("Remote ingest finished with exit code:", stdout.channel.recv_exit_status())
        log.msg("Standard output:\n", stdout)
        log.msg("Error output:\n", stderr)

        if stdout.channel.recv_exit_status() != 0:
            raise Exception('Failed to ingest document to DSpace')
        else:
            return True

    def ingest_local(self):
        """

        :return:
        """
        command = self.construct_command(comm_type='ingest')
        try:
            finished = check_call(command)
            log.msg("Command", command, "returned code:", finished)
            log.msg("Document ingested.")
            return True
        except CalledProcessError as e:
            log.msg("Command", command, "returned error code:", e.returncode)
            log.msg(e)
            raise Exception('Failed to ingest document to DSpace.')
        except Exception as ex:
            raise ex

    def replace_remote(self, ssh):
        command = self.construct_command(comm_type='update')
        try:
            stdin, stdout, stderr = ssh.exec_command(command)
        except Exception as e:
            raise e

        log.msg("Remote replace finished with exit code:", stdout.channel.recv_exit_status())
        log.msg("Standard output:\n", stdout)
        log.msg("Error output:\n", stderr)

        if stdout.channel.recv_exit_status() != 0:
            raise Exception('Failed to ingest document to DSpace')
        else:
            return True

    def replace_local(self):
        command = self.construct_command(comm_type='update')
        try:
            finished = check_call(command)
            log.msg("Command", command, "returned code:", finished)
            log.msg("Document ingested.")
            return True
        except CalledProcessError as e:
            log.msg("Command", command, "returned error code:", e.returncode)
            log.msg(e)
            raise Exception('Failed to ingest document to DSpace.')
        except Exception as ex:
            raise ex

    def unimport_local(self):
        """

        :return:
        """
        command = self.construct_command(comm_type='delete')
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

        # checking if document was indeed deleted, e.g. DSpace API reports it is not in DSpace
        if self.document_in_dspace(handle=self.handle) is False:
            return True
        else:
            return False

    def unimport_remote(self, ssh, sftp):
        """

        :param ssh:
        :param sftp:
        :return:
        """
        log.msg("Document: Trying to remove document", self.doc_id)
        command = self.construct_command(comm_type='delete', sftp_client=sftp)
        log.msg("Document: Command constructed.")
        try:
            log.msg("Document: Trying to execute the command over SSH.")
            stdin, stdout, stderr = ssh.exec_command(command)
        except Exception as e:
            raise e

        log.msg("Remote remove finished with exit code:", stdout.channel.recv_exit_status())
        log.msg("Standard output:\n", stdout)
        log.msg("Error output:\n", stderr)

        if stdout.channel.recv_exit_status() != 0:
            raise Exception('Failed to unimport document from DSpace.')

        # checking if document was indeed deleted, e.g. DSpace API reports it is not in DSpace
        if self.document_in_dspace(handle=self.handle) is False:
            # document was not found in DSpace after deletion - deletion finished ok
            return True
        else:
            return False

    def delete_mapfile_remote(self, sftp_client):
        """

        :param sftp_client:
        :return:
        """
        mapfile_name = self.doc_id + self.config.get('dspace', 'mapfile_suff')
        mapfile_path = os.path.join(self.config.get('dspace', 'mapfile_path'), mapfile_name)

        try:
            filestat = sftp_client.stat(mapfile_path)
        except IOError as e:
            log.msg('There is no mapfile for document', self.doc_id)
            return False

        try:
            sftp_client.remove(mapfile_path)
        except Exception as e:
            log.msg(e)
            raise Exception('Failed to remove mapfile for document ' + self.doc_id)

        return True

    def delete_mapfile_local(self):
        """

        :return:
        """
        mapfile_name = self.doc_id + self.config.get('dspace', 'mapfile_suff')
        mapfile_path = os.path.join(self.config.get('dspace', 'mapfile_path'), mapfile_name)

        if not os.path.exists(mapfile_path):
            return False

        try:
            os.remove(mapfile_path)
        except:
            raise Exception('Failed to remove mapfile after deleting document.')

        return True

    def document_in_dspace(self, handle):
        """

        :param handle:
        :return:
        """
        # https: // dspace.cuni.cz / rest / handle / 123456789 / 637
        # handle = doc_db.handle
        log.msg("Checking if document with handle", str(handle), "is in DSpace...")
        url = self.config.get('dspace', 'base_url') + '/rest/handle/' # TODO: Move to config

        hdl = handle.rstrip()
        prefix, suffix = str(hdl).split(sep='/')

        r_url = url + prefix + '/' + suffix
        log.msg("DSpace API request url is:", r_url)

        r = None
        try:
            r = requests.get(r_url, timeout=10)
        except requests.Timeout as ex:
            log.err("Server didn't respond in time:\n", ex.with_traceback(ex.__traceback__))
            log.msg("Trying again for document handle: ", self.handle)
            try:
                self.document_in_dspace(self.handle)
            except Exception as e:
                log.msg(e)

        if r is None:
            log.err("No request sent.")
            raise Exception("No request sent when checking if document is in DSpace.")

        log.msg("DSPACE REQUEST STATUS CODE:: ", r.status_code)

        if r.status_code == r.ok:
            log.msg("DSPACE API response code:", r.status_code)
            log.msg("Document with handle", handle, "found in DSpace!")
            log.msg("Document handle:", handle)
            log.msg("Request:\n", r.request.headers)
            log.msg("\n")
            # log.msg("Request raw\n", r.raw)
            log.msg(r.text)
            log.msg(r.reason)
            return True
        else:
            log.msg("DSPACE API response code:", r.status_code)
            log.msg("Document with handle", handle, "not found in DSpace!")
            log.msg("Document handle:", handle)
            log.msg("Request:\n", r.request.headers)
            log.msg("\n")
            # log.msg("Request raw\n", r.raw)
            log.msg(r.text)
            log.msg(r.reason)
            return False

