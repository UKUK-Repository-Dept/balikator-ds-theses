#!/usr/bin/env python
# -*- coding: utf-8 -*-

import flask
import os
import re
from flask import render_template, request
from sqlalchemy import inspect, desc, and_, or_, exists, extract
from twisted.python import log

from werkzeug.exceptions import *
from datetime import datetime, date, timedelta
from collections import namedtuple

__all__ = ['make_site']


def make_site(db_int, config, manager, debug=False):
    app = flask.Flask('.'.join(__name__.split('.')[:-1]))
    app.secret_key = os.urandom(16)
    app.debug = debug

    title = "Balikator"

    @app.template_filter('format_ts')
    def format_ts(ts):
        return ts.strftime('%Y-%m-%d %H:%M:%S')

    @app.template_filter('format_phone')
    def format_phone(phone):
        phone = ''.join(re.findall('\d+', phone))
        groups = re.findall(r'.{1,3}', ''.join(reversed(phone)))
        return '+' + ''.join(reversed(' '.join(groups)))

    @app.template_filter('to_alert')
    def state_to_alert(st):
        return {
            'incoming': 'alert-warning',
            'outgoing': 'alert-info',
            'checked': 'alert-info',
            'sent': 'alert-success',
            'finished with errors': 'alert-warning',
            'failed': 'alert-danger',
            'success': 'alert-success',
            'error': 'alert-danger',
            'finished': 'alert-success'
        }[st]

    @app.template_filter('to_icon')
    def state_to_icon(st):
        return {
            'incoming': 'pficon-user',
            'outgoing': 'pficon-enterprise',
            'checked': 'pficon-enterprise',
            'sent': 'pficon-enterprise',
            'failed': 'pficon-error-circle-o',
            'error': 'pficon-error-circle-o',
            'success': 'pficon-ok',
            'finished with errors': 'pficon-enterprise',
            'finished': 'pficon-ok'
        }[st]

    @app.template_filter('truncate_string')
    def truncate_string(st, max_length=100, suffix='...'):
        if len(st) <= max_length:
            return st
        else:
            return ' '.join(st[:max_length+1].split(' ')[0:-1]) + suffix

    @app.template_filter('to_list')
    def to_list(something):
        l = []
        l.append(something)
        return l

    @app.template_filter('dids_to_list')
    def dids_to_list(works):
        l = []
        for work in works:
            l.append(work.did)
        return l

    @app.template_filter('remove_none')
    def none_to_language(st):
        return {
            'None': 'Žádný'
        }[st]

    @app.template_filter('get_length')
    def get_length(item_list):
        return len(item_list)

    @app.template_filter('format_date')
    def format_date(date):
        return date.strftime('%d. %m. %Y')

    def query_batches(state=None, year=None, month=None, day=None, days=None, limit=None):
        batches = db_int.dated_batches

        if year is not None:
            batches = batches.filter(db_int.dated_batches.c.year == year)

        if month is not None:
            batches = batches.filter(db_int.dated_batches.c.month == month)

        if day is not None:
            batches = batches.filter(db_int.dated_batches.c.day == day)

        if state is not None:
            batches = batches.filter(db_int.dated_batches.state == state)

        if days is not None:
            since = datetime.now() - timedelta(days=days)
            batches = batches.filter(db_int.dated_batches.c.finished >= since)

        if limit is not None:
            return batches.limit(limit).all()

        return batches.all()

    def query_documents(year=None, month=None, day=None, days=None, limit=None):
        documents = db_int.dated_documents

    @app.context_processor
    def batch_count_processor():
        def get_batch_docs_stats(b_uuid):
            documents = db_int.document_batch_state_stats
            log.msg("Finding documents for batch uuid:", b_uuid)

            if b_uuid is not None:
                documents = documents.filter(db_int.document_batch_state_stats.c.batch_uuid == b_uuid)
            log.msg(documents.first())
            return documents.first()
        return dict(get_batch_docs_stats=get_batch_docs_stats)


    @app.route('/')
    @app.route('/<state>')
    @app.route('/monthly/<int:year>/<int:month>/')
    @app.route('/monthly/<int:year>/<int:month>/<state>/')
    def index(state=None, year=None, month=None):
        """
        Works defended in this year and processed in SIS today.
        :param state:
        :param year:
        :param month:
        :return:
        """
        wf_status = db_int.workflow.filter_by(name='theses').first().state
        if year is None:
            days_b = db_int.batch_daily_stats.limit(14).all()
            days_d = db_int.document_daily_stats.limit(14).all()
        else:
            days_b = db_int.batch_daily_stats\
                .filter(db_int.batch_daily_stats.c.year == year)\
                .filter(db_int.batch_daily_stats.c.month == month).all()
            days_d = db_int.document_daily_stats\
                .filter(db_int.document_daily_stats.c.year == year)\
                .filter(db_int.document_daily_stats.c.month == month).all()

        total_b_finished = sum(b.finished for b in days_b)
        total_b_errors = sum(b.finished_errors for b in days_b)
        total_b_failed = sum(b.failed for b in days_b)
        total_b = total_b_finished + total_b_errors + total_b_failed

        total_d_finished = sum(d.finished for d in days_d)
        total_d_failed = sum(d.failed for d in days_d)
        total_d_skipped = sum(d.skipped for d in days_d)
        total_d = total_d_finished + total_d_failed + total_d_skipped

        if state is None and year is None:
            batches = query_batches(limit=10)
        elif year is None:
            batches = query_batches(state=state, limit=25)
        else:
            batches = query_batches(state=state, year=year, month=month)

        if year is None:
            documents = query_documents(limit=10)
        else:
            documents = query_documents(year=year, month=month)

        return render_template('main.html', section_title="Index page", **locals())

    @app.route('/process_theses/', methods=['POST', 'GET'])
    # @app.route('/process_theses/start_date/<start_date>')
    # @app.route('/process_theses/end_date/<end_date>')
    # @app.route('/process_theses/<start_date>/<end_date>')
    def process_theses():
        """
        Works defended in a selected year and/or month and processed in SIS during a period of time that can be selected
        from calendar.
        or
        Works defended in a selected year and/or month and processed in SIS during a period of time
        that can be selected in a calendar.
        or
        Works processed in SIS during a period of time that can be selected in a calendar without any constraints
        regarding defence year and/or month.
        :return:
        """
        if request.method == 'GET':
            start_date = flask.request.args.get('start_date')
            end_date = flask.request.args.get('end_date')

            log.msg('START DATE', start_date)
            log.msg('END DATE', end_date)

        return render_template('process_theses.html', section_title="Process theses", **locals())

    @app.route('/daily/')
    def daily():
        return render_template('process_theses.html', section_title="Daily", **locals())

    # we won't be making any changes in sis_db, so there's probably no need for db.rollback()
    # but we will be making changes in db_int, so we need to rollback all uncommited changes when the app stops
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_int.rollback()

    @app.route('/daily/view')
    def daily_view():
        phone = ''
        state = 'sent'
        date = flask.request.args.get('day')

        try:
            year, month, day = map(int, date.split('-'))
        except:
            raise BadRequest('The date you have provided is not valid.')

        return render_template('daily-view.html', **locals())

    @app.route('/write/')
    def write():
        return flask.render_template('write.html', **locals())

    @app.route('/write/send', methods=['POST'])
    def write_send():
        batch_ids_ok = []
        batch_ids_err = []
        if manager.schedule_batch_setup():
            # log.msg(manager.batches_error)
            if len(manager.batches_error) == 0:
                flask.flash(u'Finished setting up batches.', 'success')
                for batch in manager.batches_ok:
                    batch_ids_ok.append(batch.batch_id)
                    flask.flash(str(batch.batch_id), 'success')
            else:
                flask.flash(u'Failed to setup batches.', 'error')
                for batch in manager.batches_error:
                    batch_ids_err.append(batch.batch_id)
                    flask.flash(str(batch.batch_id), 'error')
        else:
            flask.flash(u'Failed to process batch setup.', 'error')

        # # flask.flash(response)

        return flask.redirect('/write/')

    return app
