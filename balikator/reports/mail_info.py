#!/usr/bin/env python
# -*- coding: utf-8 -*-
from twisted.python import log
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class mail_info(object):

    def __init__(self, workflow, config):
        self.workflow = workflow
        self.config = config

    def create_email(self, from_mail, to_mail):
        log.msg("Creating message header...")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Běh workflow Theses ukončen'
        msg['From'] = from_mail
        msg['To'] = to_mail

        html_start = "<html><head></head><body>"
        html_end = "</body></html>"

        def create_workflow_info(html=True):
            """
            Creates workflow information part of the message.
            :param html: if True, creates html msg_part, else creates plaintext msg_part
            :return: msg_part - string representing workflow information part of the message, in html or plaintext
            """
            if html:
                hdr = "<h3>Workflow Theses</h3>"
                state_info = "<p><b>stav:</b>" + self.workflow.workflow.state + "</p>"
                started_info = "<p><b>spuštěno:</b>" + str(self.workflow.workflow.started) + "</p>"
                stopped_info = "<p><b>zastaveno:</b>" + str(self.workflow.workflow.stopped) + "</p>"
                double_stop = "<br><br>"
                batches_count_info = "<p><b>počet zpracovaných dávek:</b>" + \
                                     str(len(self.workflow.batches_processing)) + "</p><br><br>"
            else:
                hdr = "Workflow Theses\n\n"
                state_info = "stav:" + self.workflow.workflow.state + "\n"
                started_info = "spuštěno:" + str(self.workflow.workflow.started) + "\n"
                stopped_info = "zastaveno:" + str(self.workflow.workflow.stopped) + "\n"
                double_stop = "\n\n"
                batches_count_info = "počet zpracovaných dávek:" + str(len(self.workflow.batches_processing)) + "\n\n"

            msg_part = hdr + state_info + started_info + stopped_info + double_stop + batches_count_info

            return msg_part

        def create_batch_info(html=True):
            batches_info = list()
            for batch in self.workflow.batches_processing:
                if html:
                    hdr = "<h4>Dávka" + batch.batch_file_name + "</h4>"
                    state_info = "<p><b>stav:</b>" + batch.batch_state + "</p>"
                    started_info = "<p><b>spuštěno:</b>" + str(batch.batch_started_date) + "</p>"
                    stopped_info = "<p><b>zastaveno:</b>" + str(batch.batch_finished_date) + "</p>"
                    double_stop = "<br><br>"
                    documents_info_t = "<p><b>Informace o dokumentech</b></p><br>"
                    documents_info_hdr = "<table><tr><th></th><th>Zpracované</th><th>Chybné</th><th>Přeskočené</th></tr>"
                    documents_info = create_documents_info(batch_obj=batch, html=True)
                    documents_info_foot = "</table><br>"

                else:
                    hdr = "Dávka" + batch.batch_file_name + "\n"
                    state_info = "stav:" + batch.batch_state + "\n"
                    started_info = "spuštěno:" + str(batch.batch_started_date) + "\n"
                    stopped_info = "zastaveno:" + str(batch.batch_finished_date) + "\n"
                    double_stop = "\n\n"
                    documents_info_t = "Informace o dokumentech\n"
                    documents_info_hdr = "".rjust(20) + "Zpracované".rjust(20) + "Chybné".rjust(20) + "Přeskočené".rjust(20) + "\n"
                    documents_info = create_documents_info(batch_obj=batch, html=False)
                    documents_info_foot = "\n"

                batch_info = hdr + state_info + started_info + stopped_info + double_stop + documents_info \
                    + documents_info_t + documents_info_hdr + documents_info + documents_info_foot
                batches_info.append(batch_info)

            return batches_info

        def create_documents_info(batch_obj, html=True):
            docs_ok_insert = str(len(batch_obj.docs_with_state_process(state='finished', process='insert')))
            docs_ok_update = str(len(batch_obj.docs_with_state_process(state='finished', process='update')))
            docs_ok_delete = str(len(batch_obj.docs_with_state_process(state='finished', process='delete')))
            docs_f_insert = str(len(batch_obj.docs_with_state_process(state='finished', process='insert')))
            docs_f_update = str(len(batch_obj.docs_with_state_process(state='finished', process='update')))
            docs_f_delete = str(len(batch_obj.docs_with_state_process(state='finished', process='delete')))
            docs_skipped_count = str(len(batch_obj.docs_with_state(state='skipped')))
            if html:
                ok_insert = "<td>" + docs_ok_insert + "</td>"
                ok_update = "<td>" + docs_ok_update + "</td>"
                ok_delete = "<td>" + docs_ok_delete + "</td>"
                f_insert = "<td>" + docs_f_insert + "</td>"
                f_update = "<td>" + docs_f_update + "</td>"
                f_delete = "<td>" + docs_f_delete + "</td>"
                row_insert = "<tr><td>insert</td>" + "<td>" + ok_insert + "</td><td>" + f_insert + "</td><td></td></tr>"
                row_update = "<tr><td>update</td>" + "<td>" + ok_update + "</td><td>" + f_update + "</td><td></td></tr>"
                row_delete = "<tr><td>delete</td>" + "<td>" + ok_delete + "</td><td>" + f_delete + "</td><td></td></tr>"
                row_skipped = "<tr><td></td><td></td><td></td><td>" + docs_skipped_count + "</td></tr>"
            else:
                row_insert = "insert".rjust(20) + docs_ok_insert.rjust(20) + docs_f_insert.rjust(20) + "".rjust(20)+"\n"
                row_update = "update".rjust(20) + docs_ok_update.rjust(20) + docs_f_update.rjust(20) + "".rjust(20)+"\n"
                row_delete = "delete".rjust(20) + docs_ok_delete.rjust(20) + docs_f_delete.rjust(20) + "".rjust(20)+"\n"
                row_skipped = "".rjust(20) + "".rjust(20) + "".rjust(20) + docs_skipped_count.rjust(20)+"\n"

            table_contents = row_insert + row_update + row_delete + row_skipped
            return table_contents

        log.msg("Creating workflow information part in HTML...")
        wf_info_html = create_workflow_info()

        log.msg("Creating workflow information part in plaintext...")
        wf_info_text = create_workflow_info(html=False)

        log.msg("Creating batch information part in HTML...")
        b_info_html = create_batch_info()

        log.msg("Creating batch information part in plaintext...")
        b_info_text = create_batch_info(html=False)

        log.msg("Generating whole HTML message...")
        for batch_info in b_info_html:
            wf_info_html = wf_info_html + batch_info

        log.msg("Generating whole plaintext message...")
        for batch_info in b_info_text:
            wf_info_text = wf_info_text + batch_info

        msg_html = html_start + wf_info_html + html_end
        log.msg("HTML MESSAGE:")
        log.msg(msg_html)
        msg_text = wf_info_text
        log.msg("TEXT MESSAGE:")
        log.msg(msg_text)

        txt_part = MIMEText(msg_text, 'plain')
        html_part = MIMEText(msg_html, 'html')
        log.msg("Attaching plaintext and HTML message parts to message container...")
        msg.attach(txt_part)
        msg.attach(html_part)

        return msg

    def send_email(self, from_mail, to_mail, msg):
        s = smtplib.SMTP('localhost')
        try:
            s.sendmail(from_mail, to_mail, msg.as_string())
            s.quit()
            log.msg("Message sent.")
        except Exception as e:
            log.msg("Message not sent.")
            log.msg(e)
            raise e
