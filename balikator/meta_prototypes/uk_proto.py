#!/usr/bin/env python
# -*- coding: utf-8 -*-

from balikator.meta_prototypes.meta_proto import meta_proto
from balikator.utility.utils import utility
from twisted.python import log


class uk_proto(meta_proto):

    def __init__(self, record, config):
        super().__init__(record, config)
        self.schema_name = 'uk'
        self.language_iso = super().record_language
        self.utility = utility(config)
        self._uk_theses_type = self.get_uk_theses_type()
        self._uk_org_taxonomy_cs = self.get_uk_taxonomy_organization(lang='cs')
        self._uk_org_taxonomy_en = self.get_uk_taxonomy_organization(lang='en')
        self._uk_deg_disc_cs = self.get_uk_degree_discipline(lang='cs')
        self._uk_deg_disc_en = self.get_uk_degree_discipline(lang='en')
        self._uk_deg_prog_cs = self.get_uk_degree_program(lang='cs')
        self._uk_deg_prog_en = self.get_uk_degree_program(lang='en')
        self._uk_fac_name_cs = self.get_uk_fac_name(lang='cs')
        self._uk_fac_name_en = self.get_uk_fac_name(lang='en')
        self._uk_fac_abbr_cs = self.get_uk_fac_abbr(lang='cs')
        self._uk_abstract_cs = self.get_uk_abstract(lang='cze')
        self._uk_abstract_en = self.get_uk_abstract(lang='eng')
        self._uk_file_availability = self.get_uk_file_availability()
        self._uk_publication_place = self.get_uk_publication_place()
        self._grantor = self.get_grantor()
        # self._uk_fac_abbr_en = self.get_uk_fac_abbr(lang='en') #FIXME: Get the english abbreviation from SIS

    def get_uk_theses_type(self):
        log.msg("Getting thesis type...")
        try:
            # TODO: Should we get an english translation??
            uk_work_type = list()
            work_type = super().get_data('ds_workType')

            if work_type is None:
                return None

            type_normalized = str(work_type).lower()
            uk_work_type.append(super().construct_meta_dict(data=type_normalized, tag='thesis', qualifier='type',
                                                            language='cs_CZ'))
            return uk_work_type
        except:
            raise Exception('Failed to get document type from metadata')

    def get_uk_taxonomy_organization(self, lang):
        log.msg("Getting faculty and department of the work...")
        try:
            org_taxonomy = list()
            tag = 'taxonomy'

            if lang == 'cs':
                language = 'cs_CZ'
                qualifier = 'organization-cs'
                fac_part = super().get_data('ds_facultyName_cs')
                dpt_part = super().get_data('ds_departmentName_cs')
            elif lang == 'en':
                language = 'en_US'
                qualifier = 'organization-en'
                fac_part = super().get_data('ds_facultyName_en')
                dpt_part = super().get_data('ds_departmentName_en')
            else:
                log.msg("UK_PROTO - get_uk_taxonomy_organization(): Unsupported language")
                return None

            if fac_part is None:
                return None

            if dpt_part is None:
                return None

            taxonomy = fac_part + '::' + dpt_part

            org_taxonomy.append(super().construct_meta_dict(data=taxonomy, tag=tag, qualifier=qualifier,
                                                            language=language))
            return org_taxonomy
        except Exception as e:
            log.msg('UK_PROTO - get_uk_taxonomy_organization(): Error occured:', e)
            raise Exception('Failed to get organization taxonomy from metadata.')

    def get_uk_degree_discipline(self, lang):
        log.msg("Getting UK degree-discipline in {}".format(lang))
        try:
            result = list()
            tag = 'degree-discipline'
            discipline = None

            if lang == 'cs':
                language = 'cs_CZ'
                qualifier = 'cs'
                discipline = super().get_data('ds_studyField_cs')
            elif lang == 'en':
                language = 'en_US'
                qualifier = 'en'
                discipline = super().get_data('ds_studyField_en')
            else:
                log.msg("UK_PROTO - get_uk_degree_discipline(): Unsupported language")
                return None

            if discipline is None:
                return None

            result.append(super().construct_meta_dict(data=discipline, tag=tag, qualifier=qualifier, language=language))
            return result
        except:
            raise Exception('UK_PROTO - uk_degree_discipline():Failed to get document degree discipline from metadata')

    def get_uk_degree_program(self, lang):
        log.msg("Getting UK degree-program in {}".format(lang))
        try:
            result = list()
            tag = 'degree-program'
            program = None

            if lang == 'cs':
                language = 'cs_CZ'
                qualifier = 'cs'
                program = super().get_data('ds_studyProgram_cs')
            elif lang == 'en':
                language = 'en_US'
                qualifier = 'en'
                program = super().get_data('ds_studyProgram_en')
            else:
                log.msg("UK_PROTO - get_uk_degree_program(): Unsupported language")
                return None

            if program is None:
                return None

            result.append(super().construct_meta_dict(data=program, tag=tag, qualifier=qualifier, language=language))
            return result
        except:
            raise Exception('UK_PROTO - uk_degree_discipline():Failed to get document study program from metadata')

    def get_uk_dep_name(self, lang):
        log.msg("Getting UK department name in {}".format(lang))
        try:
            result = list()
            tag = 'department-name'
            dep_name = None

            if lang == 'cs':
                language = 'cs_CZ'
                qualifier = 'cs'
                dep_name = super().get_data('ds_departmentName_cs')
            elif lang == 'en':
                language = 'en_US'
                qualifier = 'en'
                dep_name = super().get_data('ds_departmentName_en')
            else:
                log.msg("UK_PROTO - get_uk_dep_name(): Unsupported language")
                return None

            if dep_name is None:
                return None

            result.append(super().construct_meta_dict(data=dep_name, tag=tag, qualifier=qualifier, language=language))
            return result
        except:
            raise Exception('UK_PROTO - uk_dep_name():Failed to get document department name from metadata')

    def get_university_name(self, lang):
        log.msg("Getting university name in {}".format(lang))
        try:
            result = list()
            tag = 'university-name'
            university_name = self.config.get('basic_info', 'university_name_'+lang)

            if lang == 'cs':
                language = 'cs_CZ'
                qualifier = 'cs'
            elif lang == 'en':
                language = 'en_US'
                qualifier = 'en'
            else:
                log.msg("UK_PROTO - get_university_name(): Unsupported language")
                return None

            if university_name is None:
                log.msg("UK_PROTO: Couldn't find university name in config file.")
                return None

            result.append(super().construct_meta_dict(data=university_name, tag=tag, qualifier=qualifier,
                                                      language=language))
            return result

        except Exception as e:
            raise Exception('UK_PROTO - get_university_name(): Failed to get university name from config file')

    def get_uk_publication_place(self):
        log.msg("Getting UK publication place.")
        try:
            result = list()
            tag = 'publication-place'
            publication_place = super().get_data('ds_publication_place')

            language = 'cs_CZ'
            qualifier = None

            if publication_place is None:
                log.msg("UK_PROTO - get_publication_place(): Didn't find a publication place in metadata.")
                return None

            result.append(super().construct_meta_dict(data=publication_place, tag=tag, qualifier=qualifier,
                                                      language=language))
            return result
        except Exception as e:
            raise Exception('UK_PROTO - get_publication_place(): Failed to get publication place from metadata.')

    def get_grantor(self):
        """

        :return:
        """
        grantor_info = list()
        whitespace = ' '
        tag = 'grantor'
        qualifier = None
        language = 'cs_CZ'

        log.msg("Getting alternative publisher information...")
        try:
            faculty_name = super().get_data('ds_facultyName_cs')
        except Exception as e:
            raise e
        try:
            uni_name = self.config.get('basic_info', 'university_name_cs')
        except Exception as e:
            raise e

        try:
            department = super().get_data('ds_departmentName_cs')
        except Exception as e:
            raise e

        if faculty_name is None:
            log.msg("DC_PROTO - get_publisher_alternative() - Cannot get alternative publisher information - "
                    "missing faculty information from metadata.")
            raise Exception('DC_PROTO - get_publisher_alternative() - Cannot get alternative publisher information - '
                            'missing faculty information from metadata.')
        if uni_name is None:
            log.msg("DC_PROTO - get_publisher_alternative() - Cannot get alternative publisher information - "
                    "missing university name in config file.")
            raise Exception("DC_PROTO - get_publisher_alternative() - Cannot get alternative publisher information - "
                            "missing university name in config file.")

        if department is None:
            grantor = uni_name + ',' + whitespace + faculty_name
        else:
            grantor = uni_name + ',' + whitespace + faculty_name + ',' + whitespace + department

        grantor_info.append(super().construct_meta_dict(data=grantor, tag=tag, qualifier=qualifier,
                                                        language=language))

        return grantor_info


    def get_uk_fac_name(self, lang):
        log.msg("Getting UK faculty name in {}".format(lang))
        try:
            result = list()
            tag = 'faculty-name'
            fac_name = None

            if lang == 'cs':
                language = 'cs_CZ'
                qualifier = 'cs'
                fac_name = super().get_data('ds_facultyName_cs')
            elif lang == 'en':
                language = 'en_US'
                qualifier = 'en'
                fac_name = super().get_data('ds_facultyName_en')
            else:
                log.msg("UK_PROTO - get_uk_fac_name(): Unsupported language")
                return None

            if fac_name is None:
                return None

            result.append(super().construct_meta_dict(data=fac_name, tag=tag, qualifier=qualifier, language=language))
            return result
        except:
            raise Exception('UK_PROTO - uk_fac_name():Failed to get document faculty name from metadata')

    def get_uk_fac_abbr(self, lang):
        log.msg("Getting UK faculty abbreviation in {}".format(lang))
        try:
            result = list()
            tag = 'faculty-abbr'
            fac_abbr = None

            if lang == 'cs':
                language = 'cs_CZ'
                qualifier = 'cs'
                fac_abbr = super().get_data('ds_facultyAbbr')
            elif lang == 'en':
                language = 'en_US'
                qualifier = 'en'
                fac_abbr = super().get_data('ds_facultyAbbr_en')
            else:
                log.msg("UK_PROTO - get_uk_fac_abbr(): Unsupported language")
                return None

            if fac_abbr is None:
                return None

            result.append(super().construct_meta_dict(data=fac_abbr, tag=tag, qualifier=qualifier, language=language))
            return result
        except:
            raise Exception('UK_PROTO - uk_fac_abbr():Failed to get faculty abbreviation from metadata')

    def get_uk_abstract(self, lang):
        log.msg("Getting document abstract...")
        try:
            abstracts = list()
            language = None
            abstract = None

            if lang == 'cze':
                qualifier = 'cs'
            elif lang == 'eng':
                qualifier = 'en'
            else:
                raise Exception('UK PROTO - get_uk_abstract(): Unsuported language' + lang)

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
                super().construct_meta_dict(data=abstract, tag='abstract', qualifier=qualifier, language=language))

            return abstracts
        except:
            raise Exception('Failed to get document abstract from metadata')

    def get_uk_file_availability(self):
        """
        Get work's files availability information from record.
        This information should be available at 'ds_work_availability' tag of the MARC record.
        :return: 
        """
        log.msg("Getting work's files availability code...")
        try:
            result = list()
            tag = 'file-availability'
            availability = None
            language = None
            qualifier = None

            availability = super().get_data('ds_work_availability')

            if availability is None:
                return None

            result.append(super().construct_meta_dict(data=availability, tag=tag, qualifier=qualifier, language=language))
            return result
        except:
            raise Exception('UK_PROTO - uk_file_availability():Failed to get document\'s availability from metadata')
