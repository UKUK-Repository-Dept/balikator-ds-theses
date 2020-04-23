#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from twisted.python import log
from balikator.utility.utils import utility
from datetime import datetime
from distutils.dir_util import copy_tree


class workflow_doc_import(object):

    def __init__(self, db_int, db_sis, config, sftp, scp):
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.sftp = sftp
        self.scp = scp
        self.utility = utility(config=self.config)

    def run(self, document):

        if document.current_process == 'import':
            # create import folder if it doesn't exist
            try:
                log.msg("WORKFLOW_DOC_IMPORT: Creating import folder", document.import_folder)
                self.create_import_folder(document)
            except Exception as e:
                log.msg(e)
                document.error = str(e)
                document.errors.append(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

            # check if package is complete, import package to DSpace server
            try:
                log.msg('WORKFLOW_DOC_IMPORT: Starting move_to_import_folder() function...')
                new_process = self.move_to_import_folder(document)
                document.current_process = new_process
                document.state = 'finished_import'
                document.commit()
            except Exception as e:
                log.msg(e)
                document.error = str(e)
                document.errors.append(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        return document.state

    def create_import_folder(self, document):

        try:
            if self.config.getboolean('import', 'is_remote') is True:
                self.utility.create_dir_remote(document.import_folder, sftp=self.sftp)
            else:
                self.utility.create_dir_local(document.import_folder)
        except Exception as e:
            raise e

    def move_to_import_folder(self, doc):
        # check if package is complete, copy package to DSpace import folder (either remote or local)

        def has_all_work_files():
            # check if work files are in the package directory
            log.msg("Checking if document", doc.doc_id, 'has all work files present in package...')
            for f_name, f_info in doc.work_files.items():
                log.msg("Checking file", f_info['local_renamed_file'])
                if not os.path.exists(f_info['local_renamed_file']):
                    # if one of the files doesn't exist in package dir, return False immediately
                    return False
            return True

        def has_thumbnail_file():
            # check if thumbnail file is present
            if doc.thmb_file is None:
                log.msg("Document doesn't have any thumbnail file, because it hasn't been not generated.")
                return True
            else:
                if not os.path.exists(doc.thmb_file):
                    return False

            return True

        def has_contents_file():
            # check if contents file is present
            log.msg("Checking if document", doc.doc_id, 'has contents file present in package...')
            if not os.path.exists(doc.cf_location):
                return False  # return False if contents file is missing
            return True

        def has_all_metadata_files():
            # check if metadata files are present
            log.msg("Checking if document", doc.doc_id, 'has all metadata files present in package...')
            for option, f_name in self.config.items('metafiles'):
                if not os.path.exists(os.path.join(doc.out_dir, f_name)):
                    # if one of the metadata files that should be present in package dir (according to .ini file)
                    # are not present, return False immediately
                    return False
            return True

        def has_valid_handle_file():
            log.msg("Checking if document", doc.doc_id, 'has valid handle file present in package...')
            if not os.path.exists(os.path.join(doc.out_dir,
                                               self.config.get('balikator', 'default_handle_name'))):
                return False
            else:
                with open(os.path.join(doc.out_dir, self.config.get('balikator', 'default_handle_name')),
                          mode='r') as fh:
                    line = fh.readline()
                    handle = line
                    # check if handle in "handle file" is matching handle of the previously processed document
                    if doc.handle != handle:
                        return False
                    else:
                        return True

        def package_complete():

            # check if document has all work files
            if not has_all_work_files():
                log.msg("Document ", doc.doc_id, "is missing work files...")
                return 'missing work files'

            # check if document has contents file
            if not has_contents_file():
                log.msg("Document ", doc.doc_id, "is missing contents file...")
                return 'missing contents file'

            # check if document has all metadata files
            if not has_all_metadata_files():
                log.msg("Document ", doc.doc_id, "is missing metadata files...")
                return 'missing metadata files'

            if not has_thumbnail_file():
                log.msg("Document ", doc.doc_id, "is missing thumbnail file... ")
                return 'missing thumbnail file'

            # check if handle file is present if document had been previously imported to DSpace
            # if document has no handle assigned in database, lets assume that it didn't get processed in
            # our workflow, so it should not be in the DSpace repository.
            # <J. R.> 25. 1. 2018
            if doc.workflow_process == 'insert':
                log.msg("Document ", doc.doc_id, "is marked for insert.")
                if doc.handle is not None:
                    log.msg("Document ", doc.doc_id, "HAS A HANDLE ASSIGNED!")
                    if not has_valid_handle_file():
                        log.msg("Document ", doc.doc_id, "is missing valid handle file BUT IT SHOULD HAVE IT!")
                        return 'missing valid handle file'
                else:
                    log.msg("Document ", doc.doc_id, "DOES NOT HAVE A HANDLE ASSIGNED. New one will be assigned during"
                                                     "import.")
            else:
                log.msg("Document", doc.doc_id, "is marked for ", doc.workflow_process)

            log.msg("Document ", doc.doc_id, "has a COMPLETE package...")
            return 'complete'

        def copy_package_to_remote():
            remote_folder = doc.import_folder

            try:
                log.msg("Copying package", doc.out_dir, "to remote import folder", remote_folder)
                self.scp.put(doc.out_dir, remote_path=remote_folder, recursive=True)
            except Exception as e:
                log.msg(e)
                raise Exception("SCPClient: Failed to copy package file to remote import folder.")

        def copy_package_to_local():
            local_folder = os.path.join(doc.import_folder, doc.doc_id)
            try:
                log.msg("Copying package", doc.out_dir, "to local import folder", local_folder)
                log.msg(os.path.dirname(local_folder))
                copy_tree(src=doc.out_dir, dst=local_folder)
            except Exception as e:
                log.msg(e)
                raise Exception("Failed to copy package to local import folder", local_folder)

        # get package status
        package_status = package_complete()
        log.msg("MOVE TO IMPORT FOLDER - package status:", package_status)

        # check package status
        if package_status != 'complete':
            raise Exception("Package incomplete,", package_status)

        # copy package file to remote or local import folder
        if self.config.getboolean('import', 'is_remote') is True:
            log.msg("IMPORT FOLDER IS REMOTE: ", self.config.get('import', 'is_remote'))
            log.msg('Importing package to REMOTE directory...')
            # remote directory
            try:
                copy_package_to_remote()
            except Exception as e:
                log.msg(e)
                raise e
        else:
            log.msg('Importing package to LOCAL directory...')
            # local directory
            try:
                copy_package_to_local()
            except Exception as e:
                log.msg(e)
                raise e

        return 'ingest'
