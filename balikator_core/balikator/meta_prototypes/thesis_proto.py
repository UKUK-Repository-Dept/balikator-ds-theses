from balikator.meta_prototypes.meta_proto import meta_proto
import re
from balikator.utility.utils import utility
from twisted.python import log


class thesis_proto(meta_proto):

    def __init__(self, record, config):
        super().__init__(record, config)
        self.schema_name = 'metadata_thesis'
        self.utility = utility(config)
        self._degree_name = self.get_degree_name()
        self._degree_level = self.get_degree_level()
        self._degree_discipline_cs = self.get_degree_discipline(lang='cs')
        self._degree_discipline_en = self.get_degree_discipline(lang='en')
        self._degree_program_cs = self.get_degree_program(lang='cs')
        self._degree_program_en = self.get_degree_program(lang='en')
        self._grade_cs = self.get_grade(lang='cs')
        self._grade_en = self.get_grade(lang='en')
        self._grade_letter = self.get_grade_code()

    def get_degree_name(self):
        log.msg("Getting document degree_name...")
        try:
            result = list()
            qualifier = 'name'

            degree = super().get_data('502', 'a')
            if degree is None:
                return None

            degree_match = re.search('\((.*\.)\)', degree)
            if degree_match:
                degree_name = degree_match.group(1)
                result.append(super().construct_meta_dict(data=degree_name, tag='degree', qualifier=qualifier,
                                                          language=None))
                return result
            else:
                return None
        except:
            raise Exception('Failed to get document degree name from metadata')

    def get_degree_level(self):
        log.msg("Getting document degree_level...")
        try:
            result = list()
            qualifier = 'level'
            language = 'cs_CZ'
            study_level = super().get_data('ds_studyLevel')
            if study_level is None:
                return None

            result.append(super().construct_meta_dict(data=study_level, tag='degree', qualifier=qualifier,
                                                      language=language))

            return result
        except:
            raise Exception('Failed to get document degree level from metadata')

    def get_degree_discipline(self, lang):
        log.msg("Getting document degree_discipline...")
        try:
            result = list()
            qualifier = 'discipline'
            discipline = None

            if lang == 'cs':
                language = 'cs_CZ'
                discipline = super().get_data('ds_studyField_cs')
            elif lang == 'en':
                language = 'en_US'
                discipline = super().get_data('ds_studyField_en')
            else:
                log.msg("THESIS PROTO - get_degree_discipline(): Unsupported language")
                return None

            if discipline is None:
                return None

            result.append(super().construct_meta_dict(data=discipline, tag='degree', qualifier=qualifier,
                                                      language=language))
            return result
        except:
            raise Exception('Failed to get document degree discipline from metadata')

    def get_degree_program(self, lang):
        log.msg("Getting document degree_program...")
        try:
            result = list()
            qualifier = 'program'

            if lang == 'cs':
                language = 'cs_CZ'
                program = super().get_data('ds_studyProgram_cs')
            elif lang == 'en':
                language = 'en_US'
                program = super().get_data('ds_studyProgram_en')
            else:
                log.msg("THESIS PROTO - get_degree_program(): Unsupported language")
                return None

            if program is None:
                return None

            result.append(super().construct_meta_dict(data=program, tag='degree', qualifier=qualifier,
                                                      language=language))
            return result
        except:
            raise Exception('Failed to get document degree program from metadata')

    def get_grade(self, lang):
        log.msg("Getting document grade...")
        try:
            result = list()

            if lang == 'cs':
                language = 'cs_CZ'
                qualifier = 'cs'
                grade = super().get_data('ds_finalGrade_cs')
            elif lang == 'en':
                language = 'en_US'
                grade = super().get_data('ds_finalGrade_en')
                qualifier = 'en'
            else:
                log.msg("THESIS PROTO - get_grade(): Unsupported language")
                return None

            if grade is None:
                return None

            result.append(super().construct_meta_dict(data=grade, tag='grade', qualifier=qualifier, language=language))
            return result
        except:
            raise Exception('Failed to get document grade from metadata')

    def get_grade_code(self):
        log.msg("Getting document grade code...")
        try:
            result = list()
            qualifier = 'code'
            language = None
            grade_code = super().get_data('ds_finalGrade_code')

            if grade_code is None:
                return None

            result.append(super().construct_meta_dict(data=grade_code, tag='grade', qualifier=qualifier,
                                                      language=language))

            return result
        except Exception as e:
            log.msg(e)
            raise Exception('Failed to get document grade LETTER from metadata')
