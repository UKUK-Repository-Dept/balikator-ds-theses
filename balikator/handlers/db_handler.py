#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.python import log
from datetime import datetime


class db_handler(object):
    # FIXME: This can be deleted, because it's not used at all!
    """
    This class is responsible for handling the database operations.
    """

    def __init__(self, config, connection_int):
        self.config = config
        self.db_int = connection_int
        self.tb_doc = self.db_int.document
        self.tb_batch = self.db_int.batch

    def doc_ready_for_processing(self, document):
        in_live_table = False
        can_change = False

        def doc_in_live_table(document):
            doc_object = self.tb_doc.filter(self.tb_doc.did == document.did).first()
            if doc_object is None:
                live_table = False
            else:
                live_table = True

            return live_table

        def doc_can_change(document):
            # FIXME: Function checks for existence of the document in the document table twice, it is unnecessary
            doc_object = self.tb_doc.filter(self.tb_doc.did == document.did).first()
            if doc_object is None:
                change = True
            else:
                if doc_object.state == 'finished' or doc_object.state == 'error':
                    change = True
                else:
                    change = False

            return change

        in_live_table = doc_in_live_table(document)
        can_change = doc_can_change(document)

        return in_live_table, can_change

    def insert_document_live_table(self, document):
        try:
            tb_doc = self.db_int.document
            tb_doc.insert(did=document.did, kind=document.kind, state='planned', batch_uuid=document.batch_uuid,
                          current_process='new', direction_process=document.doc_process)
        except Exception as e:
            self.db_int.rollback()
            log.msg(e)
            raise e

        self.db_int.commit()

    def get_doc_from_live_table(self, document):
        tb_doc = self.db_int.document
        return tb_doc.filter(tb_doc.did == document.did).first()

    def update_document_live_table(self, document):
        tb_doc = self.db_int.document
        tb_doc.filter(tb_doc.did == document.did).update({'state': 'planned',
                                                          'batch_uuid': document.batch_uuid,
                                                          'current_process': 'new',
                                                          'direction_process': document.doc_process,
                                                          'created': datetime.now(),
                                                          'finished': None})

    def update_batch_state(self, batch, state):
        #FIXME: should work with uuid and db table batch, not a python batch object
        if state == 'finished' or state == 'failed':
            self.tb_batch.filter(self.tb_batch.uuid == str(batch.batch_uuid)).update({'state': state,
                                                                                      'finished': datetime.now()})
        else:
            self.tb_batch.filter(self.tb_batch.uuid == str(batch.batch_uuid)).update({'state': state})

        self.db_int.commit()

        return self.tb_batch.filter(self.tb_batch.uuid == str(batch.batch_uuid)).one().state
