#!/usr/bin/env python
# -*- coding: utf-8 -*-


from datetime import datetime
from twisted.internet import task, reactor, threads
from twisted.python import log
from balikator.utility.utils import utility
from balikator.reports.mail_info import mail_info

__all__ = ['Manager']


class Manager(object):

    def __init__(self, db_int, db_sis, config, workflow_theses, workflow_obd=None):
        """
        """
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.workflow_theses = workflow_theses
        self.workflow_obd = workflow_obd
        self.theses_loop_interval = float(self.config.get('balikator', 'process_loop_interval'))
        self.obd_loop_interval = None
        self.utility = utility(self.config)
        self.ssh = None
        self.sftp = None
        self.scp = None
        self.stopped = False

    def start_theses(self):
        """
        Sets workflow running in database and starts looping call to run theses workflow periodicaly after given
        amount of time.
        :return: None
        """
        lc = task.LoopingCall(self.run_workflow_theses).start(self.theses_loop_interval)
        lc.addCallbacks(self.set_workflow_stopped)

    def stop_loop(self, lc):
        log.msg("Workflow failed - Stopping looping call.")
        lc.stop()

    def set_workflow_running(self):
        """
        Sets workflow to running state in internal database.
        :return: None
        """

        self.workflow_theses.state = 'running'
        self.workflow_theses.started = datetime.today()
        self.workflow_theses.stopped = None
        self.db_int.commit()

    def send_report_mail(self):
        # send report email
        mail_info_obj = mail_info(workflow=self.workflow_theses, config=self.config)
        try:
            message = mail_info_obj.create_email(from_mail=self.config.get('dspace', 'dspace_mail'),
                                                 to_mail=self.config.get('dspace', 'admin_mail'))
            mail_info_obj.send_email(from_mail=self.config.get('dspace', 'dspace_mail'),
                                     to_mail=self.config.get('dspace', 'admin_mail'),
                                     msg=message)
            return True
        except Exception as e:
            log.msg(e)
            return False

    def set_workflow_failed(self, error):
        # FIXME: Not implemented correctly right now
        # send e-mail only if any batch was actually processed
        # if len(self.workflow_theses.batches_processing) > 0:
        #     # send report mail
        #     if self.send_report_mail():
        #         log.msg("Report mail sent successfully.")
        #     else:
        #         log.msg("Report mail not sent.")

        # close connections
        self.close_connections()

        self.workflow_theses.state = 'failed'
        self.workflow_theses.stopped = datetime.today()
        self.workflow_theses.error = error
        self.db_int.commit()

    def set_workflow_stopped(self):
        # FIXME: Not implemented correctly right now
        # send e-mail only if any batch was actually processed
        # if len(self.workflow_theses.batches_processing) > 0:
        #     # send report email
        #     if self.send_report_mail():
        #         log.msg("Report mail sent successfully.")
        #     else:
        #         log.msg("Report mail not sent.")

        # close connections
        log.msg("Closing SSH connections.")
        self.close_connections()

        # deleting batch workflow objects
        log.msg("WORKFLOW BATCH:", self.workflow_theses.workflow_batch)
        log.msg("WORKFLOW BATCH SETUP:", self.workflow_theses.workflow_batch.workflow_batch_setup)
        log.msg("WORKFLOW BATCH PROCESSING:", self.workflow_theses.workflow_batch.workflow_batch_processing)
        log.msg("WORKFLOW BATCH IMPORT:", self.workflow_theses.workflow_batch.workflow_batch_import)

        # FIXME: WILL THIS DELETE THE OBJECT AND RELEASE THE MEMORY?
        log.msg("Deleting references to batch workflow  objects.")
        log.msg("Deleting batch_setup")
        del self.workflow_theses.workflow_batch.workflow_batch_setup
        log.msg("Deleting batch_processing")
        del self.workflow_theses.workflow_batch.workflow_batch_processing
        log.msg("Deleting batch_import")
        del self.workflow_theses.workflow_batch.workflow_batch_import
        log.msg("Deleting workflow_batch")
        del self.workflow_theses.workflow_batch

        self.workflow_theses.state = 'stopped'
        self.workflow_theses.stopped = datetime.today()
        self.db_int.commit()

    def close_connections(self):
        if self.scp is not None:
            log.msg("Closing SCPClient...")
            self.scp.close()

        if self.sftp is not None:
            log.msg("Closing SFTPClient...")
            self.sftp.close()

        if self.ssh is not None:
            log.msg("Closing SSHClient...")
            self.ssh.close()

        return

    def open_connections(self):
        if not self.is_connected():
            log.msg("SSH STATUS: not active")
            log.msg("Connecting to remote server through SSH...")
            self.ssh = self.utility.create_ssh_client(server=self.config.get("storage", "server"),
                                                      port=self.config.getint("storage", "port"),
                                                      user=self.config.get("storage", "username"),
                                                      password=self.config.get("storage", "password")
                                                      )
            log.msg("Creating SFTPClient...")
            self.sftp = self.utility.create_sftp_client(ssh_session=self.ssh)
            log.msg("Creating SCPClient...")
            self.scp = self.utility.create_scp_client(ssh_session=self.ssh)

            return self.ssh
        else:
            log.msg("SSH STATUS: active")

    def is_connected(self):
        log.msg("Checking if SSH is connected:")
        transport = self.ssh.get_transport() if self.ssh else None
        return transport and transport.is_active()

    def run_workflow_theses(self):
        """
        Runs theses workflow and gathers information about it's state. Updates state of the workflow
        in the internal database.
        :return: None
        """

        if self.config.getboolean('workflow_theses', 'using_remote_server') is True:
            log.msg("WORKFLOW THESES is using remote server...")
            try:
                self.open_connections()
            except Exception as e:
                log.msg("Failed to establish connections.")
                log.msg(e)
                self.set_workflow_failed(error=str(e))
        else:
            pass

        try:

            if self.workflow_theses.state == 'failed':
                log.msg("Workflow Theses failed.")
                log.msg("Workflow needs to be restarted.")
                pass

            elif self.workflow_theses.state == 'stopped':
                log.msg("Workflow Theses is stopped.")
                log.msg("Starting Theses again...")
                self.set_workflow_running()
                log.msg("Workflow Theses started.")
                log.msg(self.ssh, self.scp, self.sftp)
                workflow_state = self.workflow_theses.run(ssh=self.ssh, scp=self.scp, sftp=self.sftp)
                self.workflow_theses.state = workflow_state
                self.db_int.commit()
                self.set_workflow_stopped()

            elif self.workflow_theses.state == 'running':
                log.msg("Workflow Theses is running...")

            else:
                self.set_workflow_running()
                log.msg("Workflow Theses started.")
                workflow_state = self.workflow_theses.run()
                self.workflow_theses.state = workflow_state
                self.db_int.commit()

        except Exception as e:
            log.msg("THESES WORKFLOW: ERROR:\n", e)
            self.set_workflow_failed(error=str(e))

        finally:
            log.msg("THESES WORKFLOW: STATE:", self.workflow_theses.state)
