#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.python import log


class meta_proto(object):

    def __init__(self, record, config):
        self.record = record
        self.conf = config
        self.rec_lang_iso = self.get_record_language(iso=True)
        self.rec_lang = self.get_record_language(iso=False)

    def __str__(self):
        return self.record

    def utility(self):
        return self.utility

    @property
    def config(self):
        return self.conf

    def record_language(self, iso):
        log.msg("Checking value of iso param. ISO=", iso)
        if iso:
            log.msg("Getting language in meta_proto...")
            return self.rec_lang_iso
        else:
            log.msg("Getting language in meta_proto...")
            return self.rec_lang

    def get_data(self, field, subfield=None):
        if self.record[field] is None:
            return None

        if subfield is None:
            return self.record[field].data

        if self.record[field][subfield] is None:
            return None

        return self.record[field][subfield]

    def construct_meta_dict(self, data, tag, qualifier, language):
        if qualifier is None:
            qualifier = 'none'

        if language is None:
            language = 'none'

        return {'element': tag, 'qualifier': qualifier, 'language': language, 'content': data}

    def get_record_language(self, iso):
        if self.record['008'] is None:
            return None

        field_contents = self.record['008'].data
        # print(field_contents)
        language_found = field_contents[35:38]
        lang_code_found = False
        language = None
        if iso:
            config_id = '008_map'
        else:
            config_id = 'lang_string_map'

        for option, value in self.config.items(config_id):
            if option == language_found:
                language = value
                lang_code_found = True

        log.msg("LANGUAGE:", language)
        if not lang_code_found:
            raise Exception("META_PROTO: Languange code for language '{}' "
                            "not found in config file.".format(language_found))
        return language

    def get_fields(self, tag):
        fields = self.record.get_fields(tag)
        if len(fields) == 0:
            return None

        return self.record.get_fields(tag)

