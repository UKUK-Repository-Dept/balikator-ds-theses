#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import shutil
import json
from datetime import datetime
from balikator.utility.utils import utility
from balikator.meta_prototypes.dc_proto import dc_proto
from balikator.meta_prototypes.dcterms_proto import dcterms_proto
from balikator.meta_prototypes.thesis_proto import thesis_proto
from balikator.meta_prototypes.uk_proto import uk_proto
from balikator.handlers.dc_meta_handler import DC_handler
from balikator.handlers.file_handler import FileHandler
from twisted.python import log


class workflow_doc_package(object):

    def __init__(self, db_int, db_sis, config, sftp, scp):
        self.db_int = db_int
        self.db_sis = db_sis
        self.config = config
        self.sftp = sftp
        self.scp = scp
        self.utility = utility(self.config)
        self.dc_handler = DC_handler(self.config)
        self.file_handler = FileHandler(self.config)

    def run(self, document):
        log.msg("DOC_PACKAGE connections:")
        log.msg("SFTP:", self.sftp)
        log.msg("SCP:", self.scp)
        if document.current_process == 'new':
            log.msg("Trying to create metadata prototypes...")
            try:
                new_process = self.create_metadata_prototypes(document)
                document.current_process = new_process
                document.commit()
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        if document.current_process == 'metadata_files':
            # create metadata files from prototype metadata objects which should handle all metadata needed
            log.msg("Trying to create metadata files...")
            try:
                new_process = self.create_metadata_files(document)
                document.current_process = new_process
                document.commit()
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        if document.current_process == 'files_information':
            # get information about work files from SIS database table dipl2did
            log.msg("Trying to gather information about work files...")
            try:
                new_process = self.get_files_information(document)
                document.current_process = new_process
                document.commit()
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        if document.current_process == 'contents_file':
            # create contents file for document
            log.msg("Trying to create contents file...")
            try:
                new_process = self.create_contents_file(document)
                document.current_process = new_process
                document.commit()
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        if document.current_process == 'work_files':
            # get work files from external storage
            log.msg("Trying to gather work files from storage...")
            try:
                new_process = self.move_files_to_package(document)
                document.current_process = new_process
                document.commit()
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        if document.current_process == 'package':
            # rename original files using metadata files
            # create handle file if document has handle assigned
            # create one package ready for import to DSpace
            log.msg("Trying to prepare a package...")
            try:
                state = self.prepare_package(document)
                document.current_process = 'import'
                document.state = state
                document.commit()
            except Exception as e:
                document.errors.append(e)
                document.error = str(e)
                log.msg(e)
                document.state = 'failed'
                document.finished = datetime.today()
                document.commit()

        return document.state

    def create_metadata_prototypes(self, doc):
        """
        Creates metadata prototype objects for every metadata format/namespace we use for document description
        and stores the reference to it in the document object.
        :param doc: document object
        :return: string('metadata_files'): finished process identification
        """
        try:
            doc.dc_proto = dc_proto(doc.record_object, self.config)
        except Exception as e:
            log.msg(e)
            raise e
        try:
            doc.dcterms_proto = dcterms_proto(doc.record_object, self.config)
        except Exception as e:
            log.msg(e)
            raise e
        try:
            doc.thesis_proto = thesis_proto(doc.record_object, self.config)
        except Exception as e:
            log.msg(e)
            raise e

        try:
            doc.uk_proto = uk_proto(doc.record_object, self.config)
        except Exception as e:
            log.msg(e)
            raise e

        if doc.dc_proto is None:
            raise Exception("Failed to create Dublin Core metadata prototype.")

        if doc.dcterms_proto is None:
            raise Exception("Failed to create DC Terms metadata prototype.")

        if doc.thesis_proto is None:
            raise Exception("Failed to create Thesis metadata prototype.")

        return 'metadata_files'

    def create_metadata_files(self, doc):
        """
        Creates metadata files for every metadata format/namespace we use for document description. If any of the
        file creation task fails, it raises an exception.
        :param doc: document object
        :return: string('files_information'): finished process identification
        """
        try:
            log.msg("DOC OUT DIR:", doc.out_dir)
            fh = self.dc_handler.open_meta_file(doc_path=doc.out_dir, meta_format='dc')
            self.dc_handler.write_metadata(doc, fh=fh, meta_format='dc')
            self.dc_handler.close_meta_file(fh=fh)
        except Exception as e:
            raise e

        try:
            fh = self.dc_handler.open_meta_file(doc_path=doc.out_dir, meta_format='dcterms')
            self.dc_handler.write_metadata(doc, fh=fh, meta_format='dcterms')
            self.dc_handler.close_meta_file(fh=fh)
        except Exception as e:
            raise e

        try:
            fh = self.dc_handler.open_meta_file(doc_path=doc.out_dir, meta_format='thesis')
            self.dc_handler.write_metadata(doc, fh=fh, meta_format='thesis')
            self.dc_handler.close_meta_file(fh=fh)
        except Exception as e:
            raise e

        try:
            fh = self.dc_handler.open_meta_file(doc_path=doc.out_dir, meta_format='uk')
            self.dc_handler.write_metadata(doc, fh=fh, meta_format='uk')
            self.dc_handler.close_meta_file(fh=fh)
        except Exception as e:
            raise e

        return 'files_information'

    def get_files_information(self, doc):
        """190993
        Gets information about the theses files from database and stores it in the document object for later use.
        Only information about active files from storage are stored. Active document is document, that has attribute
        farchivni equal to NULL in the dipl2doc table.
        :param doc: document object
        :return: string('contents_file') - finished process identification
        """

        def file_availability_check():

            work_availability_conf_list = self.config.options('work_availability_map')

            work_availability_codes = [str(code).upper() for code in work_availability_conf_list]
            log.msg("WORK AVAILABILITY CODES IN CONFIG:", work_availability_codes)
            # unavailable_files = list()

            if doc.work_availability in work_availability_codes:
                # no file is unavailable
                unavailable_files = str(self.config.get('work_availability_map', doc.work_availability)).split(sep=',')
                log.msg("Unavailable files:", unavailable_files)
            else:
                raise Exception("Unknown work availability code: " + doc.work_availability)

            return unavailable_files

        def get_translated_ftyp(file_db):
            """

            :param file_db:
            :return:
            """

            try:
                return self.db_sis.tdpriloha.filter_by(kod=file_db.ftyp).one().prevod
            except Exception as e:
                # in some cases there's no row for a given ftyp (for example:
                # files with ftyp=DPR12, DPR13) - that means there's no
                # prevod value for this ftyp.

                # In that case it would be best to get just the base ftyp
                # without a integer at the end of the string and try to search
                # for prevod value again.
                # 
                # Example:
                #   | FTYP  | BASE_FTYP | PREVOD |
                #   | DPR12 |    DPR    |   PR   | 
                log.err("ERROR: FILE HAS A FTYP THAT DOES NOT EXIST IN TDPRILOHA TABLE: " + str(file_db.ftyp))
                ftyp_base = re.sub('\d{1,2}', '', file_db.ftyp)

                try:
                    return self.db_sis.tdpriloha.filter_by(kod=ftyp_base).one().prevod
                except Exception as e:
                    log.msg(e)
                    raise e

        # FIXME: Check if new logic works with all kinds of file types (all kinds of FTYP values)
        def old_file_version_stored(file_obj, f_dict):

            current_orig_ftyp = str(file_obj.ftyp).lstrip('D')

            for key, inner_dict in f_dict.items():
                stored_orig_ftyp = str(inner_dict['ftyp']).lstrip('D')
                if current_orig_ftyp == stored_orig_ftyp:
                    if str(file_obj.ftyp).startswith('D'):
                        # new version of the same file (begins with D)
                        log.msg("CURRENT FTYP: ", file_obj.ftyp)
                        log.msg("STORED FTYP: ", inner_dict['ftyp'])
                        log.msg("CURRENT FID: ", file_obj.fid)
                        log.msg("STORED FID: ", inner_dict['fid'])
                        # This should return fid of stored file that has to be removed from info dict
                        return inner_dict['fid']
                    else:
                        log.msg("CURRENT FTYP: ", file_obj.ftyp)
                        log.msg("STORED FTYP: ", inner_dict['ftyp'])
                        log.msg("CURRENT FID: ", file_obj.fid)
                        log.msg("STORED FID: ", inner_dict['fid'])
                        # This should return None
                        return None
                else:
                    # ftyp values are not matching, it's not the same type of file
                    log.msg("CURRENT FTYP: ", file_obj.ftyp)
                    log.msg("STORED FTYP: ", inner_dict['ftyp'])
                    return None

        try:

            dipl2doc = self.db_sis.dipl2doc  # make dipl2doc a searchable table object
            # information we need: did
            # information that we need to gather: FID, FTYP, FNAZEV, DID
            files_doc = dipl2doc.filter_by(did=doc.doc_id).all()

            forbidden_files = file_availability_check()

            if files_doc is None:
                raise Exception("Didn't find any information about theses files in SIS database.")
            f_info = {}
            for file in files_doc:

                translated_ftyp = get_translated_ftyp(file)

                if file.farchivni is None:  # get information only about active files in storage (farchivni == None(NULL))
                    orig_f_path = self.get_file_location(fid=file.fid)
                    meta_f_path = self.get_file_location(fid=file.fid, f_type='meta')
                    if orig_f_path is None:
                        raise Exception("Failed to get the path to original file in storage.")

                    if meta_f_path is None:
                        raise Exception("Failed to get the path to metadata file in storage.")

                    file_forbidden = False
                    if translated_ftyp in forbidden_files:
                        file_forbidden = True

                    old_version_fid = old_file_version_stored(file, f_info)

                    log.msg("File: {}\tOld version stored: {}".format(file.fnazev, old_version_fid))
                    # check if old version of a file is stored in f_info dict,
                    # e.g. if currently processed file has ftyp begins with 'D', and there is the same file
                    # stored in dict but with ftyp not beginning with 'D', remove the currently stored file
                    # and store currently processed file
                    try:
                        if old_version_fid is not None:
                            log.msg("FILE FID: ", file.fid)
                            log.msg("CURRENTLY PROCESSED FILE FTYP: ", file.ftyp)
                            log.msg("Found old version of the file store in file info dict, deleting old version info.")
                            f_info.pop(old_version_fid)
                        else:
                            log.msg("FILE FID: ", file.fid)
                            log.msg("CURRENTLY PROCESSED FILE FTYP: ", file.ftyp)
                            log.msg("No older version of the file stored in the file info dict...")
                            pass
                    except:
                        raise

                    # construct path to storage folder
                    # FIXED: fnazev is not unique identifier! Results in rewriting values of the f_info dictionary!
                    # FIX: file.fid is used as unique identifier
                    f_info.update({
                        file.fid: {
                            'did': file.did,
                            'ftyp': file.ftyp,
                            'translated_ftyp': translated_ftyp,
                            'fnazev': file.fnazev,
                            'fforbidden': file_forbidden,
                            'orig_file': orig_f_path,
                            'meta_file': meta_f_path,
                            'fid': file.fid,
                        }
                    })
                else:
                    continue

                log.msg("FILE INFO:\n")
                log.msg(json.dumps(f_info))
            try:
                doc.work_files = f_info
                log.msg("GET FILES INFORMATION:\n", doc.work_files)
            except Exception as e:
                log.msg(e)
                raise e
        except Exception as e:
            log.msg(e)
            raise e

        return 'contents_file'

    def create_contents_file(self, doc):
        """
        Writes document bitstreams to a contents file. Each line int contents file is one bitstream belonging to one
        work. Raises and exception if: file doesn't open properly, if list of document files is empty, or it
        cannot write to a file.
        :param doc: document object
        :return: string - 'finished' when no exception is raised
        """
        print("Creating contents file...")
        # create one line for each file belonging to one work
        # the line should consist of: document name (with extension),document bundle name(ORIGINAL,TEXT_REPRESENTATION),
        # document permissions (format: -[r|w] 'group name', description (short description of the file - content-wise),
        # primary (used to specify primary bitstream (not sure if it is optional or not)
        cf_location = os.path.join(doc.out_dir, self.config.get("balikator", "default_cf_name"))

        # store contents file location to document object
        doc.cf_location = cf_location
        log.msg("WORKFLOW_DOC(create_contents_file): CF_LOCATION:", cf_location)
        log.msg("WORKFLOW_DOC(create_contents_file): DOC FILES PATH:", doc.work_files)
        if os.path.exists(cf_location):
            # delete old file
            log.msg("Found contents file in the output folder.")
            log.msg("Removing old contents file and creating a new one...")
            os.remove(cf_location)

        fh = open(cf_location, 'w', encoding='utf-8')

        sorted_contents = self.sort_doc_contents(files_dict=doc.work_files)
        log.msg("SORTED CONTENT DICT:", sorted_contents)

        if len(sorted_contents) == 0:
            raise Exception("There are no files information to write into contents file")

        for name_tuple in sorted_contents:
            log.msg("'INDEX - NAME' TUPLE:", name_tuple)
            file_name = name_tuple[1]
            try:
                self.file_handler.write_bitstreams(file_info=file_name, fh=fh)
            except Exception as e:
                raise e

        return 'work_files'


    def assign_content_importance(self, importance_value, multiplicity_index):
        """

        :param str importance_value: importance value of given thesis file
        :param multiplicity_index: multiplicity index of thesis file
        :return:
        """
        # and ftyp has a multiplicity index (e. g. FTYP = PO8 (base FTYP = PO, multiplicity index = 8),
        # construct a index value for sorting based on this key:
        #
        # if number of digits of multiplicity index is 1 (e. g. '8'):
        #   index = str(importance_value (from config)) + str(0) + str(multiplicity index)
        #
        # if number of digits of multiplicity index is 2 (e. g. '12'):
        #   index = str(importance_value (from config)) + str(multiplicity index)
        #
        # if ftyp does not have a multiplicity index (no digit at the end of 'ftyp', e. g. ftyp = 'TX'):
        #   index = str(importance_value (from config) + str(0) + str(0)
        #
        # Examples:
        #
        # PO2   = (importance_value =   9)    +   ('0')   +   ('2')   = '902'   => converted to 902
        # PR4   = (importance_value =   4)    +   ('0')   +   ('4')   = '404'   => converted to 404
        # PR12  = (importance_value =   4)    +   ('12')              = '412'   => converted to 412
        # ZH    = (importance_value =  10)    +   ('0')   +   ('0')   = '1000'  => converted to 1000
        if multiplicity_index is None:
            index = str(importance_value) + str(0) + str(0)

        elif (len(str(multiplicity_index))) == 1:
            index = str(importance_value) + str(0) + str(multiplicity_index)

        elif (len(str(multiplicity_index))) == 2:
            index = str(importance_value) + str(multiplicity_index)

        else:
            index = None

        return index

    def sort_doc_contents(self, files_dict):
        """
        Return a list of tuples with work content files sorted in a way they appear in the docs 'content' file
        :param files_dict: dict with information about files belonging to a certain document (work)
        :return: sorted_tuple_list: list of tuples. Each tuple contains index and filename. Tuples are sorted by index.
        """
        result_dict = {}
        for option, value in self.config.items('content_importance_map'):
            option_capital = str(option).upper()
            for file_id, information in files_dict.items():

                # find option in config that matches translated_ftyp (from table tdpriloha, atribute "prevod"
                type_match = re.search(option_capital, information['translated_ftyp'])
                type_duplicity_match = re.search('(\d{1,2}$)', information['ftyp'])
                index_match = re.search('_index', information['fnazev'])

                # if match is found in ftyp
                if type_match and not index_match:  # this should evaluate to False if file_name is an index file

                    if type_duplicity_match is not None:

                        log.msg("File", information['fnazev'], "with ftyp", information['ftyp'],
                                "and TRANSLATED FTYP", information['translated_ftyp'],
                                "HAS A MULTIPLICITY index of ", type_duplicity_match.group(1), "in FTYP.")
                        index = self.assign_content_importance(value, multiplicity_index=type_duplicity_match.group(1))

                    else:
                        log.msg("File", information['fnazev'], "with ftyp", information['ftyp'],
                                "and TRANSLATED FTYP", information['translated_ftyp'],
                                "does not have multiplicity index in FTYP.")
                        index = self.assign_content_importance(value, multiplicity_index=None)

                    log.msg("FOUND TYPE", option_capital, "in file", information['fnazev'])

                    if index is None:
                        log.msg("workflow_doc_package: sort_doc_contents(): Wierd index number: ", + file_id,
                                " ", information['ftyp'], " TRANSLATED FTYP: ", information['translated_ftyp'])
                        raise Exception('workflow_doc_package: sort_doc_contents(): Wierd index number: None')

                    result_dict[int(index)] = information

                elif type_match and index_match:
                    value_index = self.config.get('content_index_importance_map', option_capital + '_index')
                    if type_duplicity_match is not None:
                        log.msg("File", information['fnazev'], "with ftyp", information['ftyp'],
                                "HAS A MULTIPLICITY index of ", type_duplicity_match.group(1), "in FTYP.")
                        index = self.assign_content_importance(value_index,
                                                               multiplicity_index=type_duplicity_match.group(1))
                    else:
                        log.msg("File", information['fnazev'], "with ftyp", information['ftyp'],
                                "does not have multiplicity index in FTYP.")

                        index = self.assign_content_importance(value_index, multiplicity_index=None)

                    if index is None:
                        log.msg("workflow_doc_package: sort_doc_contents(): Wierd index number: ", + file_id,
                                " ", information['ftyp'])
                        raise Exception('workflow_doc_package: sort_doc_contents(): Wierd index number.')

                    log.msg("FOUND TYPE", option_capital, "in index file", information['fnazev'])
                    result_dict[int(index)] = information
                else:
                    continue

        sorted_tuple_list = sorted(result_dict.items())
        print("SORTED TUPLE LIST\n", sorted_tuple_list)

        return sorted_tuple_list

    def get_file_location(self, fid, f_type='orig'):
        """
        Gets documents' file FID and constructs a path to file in storage directory. Returns constructed path.
        :param fid: FID identifier of the document file
        :param f_type: type of thw file we wont to construct path to [orig|meta]
        :return: f_path: path to file in storage
        """
        storage_path = self.config.get('balikator', 'work_storage_path')
        fid_match = re.match("(\d{2})(\d{3})(\d{4,5})", str(fid))
        ORIG_SUFFIX = self.config.get('storage_file_suffixes', 'orig_file')
        META_SUFFIX = self.config.get('storage_file_suffixes', 'meta_file')
        if not fid_match:
            raise Exception("Didn't find a matching string in file FID. Unknown FID format.")
        else:
            log.msg("Found matching string in file FID, constructing storage path.")
            for option, value in self.config.items('storage_work_types'):
                if value == fid_match.group(1):
                    folder_root = str(option).upper()
                    folder_1 = fid_match.group(1) + fid_match.group(2)
                    folder_2 = fid_match.group(3)
                    storage_sub_folder = os.path.join(folder_root, folder_1, folder_2)
                    if f_type == 'orig':
                        file_name = str(folder_1) + str(folder_2) + ORIG_SUFFIX
                    elif f_type == 'meta':
                        file_name = str(folder_1) + str(folder_2) + META_SUFFIX
                    else:
                        raise Exception('Cannot construct filename of the work file. Unknown file type:', f_type,
                                        'Possible values: [orig|meta].')
                    f_path = os.path.join(storage_path, storage_sub_folder, file_name)
                    log.msg("File storage path: ", f_path)
                    return f_path
                else:
                    # if current value doesn't match fid prefix, ignore it
                    pass

    def move_files_to_package(self, doc):
        """
        Copies work files that are necessary for successful package creation to documents' package directory.
        Raises an exception if required package files are not present in list of required files in document object.
        Files are copied using SCP or plain copy function. SCP is used if storage is on a remote server, copy is
        used in case the storage is on a local machine.
        :param doc: document object
        :return: string - 'finished' when no exception is raised
        """
        # FIXME: There should be a more generic function for copying files from local or remote folder
        def copy_file_from_remote():

            for f_name, f_info in doc.work_files.items():

                try:
                    log.msg("Getting file", f_info['orig_file'], "from remote storage...")
                    self.scp.get(f_info['orig_file'], local_path=doc.out_dir, preserve_times=True)
                    f_info.update({'local_orig_file': os.path.join(doc.out_dir, os.path.basename(f_info['orig_file']))})
                except Exception as e:
                    log.msg(e)
                    raise Exception("SCPClient: Failed to get original file from remote storage.")

        def copy_file_from_local():
            for f_name, f_info in doc.work_files.items():

                if not os.path.exists(f_info['orig_file']):
                    raise Exception("Original file doesn't exist in the local storage.")

                try:
                    log.msg("Copying file", f_info['orig_file'], "from local storage...")
                    shutil.copy2(src=f_info['orig_file'], dst=doc.out_dir)
                    f_info.update({'local_orig_file': os.path.join(doc.out_dir, os.path.basename(f_info['orig_file']))})
                except:
                    raise Exception("Failed to copy original file to document package.")

        print("Moving files from storage...")

        if self.config.getboolean("storage", "is_remote") is True:
            log.msg("Moving from REMOTE storage...")
            try:
                copy_file_from_remote()
            except Exception as e:
                log.msg(e)
                raise e
        else:
            log.msg("Moving from LOCAL storage...")
            try:
                copy_file_from_local()
            except Exception as e:
                log.msg(e)
                raise e

        return 'package'

    def prepare_package(self, doc):
        # rename original files using metadata files, remove metadata files
        # create handle file if document has handle assigned

        def append_thumb_to_contents(thmb_path):
            """
            Appends thumbnail image to contents file.
            :return: None
            """
            if os.path.exists(doc.cf_location):
                fh = open(doc.cf_location, mode='a')
                self.file_handler.append_thmb_to_contents_file(fh=fh, thmb_path=thmb_path)
                fh.close()
            else:
                log.msg("Cannot append thumbnail to contents file {}.".format(doc.cf_location), "Contents file doesn't exist.")
                return

        def create_thumbnail():
            """
            Creates thumbnail from the first page of the document text, if there is any.
            :return: None
            """

            # if document is not public, use a premade thumbnail instead of creating one from the fulltext file
            log.msg("WORK AVAILABILITY CODE: ", doc.work_availability)
            if doc.work_availability == 'N':
                log.msg("{} - Práce je neveřejná - KÓD {} - POUŽÍVÁM PŘEDPŘIPRAVENÝ NÁHLEDOVÝ OBRÁZEK".format(doc.doc_id, doc.work_availability))
                # thmb_path = self.config.get('thumbnails','custom_cs')
                # append custom CZECH thumbnail
                if os.path.exists(self.config.get('thumbnails', 'custom_cs')):
                    log.msg("Adding custom czech thumbnail from {}".format(self.config.get('thumbnails', 'custom_cs')))
                    append_thumb_to_contents(thmb_path=self.config.get('thumbnails', 'custom_cs'))
                    shutil.copy(self.config.get('thumbnails', 'custom_cs'), doc.out_dir)
                # append custom ENGLISH thumbnail
                if os.path.exists(self.config.get('thumbnails', 'custom_en')):
                    log.msg("Adding custom czech thumbnail from {}".format(self.config.get('thumbnails', 'custom_en')))
                    append_thumb_to_contents(thmb_path=self.config.get('thumbnails', 'custom_en'))
                    shutil.copy(self.config.get('thumbnails', 'custom_en'), doc.out_dir)

                doc.thmb_file = None
                return doc.thmb_file

            # get file location
            for f_name, f_info in doc.work_files.items():
                log.msg("TYP SOUBORU (FTYP): ", f_info['ftyp'])
                if f_info['ftyp'] == 'TX' or f_info['ftyp'] == 'DTX':
                    # we found text of the work, get it's location
                    text_loc = f_info['local_renamed_file']
                    if os.path.exists(text_loc):
                        log.msg("Path exists: {}".format(text_loc))
                        
                        try:
                            log.msg(os.listdir(os.path.dirname(text_loc)))
                            thmb_path = self.utility.create_thumb_from_pdf(pdf_path=text_loc)
                            f_info.update({'thmb_path': thmb_path})
                            append_thumb_to_contents(thmb_path=thmb_path)
                            doc.thmb_file = thmb_path
                        except Exception as e:
                            log.msg(e)
                            # FIXME: Error is not raised when thumbnail generation fails
                            # raise Exception('Failed to generate thumbnail file.')
                    else:
                        log.msg("Thumbnail not created because source file {} doesn't exist.".format(text_loc))
                else:
                    pass
            return doc.thmb_file

        def rename_files():
            for f_id, f_info in doc.work_files.items():
                filename, extension = os.path.splitext(str(f_info['fnazev']))
                new_filename = str(f_id) + extension
                # open metadata file and get information about original file belonging to it
                log.msg("PREPARE PACKAGE: renaming file", os.path.basename(f_info['local_orig_file']), "to",
                        new_filename)
                try:
                    shutil.move(f_info['local_orig_file'], os.path.join(doc.out_dir, new_filename))
                    log.msg("File", f_info['local_orig_file'], 'renamed to', os.path.join(doc.out_dir, new_filename))
                    log.msg("Storing information about renamed file to document object...")
                    doc.work_files[f_id].update({'local_renamed_file': os.path.join(doc.out_dir, new_filename)})
                except Exception as e:
                    log.msg(e)
                    raise Exception('Failed to rename work file', os.path.basename(f_info['local_orig_file']), "to",
                                    new_filename)

        def create_handle_file():
            handle_file = os.path.join(doc.out_dir, self.config.get('balikator', 'default_handle_name'))
            if os.path.exists(handle_file):
                log.msg("PREPARE PACKAGE: Handle file already exists. Removing old one...")
                os.remove(handle_file)
                log.msg("PREPARE PACKAGE: Creating a new handle file", handle_file)
            else:
                log.msg("PREPARE PACKAGE: Handle file not found. Creating one...")

            try:
                with open(handle_file, mode='w') as fh:
                    fh.write(doc.handle)
                fh.close()
            except Exception as e:
                raise Exception("Failed to create a handle file.")

            return handle_file

        try:
            rename_files()
        except Exception as e:
            raise e

        try:
            thmb_file = create_thumbnail()
            log.msg("Work thumbnail:", thmb_file)
        except Exception as e:
            raise e

        try:
            if doc.workflow_process == 'insert':
                if doc.handle is not None:
                    handle_path = create_handle_file()
                    log.msg("Work handle file:", handle_path)
                else:
                    log.msg("Work has to be inserted and has no handle: new one will be generated during import.")
            else:
                pass
        except Exception as e:
            log.msg(e)
            raise e

        # <J.R.> 24. 1. 2018
        # try:
        #     if doc.handle is None:
        #         log.msg("PREPARE PACKAGE: This document was not processed before. It has no handle assigned.")
        #         log.msg("Handle file won't be generated.")
        #     else:
        #         log.msg("PREPARE PACKAGE: This document was processed before. It has a handle assigned.")
        #         log.msg("PREPARE PACKAGE: Document did:", doc.doc_id, "Handle:", doc.handle)
        #         handle_path = create_handle_file()
        #         log.msg("Work handle file:", handle_path)
        # except Exception as e:
        #     raise e

        return 'finished_package'
