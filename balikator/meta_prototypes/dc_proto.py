#!/usr/bin/env python
# -*- coding: utf-8 -*-

from balikator.meta_prototypes.meta_proto import meta_proto
from balikator.utility.utils import utility
from twisted.python import log
import re


class dc_proto(meta_proto):

    def __init__(self, record, config):
        super().__init__(record, config)
        self.schema_name = 'dublin_core'
        self.utility = utility(config)
        self._language_iso = self.get_language(iso=True, lang=None)
        self._language_string = self.get_language(iso=False, lang='cs')
        self._type = self.get_type()
        self._title = self.get_title()
        self._title_translated = self.get_title_translated()
        # FIXME: Just for now, we need to know, how to get alternative translated title first
        # self._title_alternative = self.get_title_alternative()
        # self._title_alternative_translated = None
        self._creator = self.get_creator()
        self._issue_date = self.get_date_issued()
        self._embargoEndDate = self.get_date_embargoEnd()
        self._contributor_advisor = self.get_contributor_advisor()
        self._contributor_referee = self.get_contributor_referee()
        self._publisher = self.get_publisher()
        self._subject_cs = self.get_keywords(lang='cs')
        self._subject_en = self.get_keywords(lang='en')
        self._identifier_repId = self.get_identifier_repid()
        self._identifier_aleph = self.get_identifier_aleph()
        self._description_faculty_cs = self.get_description_faculty(lang='cs')
        self._description_faculty_en = self.get_description_faculty(lang='en')
        self._description_department_cs = self.get_description_department(lang='cs')
        self._description_department_en = self.get_description_department(lang='en')
        self._abstract_cs = self.get_abstract(lang='cze')
        self._abstract_en = self.get_abstract(lang='eng')

    def get_type(self):
        log.msg("Getting document type...")
        try:
            # TODO: Should we get an english translation??
            dc_type = list()
            work_type = super().get_data('ds_workType')

            if work_type is None:
                return None

            type_normalized = str(work_type).lower()
            dc_type.append(super().construct_meta_dict(data=type_normalized, tag='type', qualifier=None,
                                                       language='cs_CZ'))
            return dc_type
        except:
            raise Exception('Failed to get document type from metadata')

    def get_language(self, iso, lang=None):
        log.msg("Getting document language with iso={}".format(iso))
        try:
            dc_language = list()
            if iso is True:
                qualifier = 'iso'
                language = None
            else:
                if lang == 'cs':
                    language = 'cs_CZ'
                elif lang == 'en':
                    language = 'en_US'
                elif lang is None:
                    language = None
                else:
                    raise Exception('DC_PROTO - get_language(): Unsupported language')

                qualifier = None

            lang_data = super().record_language(iso=iso)
            log.msg("GET_LANGUAGE:", lang_data)

            log.msg("Constructing language meta dictionary...")
            dc_language.append(super().construct_meta_dict(data=lang_data, tag='language',
                                                           qualifier=qualifier, language=language))
            return dc_language
        except:
            raise Exception('Failed to get document language with iso='+iso)

    def get_title(self):
        log.msg("Getting document title...")
        try:
            dc_title = list()
            main_title = super().get_data('245', 'a')
            remainder = super().get_data('245', 'b')
            language = super().get_data('245', '9')

            if main_title is None:
                return None

            if remainder is None:
                log.msg("MAIN TITLE:", main_title)
                main_title = main_title.rstrip("/")
                log.msg("MAIN TITLE - after RSTRIP:", main_title)
                dc_title.append(super().construct_meta_dict(data=main_title, tag='title', qualifier=None,
                                                            language=super().record_language(iso=True)))
                return dc_title

            whole_title = ' '.join([main_title, remainder])
            # FIXME: Remove trailing '/' from the end of the title
            log.msg("WHOLE TITLE:", whole_title)
            whole_title = whole_title.rstrip("/")
            log.msg("WHOLE TITLE - AFTER RSTRIP:", whole_title)

            dc_title.append(super().construct_meta_dict(data=whole_title, tag='title', qualifier=None,
                                                        language=self.utility.lang_to_iso(lang_str=language)))
            return dc_title
        except:
            raise Exception('Failed to get document title from metadata')

    def get_title_translated(self):
        log.msg("Getting document title_translated...")
        try:
            translated_titles = list()
            main_title_trans = super().get_data('246', 'a')
            if main_title_trans is None:
                return None

            alt_title_fields = super().get_fields('246')
            i = 0
            while i < len(alt_title_fields):
                alt_title_trans = alt_title_fields[i]['a']
                # first alternative title in this case is always 'en'
                language = alt_title_fields[i]['9']
                translated_title = super().construct_meta_dict(data=alt_title_trans, tag='title',
                                                               qualifier='translated',
                                                               language=self.utility.lang_to_iso(lang_str=language))

                translated_titles.append(translated_title)
                i += 1
            return translated_titles
        except:
            raise Exception('Failed to get document title_translated from metadata')

    def get_title_alternative(self):
        log.msg("Getting document title_alternative")
        # FIXME: Return None for now, until we'll have a better notion of where we can find an alternative title
        return None

    def get_creator(self):
        log.msg("Getting document creator...")
        try:
            creators = list()
            creator = super().get_data('100', 'a')

            if creator is None:
                return None

            creators.append(super().construct_meta_dict(data=creator, tag='creator', qualifier=None, language=None))
            return creators
        except:
            raise Exception('Failed to get document creator from metadata')

    def get_date_issued(self):
        log.msg("Getting document issue date...")
        #
        # Issue date is the same as acceptance date in case of theses
        #
        tag = 'date'
        qualifier = 'issued'

        try:
            result = list()
            date_issued = super().get_data('264', 'c')
            if date_issued is None:
                return None

            result.append(super().construct_meta_dict(data=date_issued, tag=tag, qualifier=qualifier, language=None))
            return result
        except:
            raise Exception('Failed to get document acceptance date from metadata')
    
    def get_date_embargoEnd(self):
        log.msg("Getting document's emgargo end date...")

        tag = 'date'
        qualifier = 'embargoEndDate'

        try:
            result = list()
            date_embargoEnd = super().get_data('ds_embargoEndDate')
            if date_embargoEnd is None:
                return None
            
            result.append(super().construct_meta_dict(data=date_embargoEnd, tag=tag, qualifier=qualifier, language=None))
            return result
        except:
            raise Exception('Failed to get document\'s embargo end date from metadata')

    def get_contributor_advisor(self):
        log.msg("Getting document advisor...")
        try:
            advisors = list()

            advisor = super().get_fields('700')

            if advisor is None:
                return None

            for field in advisor:
                if field is None:
                    return None

                role = field['4']
                if role == 'ths':
                    role = 'advisor'
                    name = field['a']
                    advisors.append(super().construct_meta_dict(data=name, tag='contributor', qualifier=role,
                                                                language=None))
                else:
                    pass
            if len(advisors) == 0:
                return None
            return advisors
        except:
            raise Exception('Failed to get document advisor from metadata')

    def get_contributor_referee(self):
        log.msg("Getting document referee...")
        try:
            referees = list()

            referee = super().get_fields('700')

            if referee is None:
                return None

            for field in referee:
                if field is None:
                    return None
                role = field['4']
                if role == 'opn':
                    role = 'referee'
                    name = field['a']
                    referees.append(super().construct_meta_dict(data=name, tag='contributor', qualifier=role,
                                                                language=None))
                else:
                    pass

            if len(referees) == 0:
                return None
            return referees
        except:
            raise Exception('Failed to get document referee from metadata')

    def get_publisher(self):
        log.msg("Getting document publisher...")
        publisher = None
        try:
            publishers = list()

            publisher = super().get_data('260', 'b')
            if publisher is None:
                try:
                    publishers = self.get_publisher_alternative()
                    return publishers

                except Exception as e:
                    log.msg("DC_PROTO - get_publisher: ", e)
                    return None

            if publisher[-1] == ',':
                log.msg("DC_PROTO - get_publisher: Found a ',' in string")
                publisher = publisher[:-1]
            publishers.append(super().construct_meta_dict(data=publisher, tag='publisher', qualifier=None, language=None))

            return publishers
        except:
            raise Exception('Failed to get document publisher from metadata')

    def get_publisher_alternative(self):
        """
        Getting publisher from alternative metadata - university name (from config file) and faculty name
        (from metadata export) and combining it into one string.
        :return:
        """
        publisher_info = list()
        whitespace = ' '
        tag = 'publisher'
        qualifier = None
        language = 'cs_CZ'
        publisher = None

        log.msg("Getting alternative publisher information...")
        try:
            faculty_name = super().get_data('ds_facultyName_cs')
        except Exception as e:
            raise e
        try:
            uni_name = self.config.get('basic_info', 'university_name_cs')
        except Exception as e:
            raise e

        publisher = uni_name + ',' + whitespace + faculty_name

        publisher_info.append(super().construct_meta_dict(data=publisher, tag=tag, qualifier=qualifier,
                                                          language=language))

        return publisher_info

    def get_keywords(self, lang):
        log.msg("Getting document keywords...")
        keywords_list = list()
        processed_keywords = list()
        keywords = None

        def split_keywords(k_words):
            k_list = re.split('; |, |/', k_words)
            # k_list = [w for w in str(keywords_sub).split(" ")]
            return k_list

        def strip_unwanted_chars(k_word):
            log.msg("Stripping unwanted characters from keyword", k_word)
            k_word = str(k_word).lstrip('.,')
            k_word = str(k_word).rstrip('.,')
            log.msg("Stripped string:", k_word)
            return k_word
        try:
            if lang == 'cs':
                language = 'cs_CZ'
                keywords = super().get_data('ds_keywords_cs')
            elif lang == 'en':
                language = 'en_US'
                keywords = super().get_data('ds_keywords_en')
            else:
                log.msg("DC_PROTO - get_keywords(): Unsupported language")
                return None

            if keywords is None:
                return None

            keywords_split = split_keywords(keywords)
            if len(keywords_split) == 0:
                log.msg("DC_PROTO - get_keywords(): Processed keywords list is empty.")
                return None

            for word_temp in keywords_split:
                processed_keywords.append(strip_unwanted_chars(k_word=word_temp))

            for word in processed_keywords:
                keywords_list.append(super().construct_meta_dict(data=word, tag='subject', qualifier=None,
                                                                 language=language))

            return keywords_list
        except:
            raise Exception('Failed to get document keywords from metadata')

    def get_identifier_repid(self):
        log.msg("Getting document repId...")
        try:
            identifiers_repid = list()
            qualifier = 'repId'
            rep_id = super().get_data('repId')
            if rep_id is None:
                return None

            identifiers_repid.append(super().construct_meta_dict(data=rep_id, tag='identifier', qualifier=qualifier,
                                                                 language=None))
            return identifiers_repid
        except:
            raise Exception('Failed to get document repId from metadata')

    def get_identifier_did(self):
        log.msg("Getting document did...")
        try:
            identifiers_did = list()
            qualifier = 'didId'
            did = super().get_data('didId')
            if did is None:
                return None

            identifiers_did.append(super().construct_meta_dict(data=did, tag='identifier', qualifier=qualifier,
                                                               language=None))
            return identifiers_did
        except:
            raise Exception('Failed to get document did from metadata')

    def get_identifier_aleph(self):
        log.msg("Getting document aleph_sysno...")
        try:
            identifiers_aleph = list()
            qualifier = 'aleph'
            aleph_id = super().get_data('001')
            if aleph_id is None:
                return None

            identifiers_aleph.append(super().construct_meta_dict(data=aleph_id, tag='identifier', qualifier=qualifier,
                                                                 language=None))
            return identifiers_aleph
        except:
            raise Exception('Failed to get document aleph sysno from metadata')

    def get_description_faculty(self, lang):
        log.msg("Getting document faculty...")
        try:
            descriptions_faculty = list()
            qualifier = 'faculty'
            faculty_name = None
            if lang == 'cs':
                language = 'cs_CZ'
                faculty_name = super().get_data('ds_facultyName_cs')
            elif lang == 'en':
                language = 'en_US'
                faculty_name = super().get_data('ds_facultyName_en')
            else:
                log.msg("DC_PROTO - get_description_faculty(): Unsupported language")
                return None

            if faculty_name is None:
                return None

            descriptions_faculty.append(super().construct_meta_dict(data=faculty_name, tag='description',
                                                                    qualifier=qualifier, language=language))

            return descriptions_faculty
        except:
            raise Exception('Failed to get document faculty name from metadata')

    def get_description_faculty_abbr(self):
        log.msg("Getting document faculty abbreviation...")
        try:
            descriptions_faculty_abbr = list()
            qualifier = "faculty_abbr"
            language = 'cs_CZ'

            faculty_abbr = super().get_data('ds_facultyAbbr')

            if faculty_abbr is None:
                return None

            descriptions_faculty_abbr.append(super().construct_meta_dict(data=faculty_abbr, tag='description',
                                                                         qualifier=qualifier, language=language))

            return descriptions_faculty_abbr
        except:
            raise Exception('Failed to get document faculty abbreviation from metadata')

    def get_description_department(self, lang):
        log.msg("Getting document department...")
        try:
            descriptions_department = list()
            qualifier = 'department'

            if lang == 'cs':
                language = 'cs_CZ'
                department = super().get_data('ds_departmentName_cs')
            elif lang == 'en':
                language = 'en_US'
                department = super().get_data('ds_departmentName_en')
            else:
                log.msg("DC_PROTO - get_description_faculty(): Unsupported language")
                return None

            if department is None:
                return None

            descriptions_department.append(super().construct_meta_dict(data=department, tag='description',
                                                                       qualifier=qualifier, language=language))
            return descriptions_department
        except:
            raise Exception('Failed to get document department name from metadata')

    def get_abstract(self, lang):
        log.msg("Getting document abstract...")
        try:
            abstracts = list()
            language = None
            abstract = None

            f_abstracts = super().get_fields('520')
            if f_abstracts is None:
                return None

            for field in f_abstracts:
                if field['8'] == lang:
                    language = super().config.get('language_map', lang)
                    abstract = field['a']

            if language is None:
                pass
            if abstract is None:
                return None
            log.msg("ABSTRACT:\n")
            log.msg(abstracts)
            abstracts.append(
                super().construct_meta_dict(data=abstract, tag='description', qualifier='abstract', language=language))

            return abstracts
        except:
            raise Exception('Failed to get document abstract from metadata')
