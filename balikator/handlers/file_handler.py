#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import os

from twisted.python import log


class FileHandler(object):
    """
    Class responsible for file handling.
    """
    def __init__(self, config):
        """
        Constructor of file_handler object, accept s one argument, config.
        :param config: ConfigParser object containing parsed balikator.ini file.
        """
        self.config = config

    def get_file_ids(self, path):
        """
        Method parses a document id from each file on a given path. ID is stored in a list if it matches an ID regexp.
        Method then deduplicats the list of ids using the set function, createing a python set from a list.
        :param path: path to a directory in which we want to collect document ids
        :return: set(ids) - set of document ids
        """
        # FIXME: regex will change!
        dir_contents = os.listdir(path)
        ids = []
        for doc_path in dir_contents:
            doc_name = os.path.basename(doc_path)
            # print(doc_name)
            id_match = re.search('\_(\d{4,6})\..*', doc_name)
            if id_match:
                doc_id = id_match.group(1)
                ids.append(doc_id)

        return set(ids)

    def group_files(self, id_set, file_list):
        """
        Method groups files based on the document ids found in its' filename. Method tries to find a match
        between each document id found in id_set and any file in a directory list. If match is found, file is
        appended to a files list (using list comprehension). Every id is used as a dictionary key and corresponding
        files in a list are used as a value.
        :param id_set: set of document ids
        :param file_list: list of file paths
        :return: grouped_files - dict with mapped document ids and file list belonging to it
        """
        # groups files according to their unique doc_id
        grouped_files = {}

        # pro každé id dokumentu najdi všechny výskyty tohoto id v názvu dokumentu
        for doc_id in id_set:
            files = [os.path.basename(path) for path in file_list
                     if re.search('('+doc_id+')', os.path.basename(path))]

            grouped_files[doc_id] = files
        # print(grouped_files)

        return grouped_files

    def write_bitstreams(self, file_info, fh):
        """
        Method goes through text_types option and tries to find a match for each one of them in a provided file name.
        If match is found, method stores the file name in description variable. Method then checks if the provided file
        is an index file. If file is an index file, it sets the bundle variable a 'TEXT' value, indicating that this
        bitestream is a text representation of the scanned image and should be used for indexing in DSpace
        (TEXT is a official bundle name used for this purpose in DSpace). If the file is not an index file,
        bundle is set to 'ORIGINAL'. Method then writes a bitstream string to a contents file
        (represented by file handle fh) and raises an exception if writing fails.
        :param file_info: dict with information about file
        :param fh: file handle leading to a opened contents file ready for writing
        :return: None
        """
        permission = self.config.get('content_permissions', 'permission_flag')
        if file_info['fforbidden'] is False:
            permission_group = self.config.get('content_permissions', 'default_group')
        elif file_info['fforbidden'] is True:
            permission_group = self.config.get('content_permissions', 'administrators')
        else:
            raise Exception("Wrong value of 'fforbidden' key in file_info: " + file_info['fforbidden'])

        bundle = ''
        description = ''
        for option, value in self.config.items('text_types'):

            option_capital = str(option).upper()
            bitstream_match = re.search(option_capital, file_info['ftyp'])
            if bitstream_match:
                description = value

        bundle_match = re.search('_index', file_info['fnazev'])
        if bundle_match:
            bundle = 'TEXT'
            description += ' (Index soubor)'
        else:
            bundle = 'ORIGINAL'

        fid = str(file_info['fid'])
        filename, extension = os.path.splitext(str(file_info['fnazev']))
        try:
            log.msg(fid + extension + "\t" + "bundle:" + bundle + "\t" + "permissions:" + permission + " " + "'" +
                    permission_group + "'" + "\t" + "description:" + description)

            fh.write(fid + extension + "\t" + "bundle:" + bundle + "\t" + "permissions:" + permission + " " + "'" +
                     permission_group + "'" + "\t" + "description:" + description)
            fh.write('\n')
        except Exception as e:
            log.msg(e)
            raise

    def append_thmb_to_contents_file(self, fh, thmb_path):
        permission = self.config.get('content_permissions', 'permission_flag')
        permission_group = self.config.get('content_permissions', 'default_group')
        bundle = 'THUMBNAIL'
        description = 'Náhledový obrázek'
        try:
            log.msg(os.path.basename(thmb_path) + "\t" + "bundle:" + bundle + "\t" + "permissions:" + permission +
                    " " + "'" + permission_group + "'" + "\t" + "description:" + description)

            fh.write(os.path.basename(thmb_path) + "\t" + "bundle:" + bundle + "\t" + "permissions:" + permission +
                     " " + "'" + permission_group + "'" + "\t" + "description:" + description + '\n')
        except:
            raise Exception('Failed to append thumbnail information to contents file.')
