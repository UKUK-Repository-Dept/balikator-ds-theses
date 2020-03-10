#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import json
import os
import re
import pyjq
from twisted.python import log

class Mapfile(object):

    def __init__(self, path):
        self.__path = path
        self.__mapfile = None
        # self.__create()
    
    @property
    def name(self):
        return os.path.basename(self.__path)

    @property
    def path(self):
        return self.__path
    
    @property
    def mapfile(self):
        return self.__mapfile

    @property
    def mapfile_json(self):
        #return json.dumps(self.__mapfile, indent=4, separators=(',', ':'), ensure_ascii=False)
        return json.dumps(self.__mapfile)

    def create(self):
        # create JSON representation of the CSV file provided in path or return an exception
        csv_dict = dict()
        mapfile_rows = list()
        try:
            with open(self.__path) as csv_file:
                row_names = self.__get_row_names(csv_file)
                print("CSV ROW NAMES:", row_names)
                csv_reader = csv.DictReader(csv_file, fieldnames=row_names, delimiter=';')
                
                for csv_row in csv_reader:
                    #print(csv_row)
                    del csv_row[None]   # remove None key/value pair if it exists (can happen beause of the trailing delimiter on each row of csv file)
                    mapfile_rows.append(csv_row)

                csv_dict['records'] = mapfile_rows
            self.__mapfile = csv_dict
            
            return 0

        except Exception as e:
            log.err(e)
            raise e

    def export(self):
        with open("/opt/dspack/mapfiles/sis/mapfile_json.json", 'w') as fh:
            json.dump(self.__mapfile, fh)
        
        return 0

    def __get_row_names(self, file):

        row_names = list()

        csv_header_row = file.readline()

        normalized_header = self.__normalize_csv_row(csv_header_row)

        row_names = normalized_header.split(';')
        
        return row_names

    def __normalize_csv_row(self, header_string):
        
        print("Normalizing header from CSV file:", header_string)

        print("Removing all non-alphanumeric characters from header...")
        header_string = re.sub('[^0-9a-zA-Z]+', ' ', header_string)
        print("All non-alphanumeric characters removed:", header_string)
        
        print("Removing leading and trailing spaces from string...")
        header_string = header_string.lstrip().rstrip()
        print("Leading and trailing spaces removed:", header_string)
        
        print("Adding ';' as a delimiter for CSV header...")
        header_string = re.sub('[\s]', ';', header_string)
        print("Delimiters added:", header_string)
        
        return header_string

    
    
        
    
    
        
    
    
    
    