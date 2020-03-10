#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import errno


class DirectoryHandler(object):
    """
    This class is reponsible for directory handling.
    """

    def __init__(self, config):
        """
        Constructor of directory_handler object, accept s one argument, config.
        :param config: ConfigParser object containing parsed balikator.ini file.
        """
        self.config = config

    def create_directory(self, path, name):
        """
        Creates a directory with a given name on a given path.
        :param path: path to directory in which the new directory should be created
        :param name: name of the new directory that should be created
        :return: dirpath - path to a newly created directory
        """
        dirpath = os.path.join(path, name)

        try:
            os.makedirs(dirpath)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        return dirpath
