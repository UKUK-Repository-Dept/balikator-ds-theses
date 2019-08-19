#!/usr/bin/env python
# -*- coding: utf-8 -*-

from balikator.meta_prototypes.meta_proto import meta_proto
from balikator.utility.utils import utility
from twisted.python import log
import re


class dcterms_proto(meta_proto):

    def __init__(self, record, config):
        super().__init__(record, config)
        self.schema_name = "metadata_dcterms"
        self.utility = utility(config)
        self._date_accepted = self.get_date_accepted()
        self._created = self.get_created()
        self._bibliographic_citation = None
        self._medium = None

    def get_date_accepted(self):
        log.msg("Getting document date_accepted...")
        try:
            dates_accepted = list()
            date = super().get_data('ds_dateAccepted')
            if date is None:
                return None

            matched = re.match('(\d{2})\-(\d{2})\-(\d{4})', date)
            if not matched:
                return None

            year = matched.group(3)
            month = matched.group(2)
            day = matched.group(1)
            date_accepted = year + '-' + month + '-' + day
            dates_accepted.append(super().construct_meta_dict(data=date_accepted, tag='dateAccepted', qualifier=None,
                                                              language=None))
            return dates_accepted
        except:
            raise Exception('Failed to get document acceptance date from metadata')

    def get_created(self):
        log.msg("Getting document date_created...")
        try:
            dates_created = list()

            date_created = super().get_data('264', 'c')
            if date_created is None:
                return None

            dates_created.append(super().construct_meta_dict(data=date_created, tag='created', qualifier=None,
                                                             language=None))
            return dates_created
        except:
            raise Exception('Failed to get document creation date from metadata')



