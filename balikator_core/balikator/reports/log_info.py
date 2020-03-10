#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.python import log


def log_batch_info(msg, batch_list):
    """

    :param msg: message, that should be printed out - heading of the log string
    :param batch_list: reference to a workflow object
    :return:
    """
    log.msg("")
    log.msg(msg)
    log.msg( "-" *25)
    for batch in batch_list:
        log.msg("|".ljust(2), "batch_uuid".center(60).rjust(2), "|".ljust(2),
                "batch_name".center(60).rjust(2),
                "|".ljust(2).rjust(2))
        log.msg("|".ljust(2), str(batch.batch_uuid).center(60).rjust(2), "|".ljust(2),
                str(batch.batch_file_name).center(60).rjust(2), "|".ljust(2).rjust(2))
    log.msg("-" * 25)


def log_workflow_info(workflow):
    """

    :param workflow: reference to a workflow object
    :return:
    """
    total_batches = len(workflow.batches_processing)
    batches_ok_count = len(workflow.batches_ok)
    batches_error_count = len(workflow.batches_errors)
    batches_failed_count = len(workflow.batches_failed)
    log.msg(batches_ok_count, "from", total_batches, "finished OK")
    log.msg(batches_error_count, "from", total_batches, "FINISHED WITH ERRORS")
    log.msg(batches_failed_count, "from", total_batches, "FAILED")
    log.msg("-" * 25)

    log_batch_info("OK BATCHES", workflow.batches_ok)
    log_batch_info("ERROR BATCHES", workflow.batches_errors)
    log_batch_info("FAILED BATCHES", workflow.batches_failed)
