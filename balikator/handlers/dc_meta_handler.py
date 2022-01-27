#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from twisted.python import log
from xml.sax.saxutils import escape


class DC_handler(object):
    """
    This class is responsible for handling metadata creation.
    """

    def __init__(self, config):
        """
        Constructor dc_meta_handler object. Accepts 1 argument, config.
        :param config: ConfigParser object containing parsed balikator.ini configuration file
        """
        self.config = config
        self.DC_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'   # XML header used in dspace package metadata file
        self.DC_OPEN_TAG = '<dublin_core>'  # opening dublin core metadata tag
        self.DC_TERMS_OPEN_TAG = '<dublin_core schema="dcterms">'   # opening dcterms metadata tag
        self.DC_THESIS_OPEN_TAG = '<dublin_core schema="thesis">'   # opening thesis metadata tag
        self.DC_UK_OPEN_TAG = '<dublin_core schema="uk">'           # opening uk metadata tag
        self.DC_END_TAG = '</dublin_core>'  # closing dublin core metadata tag
        self.def_lang = self.config.get('dc_config', 'default_lang') # default language
        # default alternative title language
        self.def_alt_title_lang = self.config.get('dc_config', 'default_alt_title_lang')

    def open_meta_file(self, doc_path, meta_format):
        """
        Method sets a correct metadata file name depending on a metadata format provided to it (each metadata format
        has a file named differently). Method then opens a file for writing,
        with that filename on a provided document path. If metadata format provided is not allowed, it raises an
        exception.

        Allowed meta_format values are:
        'dc' - opens a dublin core metadata file
        'dc_terms' - opens a dcterms metadata file
        'uk' - opens a uk metadata file
        :param doc_path: path on which the metadata file should be created
        :param meta_format: metadata format that should be written to a file
        :return: fh - file handle with reference to opened metadata file prepared for writing
        """
        filename = None
        if meta_format == 'dc':
            filename = self.config.get('metafiles', 'default_name')

        if meta_format == 'dcterms':
            filename = self.config.get('metafiles', 'dcterms_name')

        if meta_format == 'thesis':
            filename = self.config.get('metafiles', 'thesis_name')

        if meta_format == 'uk':
            filename = self.config.get('metafiles', 'uk_name')

        if filename is None:
            raise Exception('Failed to set the correct filename for metadata file. Might be caused by unknown'
                            'meta_format. Only valid values are \'dc\', \'dcterms\' and \'thesis\'.')

        log.msg("DOC_PATH:", doc_path, "FILENAME:", filename)
        try:
            if os.path.exists(os.path.join(doc_path, filename)):
                log.msg("Metadata file", os.path.join(doc_path, filename), "already exists.")
                log.msg("Removing existing file.")
                os.remove(os.path.join(doc_path, filename))
                log.msg("Metadata file removed. Creating new one...")
                fh = open(os.path.join(doc_path, filename), 'w', encoding='utf-8')
            else:
                fh = open(os.path.join(doc_path, filename), 'w', encoding='utf-8')
        except:
            raise Exception("Failed to open metadata file" + os.path.join(doc_path, filename) + "for writing.")

        return fh

    def close_meta_file(self, fh):
        """
        Closes a file referenced by a file handle.
        :param fh: file handle holding reference to opened metadata file
        :return: None
        """
        fh.close()

    def open_dc(self, fh, meta_format):
        """
        Writes an opening tag to a metadata file referenced by file handle based on a given metadata format.
        Method rises an exception if not priveded by allowed meta_format value. It writes a new line at the end.

        Allowed metadata formats are:
        'dc' - writes a DC_OPEM_TAG
        'dcterms' - writes a DC_TERMS_OPEN_TAG
        'uk' - wirets a DC_UK_OPEN_TAG

        :param fh: file handle holding reference to a opened metadata file
        :param meta_format: metadata format that should be written to a file
        :return: None
        """
        # writes DC open tag

        if meta_format == 'dc':
            fh.write(self.DC_OPEN_TAG)
        elif meta_format == 'dcterms':
            fh.write(self.DC_TERMS_OPEN_TAG)
        elif meta_format == 'thesis':
            fh.write(self.DC_THESIS_OPEN_TAG)
        elif meta_format == 'uk':
            fh.write(self.DC_UK_OPEN_TAG)
        else:
            raise Exception("Failed to write correct opening tag. It might be cause by unknown meta_format."
                            "Only valid values are 'dc' and 'dc_terms'.")
        fh.write('\n')

    def close_dc(self, fh):
        """
        Writes a closing metadata tag to a metadata file referenced in a file handle.
        :param fh: file handle holding reference to opened metadata file
        :return: None
        """
        # writes DC closing tag

        fh.write(self.DC_END_TAG)
        fh.write('\n')

    def write_element(self, element, fh):
        """
        Writes element to a metadata file reference by a file handle. Method raises an exception if writing fails.
        :param element: dict containing element name, element qualifier, element lanaguage and content
        :param fh: file handle holding a reference to opened metadata file
        :return: None
        """
        element_s = None    # element string
        qualifier_s = None  # qualifier string
        language_s = None   # language string
        content_s = None    # content string
        has_lang_attribute = True
        # for each key in element dict
        for key, value in element.items():
            str_value = str(value)
            # check if key is one of the following (we do not want some wrong keys in our dict)
            if key not in ['content', 'language', 'qualifier', 'element']:
                raise Exception("Unknown key in element dict.")
            # check if value of language key is 'none' or something else and set the boolean variable has_lang_attribute
            if element['language'] == 'none':
                has_lang_attribute = False
            else:
                has_lang_attribute = True
            # construct content, qualifier, language and content strings
            element_s = 'element="{}"'.format(element['element'])
            qualifier_s = 'qualifier="{}"'.format(element['qualifier'])
            language_s = 'language="{}"'.format(element['language'])
            content_s = element['content']

            # escape XML-invalid characters from content string
            content_s = escape(content_s, {"\"": "&quot;", "\'": "&apos;"})

        # check whether the language is defined (has_lang_attribute == False)
        if not has_lang_attribute:
            s = '<dcvalue ' + element_s + ' ' + qualifier_s + '>' + content_s + '</dcvalue>'
        else:
            s = '<dcvalue ' + element_s + ' ' + qualifier_s + ' ' + language_s + '>' + content_s + '</dcvalue>'

        try:
            fh.write(s)
            fh.write('\n')
        except:
            raise Exception("Failed to write element to file:", fh)

    def write_header(self, fh):
        """
        Writes metadata header to a file referenced by a file handle
        :param fh: file handle holding reference to opened metadata file
        :return: None
        """
        # writes dc metadata header
        try:
            fh.write(self.DC_HEADER)
            fh.write('\n')
        except:
            raise Exception("DC_handler: Failed to write DC_HEADER to file:", fh)

    def write_metadata(self, doc, fh, meta_format):
        """
        Method writes metadata file to a file referenced by file handle. Method first writes a default metadata header,
        then checks the provided meta_format value and decides what metadata will be written to a file.
        Metadata that should be written are stored in document object and the variable from they will be take depends
        on a provided metadata format. If metadata for a given metadata format are not found, method raises exception.
        If metadata are found, method checks if structure of the data stored has a valid structure
        (list of dictionaries) and calls a method that writes elements, giving an element dictionary as one of
        arbitrary parameters. If data doesn't have a valid structure, method raises an exception.

        When metadata writing is finished, method closes metadata file referenced by a file handle.
        :param doc: document object
        :param fh: file handle holding a reference to opened metadata file
        :param meta_format: metadata format
        :return: None
        """
        print("WRITE METADATA reporting!")
        meta_object = None

        self.write_header(fh)

        if meta_format == 'dc':
            meta_object = doc.dc_proto
            self.open_dc(fh, meta_format)

        if meta_format == 'dcterms':
            meta_object = doc.dcterms_proto
            self.open_dc(fh, meta_format)

        if meta_format == 'thesis':
            meta_object = doc.thesis_proto
            self.open_dc(fh, meta_format)

        if meta_format == 'uk':
            meta_object = doc.uk_proto
            self.open_dc(fh, meta_format)

        # print("DOC WRITE PARAMS:", write_params)

        if meta_object is None:
            raise Exception("Failed to select valid metadata object.")

        meta_list = self.get_all_metadata(prototype=meta_object)

        for item in meta_list:
            if isinstance(item, list):
                for element in item:
                    if isinstance(element, dict):
                        # print("ELEMENT", element, "is a dict!")
                        self.write_element(element, fh)
                    else:
                        raise Exception("Element ", element, "is not a dict!")
            else:
                raise Exception("Item", item, "is not a list!")
        self.close_dc(fh)

    def get_all_metadata(self, prototype):
        meta_list = []
        for k, v in vars(prototype).items():
            if k.startswith('_'):
                if v is None:
                    continue
                log.msg("Key:", k, "Value:", v)
                meta_list.append(v)

        return meta_list
