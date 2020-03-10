#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from twisted.python import log
from balikator.utility.utils import utility
from datetime import datetime


class workflow_doc_finish(object):

    def __init__(self, db_int, db_sis, config, ssh, sftp, scp):
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.ssh = ssh
        self.sftp = sftp
        self.scp = scp
        self.utility = utility(config=self.config)

    def run(self, document):
        """

        :param document:
        :return:
        """
        try:
            log.msg("Auditing document", document.doc_id)
            document.audit_document()
        except Exception as e:
            document.state = 'failed'
            document.error = str(e)
            document.commit()
            raise e

        #try:
        #    log.msg("Cleaning document", document.doc_id)
        #    self.clean_document(document)
        #except Exception as e:
        #    document.state = 'failed'
        #    document.error = str(e)
        #    document.commit()
        #    raise e

        return document.state

    def determine_existing_folder(self, document):
        """

        :param document:
        :return:
        """
        status = self.document_folders_exist(document)

        if status is None:
            return None, None

        if status == 0:
            return document.import_folder, document.out_dir

        if status == 1:
            return document.import_folder, None

        if status == -1:
            return None, document.out_dir

    def clean_document(self, document):
        """Handle document cleaning depending on it's state"""
        errors_remote = self.config.getboolean('document_errors', 'is_remote')
        import_remote = self.config.getboolean('import', 'is_remote')
        output_remote = self.config.getboolean('batch', 'output_is_remote')

        import_folder, output_folder = self.determine_existing_folder(document)

        if self.utility.folder_exists(path=self.config.get('document_errors', 'path'), is_remote=errors_remote,
                                      sftp_client=self.sftp) is False:
            raise Exception('Document errors folder does not exist.')

        if import_folder is not None:
            log.msg("Removing import folder", import_folder)
            self.utility.remove_folder(path=import_folder, is_remote=import_remote,
                                       sftp_client=self.sftp)
        else:
            log.msg("Document doesn't have import folder.")

        if output_folder is not None:
            if document.state == 'finished':
                log.msg("Document is finished. Removing output folder", output_folder)
                self.clean_document_folder(doc=document, output_folder=output_folder, is_remote=output_remote)
                # self.clean_finished_doc(output_folder=output_folder, is_remote=output_remote)
            elif document.state == 'failed':
                log.msg("Document is failed. Moving output folder", output_folder)
                self.clean_document_folder(doc=document, output_folder=output_folder, is_remote=output_remote)
            elif document.state == 'skipped':
                log.msg("Document is skipped. Removing output folder", output_folder)
                self.clean_document_folder(doc=document, output_folder=output_folder, is_remote=output_remote)
            else:
                log.msg('Document has an unknown state:', document.state)
                raise Exception('Document has an unknown state: ' + document.state)
        else:
            log.msg("Document doesn't have an output folder.")

    def document_folders_exist(self, document):
        """

        :param document:
        :return:
        """
        import_exists = self.utility.folder_exists(path=document.import_folder,
                                                   is_remote=self.config.getboolean('import', 'is_remote'),
                                                   sftp_client=self.sftp)

        output_exists = self.utility.folder_exists(path=document.out_dir,
                                                   is_remote=self.config.getboolean('batch', 'output_is_remote'),
                                                   sftp_client=self.sftp)

        if import_exists and output_exists:
            log.msg("Import folder and output folder exists.")
            return 0    # both exist

        elif import_exists and not output_exists:
            log.msg("Import folder exists, output folder doesn't exist.")
            return 1    # import exists

        elif output_exists and not import_exists:
            log.msg("Import folder doesn't exist, output folder exists.")
            return -1   # output exists

        elif not import_exists and not output_exists:
            log.msg("Import folder doesn't exist, output folder doesn't exist.")
            return None

    def clean_document_folder(self, doc, output_folder, is_remote):
        """
        Delete package output folder regardless of its state.
        :param doc: document object from database
        :param output_folder: path to package output folder
        :param is_remote: bool - True if batch output folder is remote
        :return: True
        """
        log.msg("Document is :", doc.state)
        log.msg("Cleaning package from output folder", output_folder)
        log.msg("Is ", output_folder, "remote? ", is_remote)
        if doc.state == 'failed':
            self.utility.move_folder(src=output_folder, dst=self.config.get('document_errors', 'path'),
                                     is_remote=is_remote, sftp_client=self.sftp)
        else:
            self.utility.remove_folder(path=output_folder, is_remote=is_remote, sftp_client=self.sftp)

        return True
