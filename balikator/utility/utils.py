#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paramiko
import os
import shutil
import traceback
import re
import pyjq
import requests
from scp import SCPClient
from twisted.python import log
from stat import S_ISDIR
from wand.image import Image
from wand.color import Color


class utility(object):

    def __init__(self, config):
        self.config = config

    def create_ssh_client(self, server, port, user, password):
        """

        :param server:
        :param port:
        :param user:
        :param password:
        :return:
        """
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, port, user, password)
        return client

    def create_scp_client(self, ssh_session):
        """

        :param ssh_session:
        :return:
        """
        if ssh_session is None:
            raise Exception("SSH Client: Failed to connect to the storage server through SSH.")

        scp = SCPClient(ssh_session.get_transport())

        if scp is None:
            raise Exception("SCP Client: Failed to create SCP client.")

        return scp

    def create_sftp_client(self, ssh_session):
        """

        :param ssh_session:
        :return:
        """
        if ssh_session is None:
            raise Exception("SSH Client: Failed to connect to the storage server through SSH")

        sftp = paramiko.SFTPClient.from_transport(ssh_session.get_transport())

        if sftp is None:
            raise Exception("SFTP Client: Failed to create SFTP client.")

        return sftp

    def lang_to_iso(self, lang_str):
        """

        :param lang_str:
        :return:
        """
        # TODO: Should be part of a different class/package
        for option, value in self.config.items('language_map'):
            # if we find a language code in options of 'language_map' part of the config file, return its value
            if option == lang_str:
                return value
        # else return the original language string
        return lang_str

    def create_dir_remote(self, remote_directory, sftp):
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
            self.create_dir_remote(dirname, sftp)  # make parent directories
            sftp.mkdir(basename)  # sub-directory missing, so created it
            sftp.chdir(basename)
            return True

    def create_dir_local(self, local_path):
        try:
            # try to create document directory in the document root working directory
            if not os.path.exists(local_path):
                os.makedirs(local_path)
            else:
                pass
            return local_path
        except:
            raise Exception("Failed to create batch output directory.")

    def create_dir_on_path(self, path, dir_name):
        """

        :param path:
        :param dir_name:
        :return:
        """
        try:
            dir_path = os.path.join(path, dir_name)
            # try to create document directory in the document root working directory
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            else:
                log.msg("Directory already exists.")
                return dir_path
        except:
            raise Exception("Failed to create batch output directory.")
        return dir_path

    def create_dir_on_remote_path(self, path, dirname, is_remote, sftp_client=None):
        if sftp_client is None:
            raise Exception("No SFTP client reference provided. Cannot perform operations on remote machine.")

        folder_path = os.path.join(path, dirname)
        try:
            if not self.folder_exists(path=folder_path, is_remote=is_remote, sftp_client=sftp_client):
                sftp_client.mkdir(folder_path)
            else:
                log.msg("Folder", folder_path, "already exists on remote path.")

            return folder_path
        except Exception as e:
            log.msg(e)
            raise Exception('Failed to create remote folder ' + folder_path)

    def file_exists(self, path, is_remote, sftp_client=None):
        """
        Checks if file exists on local or remote path.
        :param path: path to file
        :param is_remote: bool - True if mapfiles are on remote location, False if they are on local location
        :param location:
        :return: bool - True if file exists, False otherwise
        """
        log.msg("Utils: Checking if file", path, "exists.")
        if is_remote is True:
            if sftp_client is None:
                raise Exception('No SFTP client reference provided. Cannot check existence of remote file.')

            try:
                sftp_client.stat(path)
            except IOError as e:
                log.msg(e)
                log.msg("File", path, "not found on remote path.")
                return False

            return True
        else:
            # check if file exists on local machine
            if os.path.exists(path) and os.path.isfile(path):
                return True
            else:
                return False

    def folder_exists(self, path, is_remote, sftp_client=None):
        """

        :param path:
        :param is_remote:
        :param sftp_client:
        :return:
        """
        log.msg("Utils: Checking if folder", path,  "exists.")
        log.msg("is_remote: ", is_remote)
        if is_remote is True:

            if sftp_client is None:
                raise Exception('No SFTP client reference provided. Cannot check existence of remote folder.')

            try:
                sftp_client.chdir(path)
            except IOError as e:
                log.msg("Folder", path, "not found on remote path.")
                return False

            return True
        else:
            # check if folder exist on local machine
            if os.path.exists(path) is True:
                log.msg("Directiory exists: ", os.path.exists(path))
                if os.path.isdir(path) is True:
                    log.msg("Directory is directory: ", os.path.isdir(path))
                    return True
            else:
                log.msg("Directory exists:", os.path.exists(path))
                return False

    def listdir(self, path, is_remote, sftp_client=None):
        """

        :param path:
        :param is_remote:
        :param sftp_client:
        :return:
        """
        log.msg("Getting directory contents from", path)
        if is_remote is True:
            if sftp_client is None:
                raise Exception('No SFTP client reference provided. Cannot perform listdir on remote path.')

            contents = sftp_client.listdir(path=path)
        else:
            contents = os.listdir(path)

        return contents

    def isdir_remote(self, f_path, sftp_client):
        """
        Checks if remote path is a directory or not, using sftp client.
        :param f_path: path on remote server
        :param sftp_client:
        :return:
        """
        try:
            return S_ISDIR(sftp_client.stat(f_path).st_mode)
        except IOError:
            return False

    def remove_folder(self, path, is_remote, sftp_client=None):

        def rm_remote(f_path):
            """
            Serves to remove directory from remote server recursively, using sftp client.
            :param f_path: path to remote directory
            :return: None
            """
            file_l = sftp_client.listdir(path=f_path)
            log.msg("RM_REMOTE: file_list(", f_path, "):\n", file_l)

            for file in file_l:

                file_path = os.path.join(f_path, file)
                log.msg("Checking file", file, " on path", file_path, "...")
                if self.isdir_remote(file_path, sftp_client=sftp_client) is True:
                    log.msg("Filepath", file_path, "is a directory...")
                    rm_remote(file_path)
                else:
                    log.msg("Filepath", file_path, "is a file...")
                    sftp_client.remove(file_path)
                    log.msg('File', file_path, 'removed...')
            log.msg("Removing directory", f_path, "...")
            sftp_client.rmdir(f_path)
            log.msg("Directory", f_path, "removed...")

        log.msg("Removing folder", path, "...")

        if is_remote is True:
            try:
                rm_remote(f_path=path)
            except Exception as e:
                log.msg(e)
                tb = traceback.format_exc()
                log.msg(tb)
                raise Exception('Failed to clean up remote directory ' + path)
        else:
            try:
                shutil.rmtree(path)
            except Exception as e:
                log.msg(e)
                tb = traceback.format_exc()
                log.msg(tb)
                raise Exception(e)

    def move_folder(self, src, dst, is_remote, sftp_client=None):

        if is_remote is True:   # is_remote is True, if both src and dst are on the same remote server
            if sftp_client is None:
                raise Exception('Utility-move_folder(): No sftp_client provided when trying to folder on remote paths.')

            if self.folder_exists(path=src, is_remote=True, sftp_client=sftp_client) is False:
                raise Exception("Utility-move_folder(): Remote source folder doesn't exist.")

            if self.folder_exists(path=dst, is_remote=True, sftp_client=sftp_client) is False:
                raise Exception("Utility-move_folder(): Remote destination folder doesn't exist.")

            sftp_client.rename(src, dst)
        else:
            if self.folder_exists(path=src, is_remote=False) is False:
                raise Exception("Utility-move_folder(): Local source folder doesn't exist.")

            if self.folder_exists(path=dst, is_remote=False) is False:
                raise Exception("Utility-move_folder(): Local destination folder doesn't exist.")

            shutil.move(src, dst)

    def file_empty(self, path, is_remote, sftp_client):
        """

        :param path:
        :param is_remote:
        :param sftp_client:
        :return:
        """
        if is_remote is True:
            filestat = sftp_client.stat(path)
            if filestat.st_size == 0:
                return True
        else:
            if os.stat(path).st_size == 0:
                return True

        return False

    def create_thumb_from_pdf(self, pdf_path):
        """
        Creates thumbnail from the first page of pdf file using wand module.
        :param pdf_path: path to pdf file from which the thumbnail will be created
        :return: thmb_path: path to created thumbnail
        """
        log.msg("PDF PATH: {}".format(pdf_path))
        thmb_path = os.path.join(os.path.dirname(pdf_path), 'thumbnail.png')
        log.msg("THMB PATH: {}".format(thmb_path))

        first_page = pdf_path + '[0]'
        log.msg("First page: ", first_page)
        img = Image(filename=first_page)
        img.format = 'png'
        img.resize(200, 300)
        img.background_color = Color('white')
        img.alpha_channel = 'remove'
        img.save(filename=thmb_path)
        return thmb_path

    def get_solr_data(self, info_type="collection_items", collection_id=None, resource_type=None, max_rows=None, start_rows=None):

        query_url = self.config.get('index_discovery_query_config', 'solr_endpoint') + "/select?q="
        return_format = 'json'
        
        if info_type == 'coll_items_info':
            
            if max_rows is None:
                raise Exception("Excepiton at get_solr_data for mode 'coll_items_info': 'rows' param cannot be 'None'")

            if start_rows is None:
                raise Exception("Excepiton at get_solr_data for mode 'coll_items_info': 'start' param cannot be 'None'")

            if resource_type is None:
                raise Exception("Exception at get_solr_data for mode 'coll_items_info': resourcetype param cannot be 'None'")
            
            if collection_id is None:
                raise Exception("Missing value of 'collection_id' param in 'get_solr_data()': value is: " + str(collection_id))

            query_coll = "location.coll:" + str(collection_id) + "+AND+" + "search.resourcetype:" + str(resource_type)
            
            query_params = query_coll + "&rows=" + str(max_rows) + "&start=" + str(start_rows) + "&wt=" + return_format

        else:
            raise NotImplementedError("There no functionality implemented for 'info_type=" + info_type + "'")
        
        log.msg("Constructing SOLR query url...")        
        query_url = query_url + query_params

        log.msg(query_url)

        try:
            response = requests.get(query_url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise e
    
    def process_solr_item_data(self, json_data):
        #TODO:  Get only relevant information from SOLR json:
                #       - total count (just to check)
                #       - handle
                #       - repid
                #       - alephID
                #       - dtlID
        
        items_data = pyjq.all('.response.docs[] | {"handle": .\"handle\", "sis_id": \."dc.identifier.repId", "aleph_sysno": .\"dc.identifier.aleph\", "dtl_id": \."dc.identifier.dtl\"}', json_data)    
        
        return items_data
    
    def process_solr_item_count(self, json_data):
        # get number of hits
        num_found = pyjq.one('.response | {"numFound": .\"numFound\"}', json_data)

        return num_found['numFound']