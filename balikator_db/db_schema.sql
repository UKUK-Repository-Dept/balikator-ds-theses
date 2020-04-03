--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;

--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET search_path = public, pg_catalog;

--
-- Name: assigned_process; Type: TYPE; Schema: public; Owner: balikator
--

CREATE TYPE assigned_process AS ENUM (
    'new',
    'files_information',
    'contents_file',
    'package',
    'import',
    'metadata_files',
    'work_files',
    'ingest',
    'handle',
    'ingest_check',
    'document_finish'
);


ALTER TYPE public.assigned_process OWNER TO balikator;

--
-- Name: TYPE assigned_process; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TYPE assigned_process IS 'Enumeration of all processes that can be assigned to a document. Depending on the value, document will be processed by a different part of workflow.';


--
-- Name: batch_process; Type: TYPE; Schema: public; Owner: balikator
--

CREATE TYPE batch_process AS ENUM (
    'new',
    'record_parsing',
    'doc_creation',
    'doc_setup',
    'doc_processing',
    'doc_database',
    'doc_import',
    'create_mapfile',
    'move_mapfile',
    'doc_ingest',
    'batch_finish',
    'cleanup'
);


ALTER TYPE public.batch_process OWNER TO balikator;

--
-- Name: TYPE batch_process; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TYPE batch_process IS 'Assigned batch process';


--
-- Name: document_direction_process; Type: TYPE; Schema: public; Owner: balikator
--

CREATE TYPE document_direction_process AS ENUM (
    'import',
    'insert',
    'update',
    'delete'
);


ALTER TYPE public.document_direction_process OWNER TO balikator;

--
-- Name: TYPE document_direction_process; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TYPE document_direction_process IS 'List of process names that are corresponding with direction of the document processin. Possible values are: ''import'', ''update'', ''delete.';


--
-- Name: document_kind; Type: TYPE; Schema: public; Owner: balikator
--

CREATE TYPE document_kind AS ENUM (
    'theses',
    'obd'
);


ALTER TYPE public.document_kind OWNER TO balikator;

--
-- Name: process_status; Type: TYPE; Schema: public; Owner: balikator
--

CREATE TYPE process_status AS ENUM (
    'planned',
    'started',
    'finished',
    'failed',
    'error',
    'finished with errors',
    'skipped',
    'preprocessed',
    'finished_package',
    'finished_import',
    'finished_processing',
    'finished_ingest',
    'cleanup',
    'evaluation'
);


ALTER TYPE public.process_status OWNER TO balikator;

--
-- Name: TYPE process_status; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TYPE process_status IS 'Processing status of the document indicating whether the document processing has been - planned, started, finished or finished with error.';


--
-- Name: workflow_status; Type: TYPE; Schema: public; Owner: balikator
--

CREATE TYPE workflow_status AS ENUM (
    'running',
    'stopped',
    'failed'
);


ALTER TYPE public.workflow_status OWNER TO balikator;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: batch; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE batch (
    uuid uuid DEFAULT uuid_generate_v4() NOT NULL,
    finished timestamp without time zone,
    created timestamp without time zone DEFAULT now() NOT NULL,
    state process_status NOT NULL,
    name character varying(64) NOT NULL,
    batch_process batch_process DEFAULT 'new'::batch_process NOT NULL
);


ALTER TABLE public.batch OWNER TO balikator;

--
-- Name: TABLE batch; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE batch IS 'Table containing information about processed batches of documents. Each batch can have 1 or more document in it. Batch identified by batch uuid, assigned at the time of batch creation. Batch has a creation date and process status, indicating whether there was some faulty document in it (error status), or all documents were processed without error (finished).';


--
-- Name: COLUMN batch.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch.state IS 'State of the batch processing. Should be one of the values in process_status enum type and should not be NULL.';


--
-- Name: COLUMN batch.name; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch.name IS 'Name of the batch file';


--
-- Name: COLUMN batch.batch_process; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch.batch_process IS 'Assigned batch process';


--
-- Name: batch_audit; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE batch_audit (
    id bigint NOT NULL,
    uuid uuid NOT NULL,
    state process_status NOT NULL,
    name character varying(64) NOT NULL,
    batch_process batch_process NOT NULL,
    created timestamp without time zone NOT NULL,
    finished timestamp without time zone NOT NULL
);


ALTER TABLE public.batch_audit OWNER TO balikator;

--
-- Name: TABLE batch_audit; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE batch_audit IS 'Audit table stores information about all processed batches, finished, failed, or finished with errors.';


--
-- Name: COLUMN batch_audit.id; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch_audit.id IS 'Primary key';


--
-- Name: COLUMN batch_audit.uuid; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch_audit.uuid IS 'UUID of the batch';


--
-- Name: COLUMN batch_audit.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch_audit.state IS 'State of the processed batch.';


--
-- Name: COLUMN batch_audit.name; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch_audit.name IS 'Name of the batch file.';


--
-- Name: COLUMN batch_audit.batch_process; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch_audit.batch_process IS 'Last process assigned to batch before finishing.';


--
-- Name: COLUMN batch_audit.created; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch_audit.created IS 'Date and time when batch was created.';


--
-- Name: COLUMN batch_audit.finished; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN batch_audit.finished IS 'Date and time when batch was processed.';


--
-- Name: batch_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: balikator
--

CREATE SEQUENCE batch_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.batch_audit_id_seq OWNER TO balikator;

--
-- Name: batch_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: balikator
--

ALTER SEQUENCE batch_audit_id_seq OWNED BY batch_audit.id;


--
-- Name: batch_daily_stats; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW batch_daily_stats AS
    SELECT (date_part('year'::text, batch.finished))::integer AS year, (date_part('month'::text, batch.finished))::integer AS month, (date_part('day'::text, batch.finished))::integer AS day, (sum(CASE WHEN (batch.state = 'finished'::process_status) THEN 1 ELSE 0 END))::integer AS finished, (sum(CASE WHEN (batch.state = 'finished with errors'::process_status) THEN 1 ELSE 0 END))::integer AS finished_errors, (sum(CASE WHEN (batch.state = 'failed'::process_status) THEN 1 ELSE 0 END))::integer AS failed FROM batch GROUP BY (date_part('year'::text, batch.finished))::integer, (date_part('month'::text, batch.finished))::integer, (date_part('day'::text, batch.finished))::integer ORDER BY (date_part('year'::text, batch.finished))::integer DESC, (date_part('month'::text, batch.finished))::integer DESC, (date_part('day'::text, batch.finished))::integer DESC;


ALTER TABLE public.batch_daily_stats OWNER TO balikator;

--
-- Name: batch_info_doc_count; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE batch_info_doc_count (
    uuid uuid,
    name character varying(64),
    batch_process batch_process,
    created timestamp without time zone,
    finished timestamp without time zone,
    state process_status,
    state_planned bigint,
    state_started bigint,
    state_finished bigint,
    state_failed bigint
);


ALTER TABLE public.batch_info_doc_count OWNER TO balikator;

--
-- Name: TABLE batch_info_doc_count; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE batch_info_doc_count IS 'Views information about batch from batch table with information about documents from each batch, grouped by their state: new, running, failed, finished.';


--
-- Name: dated_batches; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW dated_batches AS
    SELECT batch.uuid, batch.finished, batch.created, batch.name, batch.state, batch.batch_process, (date_part('year'::text, batch.finished))::integer AS year, (date_part('month'::text, batch.finished))::integer AS month, (date_part('day'::text, batch.finished))::integer AS day FROM batch ORDER BY batch.finished DESC;


ALTER TABLE public.dated_batches OWNER TO balikator;

--
-- Name: document; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE document (
    did integer NOT NULL,
    created timestamp without time zone DEFAULT now() NOT NULL,
    kind document_kind NOT NULL,
    state process_status NOT NULL,
    handle character varying,
    batch_uuid uuid NOT NULL,
    current_process assigned_process DEFAULT 'new'::assigned_process NOT NULL,
    direction_process document_direction_process NOT NULL,
    "repId" integer NOT NULL,
    finished timestamp without time zone,
    workflow_process document_direction_process,
    aleph_id character varying(12),
    work_type character varying(64)
);


ALTER TABLE public.document OWNER TO balikator;

--
-- Name: TABLE document; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE document IS 'Master object for all document states';


--
-- Name: COLUMN document.did; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.did IS 'ID of the document in SIS. Primary key. DID of the work in balikator DB should be same as DID of the work in SIS DB.';


--
-- Name: COLUMN document.created; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.created IS 'Immutable timestamp of the moment we have first noticed the work in SIS DB. For sorting.';


--
-- Name: COLUMN document.kind; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.kind IS 'Kind of the document being processed. Should by one of the document_kind type.';


--
-- Name: COLUMN document.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.state IS 'State of the processing of the document. Should be one of the process_status type and not NULL.';


--
-- Name: COLUMN document.handle; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.handle IS 'Document handle in the DSpace repository';


--
-- Name: COLUMN document.batch_uuid; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.batch_uuid IS 'Immutable UUID of the batch the document is assigned to. Document should always be part of a batch, so value of batch_uuid should never be NULL.';


--
-- Name: COLUMN document.current_process; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.current_process IS 'Name of the process currently assigned to a document. Depending on the value, document will be process by a different part of the workflow.';


--
-- Name: COLUMN document.direction_process; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.direction_process IS 'Values of this column determines how the document will be processed withing document workflow, if it''s goint to be imported, updated or deleted from the repository.';


--
-- Name: COLUMN document."repId"; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document."repId" IS 'SIS repository ID.';


--
-- Name: COLUMN document.workflow_process; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.workflow_process IS 'Actual process with which a document enters packager workflow. This could be different from the direction_process stored in the MARC record of a document within a batch file.';


--
-- Name: COLUMN document.work_type; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document.work_type IS 'Work type, could be something like "Bakalářská práce", "Diplomová práce", "Disertační práce", "Habilitační práce" or NULL.';


--
-- Name: dated_documents; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW dated_documents AS
    SELECT document.did, document.batch_uuid, document.aleph_id, document.kind, document.handle, document.direction_process, document.workflow_process, document.created, document.finished, document.current_process, document.state, (date_part('year'::text, document.finished))::integer AS year, (date_part('month'::text, document.finished))::integer AS month, (date_part('day'::text, document.finished))::integer AS day FROM document ORDER BY document.finished DESC;


ALTER TABLE public.dated_documents OWNER TO balikator;

--
-- Name: document_audit; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE document_audit (
    did integer NOT NULL,
    "repId" integer NOT NULL,
    batch_uuid uuid NOT NULL,
    handle character varying(64),
    direction_process document_direction_process NOT NULL,
    kind document_kind NOT NULL,
    created timestamp without time zone NOT NULL,
    finished timestamp without time zone NOT NULL,
    state process_status NOT NULL,
    id bigint NOT NULL,
    workflow_process document_direction_process,
    aleph_id character varying(12),
    work_type character varying(64)
);


ALTER TABLE public.document_audit OWNER TO balikator;

--
-- Name: TABLE document_audit; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE document_audit IS 'This table holds information about all processed documents, regardles their final state (finished or failed). Serves for auditing and statistics as well as cross-reference when there is a document in a batch that has been already processed in the past.';


--
-- Name: COLUMN document_audit.work_type; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN document_audit.work_type IS 'Type of work, could be something like "Bakalářská práce", "Diplomová práce", "Disertační práce", "Habilitační práce" or None (NULL)';


--
-- Name: document_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: balikator
--

CREATE SEQUENCE document_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.document_audit_id_seq OWNER TO balikator;

--
-- Name: document_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: balikator
--

ALTER SEQUENCE document_audit_id_seq OWNED BY document_audit.id;


--
-- Name: document_batch_direction_stats; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW document_batch_direction_stats AS
    SELECT document_audit.batch_uuid, (sum(CASE WHEN (document_audit.direction_process = 'insert'::document_direction_process) THEN 1 ELSE 0 END))::integer AS insert, (sum(CASE WHEN (document_audit.direction_process = 'update'::document_direction_process) THEN 1 ELSE 0 END))::integer AS update, (sum(CASE WHEN (document_audit.direction_process = 'delete'::document_direction_process) THEN 1 ELSE 0 END))::integer AS delete FROM document_audit GROUP BY (date_part('year'::text, document_audit.finished))::integer, (date_part('month'::text, document_audit.finished))::integer, (date_part('day'::text, document_audit.finished))::integer, document_audit.batch_uuid ORDER BY (date_part('year'::text, document_audit.finished))::integer DESC, (date_part('month'::text, document_audit.finished))::integer DESC, (date_part('day'::text, document_audit.finished))::integer DESC;


ALTER TABLE public.document_batch_direction_stats OWNER TO balikator;

--
-- Name: document_batch_state_stats; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW document_batch_state_stats AS
    SELECT document_audit.batch_uuid, (sum(CASE WHEN (document_audit.state = 'finished'::process_status) THEN 1 ELSE 0 END))::integer AS finished, (sum(CASE WHEN (document_audit.state = 'failed'::process_status) THEN 1 ELSE 0 END))::integer AS failed, (sum(CASE WHEN (document_audit.state = 'skipped'::process_status) THEN 1 ELSE 0 END))::integer AS skipped FROM document_audit GROUP BY (date_part('year'::text, document_audit.finished))::integer, (date_part('month'::text, document_audit.finished))::integer, (date_part('day'::text, document_audit.finished))::integer, document_audit.batch_uuid ORDER BY (date_part('year'::text, document_audit.finished))::integer DESC, (date_part('month'::text, document_audit.finished))::integer DESC, (date_part('day'::text, document_audit.finished))::integer DESC;


ALTER TABLE public.document_batch_state_stats OWNER TO balikator;

--
-- Name: document_batch_wf_direction_stats; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW document_batch_wf_direction_stats AS
    SELECT document_audit.batch_uuid, (sum(CASE WHEN (document_audit.workflow_process = 'insert'::document_direction_process) THEN 1 ELSE 0 END))::integer AS insert, (sum(CASE WHEN (document_audit.workflow_process = 'update'::document_direction_process) THEN 1 ELSE 0 END))::integer AS update, (sum(CASE WHEN (document_audit.workflow_process = 'delete'::document_direction_process) THEN 1 ELSE 0 END))::integer AS delete, (sum(CASE WHEN (document_audit.workflow_process IS NULL) THEN 1 ELSE 0 END))::integer AS skipped FROM document_audit GROUP BY (date_part('year'::text, document_audit.finished))::integer, (date_part('month'::text, document_audit.finished))::integer, (date_part('day'::text, document_audit.finished))::integer, document_audit.batch_uuid ORDER BY (date_part('year'::text, document_audit.finished))::integer DESC, (date_part('month'::text, document_audit.finished))::integer DESC, (date_part('day'::text, document_audit.finished))::integer DESC;


ALTER TABLE public.document_batch_wf_direction_stats OWNER TO balikator;

--
-- Name: document_daily_direction_stats; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW document_daily_direction_stats AS
    SELECT (date_part('year'::text, document.finished))::integer AS year, (date_part('month'::text, document.finished))::integer AS month, (date_part('day'::text, document.finished))::integer AS day, (sum(CASE WHEN (document.direction_process = 'insert'::document_direction_process) THEN 1 ELSE 0 END))::integer AS insert, (sum(CASE WHEN (document.direction_process = 'update'::document_direction_process) THEN 1 ELSE 0 END))::integer AS update, (sum(CASE WHEN (document.direction_process = 'delete'::document_direction_process) THEN 1 ELSE 0 END))::integer AS delete FROM document GROUP BY (date_part('year'::text, document.finished))::integer, (date_part('month'::text, document.finished))::integer, (date_part('day'::text, document.finished))::integer ORDER BY (date_part('year'::text, document.finished))::integer DESC, (date_part('month'::text, document.finished))::integer DESC, (date_part('day'::text, document.finished))::integer DESC;


ALTER TABLE public.document_daily_direction_stats OWNER TO balikator;

--
-- Name: document_daily_stats; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW document_daily_stats AS
    SELECT (date_part('year'::text, document.finished))::integer AS year, (date_part('month'::text, document.finished))::integer AS month, (date_part('day'::text, document.finished))::integer AS day, (sum(CASE WHEN (document.state = 'finished'::process_status) THEN 1 ELSE 0 END))::integer AS finished, (sum(CASE WHEN (document.state = 'failed'::process_status) THEN 1 ELSE 0 END))::integer AS failed, (sum(CASE WHEN (document.state = 'skipped'::process_status) THEN 1 ELSE 0 END))::integer AS skipped FROM document GROUP BY (date_part('year'::text, document.finished))::integer, (date_part('month'::text, document.finished))::integer, (date_part('day'::text, document.finished))::integer ORDER BY (date_part('year'::text, document.finished))::integer DESC, (date_part('month'::text, document.finished))::integer DESC, (date_part('day'::text, document.finished))::integer DESC;


ALTER TABLE public.document_daily_stats OWNER TO balikator;

--
-- Name: document_daily_wf_direction_stats; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW document_daily_wf_direction_stats AS
    SELECT (date_part('year'::text, document.finished))::integer AS year, (date_part('month'::text, document.finished))::integer AS month, (date_part('day'::text, document.finished))::integer AS day, (sum(CASE WHEN (document.workflow_process = 'insert'::document_direction_process) THEN 1 ELSE 0 END))::integer AS insert, (sum(CASE WHEN (document.workflow_process = 'update'::document_direction_process) THEN 1 ELSE 0 END))::integer AS update, (sum(CASE WHEN (document.workflow_process = 'delete'::document_direction_process) THEN 1 ELSE 0 END))::integer AS delete, (sum(CASE WHEN (document.workflow_process IS NULL) THEN 1 ELSE 0 END))::integer AS skipped FROM document GROUP BY (date_part('year'::text, document.finished))::integer, (date_part('month'::text, document.finished))::integer, (date_part('day'::text, document.finished))::integer ORDER BY (date_part('year'::text, document.finished))::integer DESC, (date_part('month'::text, document.finished))::integer DESC, (date_part('day'::text, document.finished))::integer DESC;


ALTER TABLE public.document_daily_wf_direction_stats OWNER TO balikator;

--
-- Name: document_handles; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE document_handles (
    did integer NOT NULL,
    handle character varying(64)
);


ALTER TABLE public.document_handles OWNER TO balikator;

--
-- Name: TABLE document_handles; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE document_handles IS 'Table mapping document did to a DSpace handle. All document in this table should have a handle assigned. If the document did is not here, it means that the handle was not yet assigned to it. Document did is a primary key, so it should not repeat and it cannot be updated.';


--
-- Name: errors_batch; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE errors_batch (
    batch_uuid uuid NOT NULL,
    error_message character varying(256) NOT NULL,
    id bigint NOT NULL
);


ALTER TABLE public.errors_batch OWNER TO balikator;

--
-- Name: TABLE errors_batch; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE errors_batch IS 'Table of batch errors. Eeach error consists of batch uuid and error message. UUID is not a primary key, instead auto-increment number is used a a primary key. Table servers as helper for storing detailed information about each error that happend in a processed batch.';


--
-- Name: COLUMN errors_batch.batch_uuid; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_batch.batch_uuid IS 'Batch uuid - connects error to a batch.';


--
-- Name: COLUMN errors_batch.error_message; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_batch.error_message IS 'Message describing batch error.';


--
-- Name: COLUMN errors_batch.id; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_batch.id IS 'ID - primary key';


--
-- Name: errors_batch_id_seq; Type: SEQUENCE; Schema: public; Owner: balikator
--

CREATE SEQUENCE errors_batch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.errors_batch_id_seq OWNER TO balikator;

--
-- Name: errors_batch_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: balikator
--

ALTER SEQUENCE errors_batch_id_seq OWNED BY errors_batch.id;


--
-- Name: errors_document; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE errors_document (
    doc_id integer NOT NULL,
    batch_uuid uuid NOT NULL,
    error_message character varying(256) NOT NULL,
    id bigint NOT NULL
);


ALTER TABLE public.errors_document OWNER TO balikator;

--
-- Name: COLUMN errors_document.doc_id; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_document.doc_id IS 'Document ID from document table.';


--
-- Name: COLUMN errors_document.batch_uuid; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_document.batch_uuid IS 'Batch uuid.';


--
-- Name: COLUMN errors_document.error_message; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_document.error_message IS 'Error message';


--
-- Name: COLUMN errors_document.id; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_document.id IS 'Primary key';


--
-- Name: errors_document_id_seq; Type: SEQUENCE; Schema: public; Owner: balikator
--

CREATE SEQUENCE errors_document_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.errors_document_id_seq OWNER TO balikator;

--
-- Name: errors_document_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: balikator
--

ALTER SEQUENCE errors_document_id_seq OWNED BY errors_document.id;


--
-- Name: errors_workflow; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE errors_workflow (
    id bigint NOT NULL,
    workflow_id integer NOT NULL,
    name character varying(32) NOT NULL,
    error_message character varying(256) NOT NULL
);


ALTER TABLE public.errors_workflow OWNER TO balikator;

--
-- Name: TABLE errors_workflow; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE errors_workflow IS 'Errors in the workflow, that caused it to fail';


--
-- Name: COLUMN errors_workflow.id; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_workflow.id IS 'Primary key';


--
-- Name: COLUMN errors_workflow.workflow_id; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_workflow.workflow_id IS 'ID of the workflow';


--
-- Name: COLUMN errors_workflow.name; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_workflow.name IS 'Name of the workflow';


--
-- Name: COLUMN errors_workflow.error_message; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN errors_workflow.error_message IS 'Error message';


--
-- Name: errors_workflow_id_seq; Type: SEQUENCE; Schema: public; Owner: balikator
--

CREATE SEQUENCE errors_workflow_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.errors_workflow_id_seq OWNER TO balikator;

--
-- Name: errors_workflow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: balikator
--

ALTER SEQUENCE errors_workflow_id_seq OWNED BY errors_workflow.id;


--
-- Name: monthly_batch_counts; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW monthly_batch_counts AS
    SELECT (date_part('year'::text, batch.finished))::integer AS year, (date_part('month'::text, batch.finished))::integer AS month, count(batch.uuid) AS count FROM batch GROUP BY date_part('year'::text, batch.finished), date_part('month'::text, batch.finished) ORDER BY date_part('year'::text, batch.finished) DESC, date_part('month'::text, batch.finished) DESC;


ALTER TABLE public.monthly_batch_counts OWNER TO balikator;

--
-- Name: monthly_document_counts; Type: VIEW; Schema: public; Owner: balikator
--

CREATE VIEW monthly_document_counts AS
    SELECT (date_part('year'::text, document.finished))::integer AS year, (date_part('month'::text, document.finished))::integer AS month, count(document.did) AS count FROM document GROUP BY date_part('year'::text, document.finished), date_part('month'::text, document.finished) ORDER BY date_part('year'::text, document.finished) DESC, date_part('month'::text, document.finished) DESC;


ALTER TABLE public.monthly_document_counts OWNER TO balikator;

--
-- Name: process_contents_file; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE process_contents_file (
    did integer,
    state process_status NOT NULL,
    created timestamp without time zone,
    finished timestamp without time zone
);


ALTER TABLE public.process_contents_file OWNER TO balikator;

--
-- Name: TABLE process_contents_file; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE process_contents_file IS 'Contains documents assigned with process of creating contents file (DSpace file responsible for bitstream description).';


--
-- Name: COLUMN process_contents_file.did; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_contents_file.did IS 'Document id from SIS database. Unique identifier of the document.';


--
-- Name: COLUMN process_contents_file.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_contents_file.state IS 'State of this process for each document.';


--
-- Name: COLUMN process_contents_file.created; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_contents_file.created IS 'Timestamp indicating when this process started on a document.';


--
-- Name: COLUMN process_contents_file.finished; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_contents_file.finished IS 'Timestamp indicating when this process ended on a document.';


--
-- Name: process_dc_metadata; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE process_dc_metadata (
    did integer NOT NULL,
    created timestamp without time zone,
    state process_status NOT NULL,
    finished timestamp without time zone
);


ALTER TABLE public.process_dc_metadata OWNER TO balikator;

--
-- Name: COLUMN process_dc_metadata.did; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_dc_metadata.did IS 'DID - document id from the SIS database. Unique identifier of the document';


--
-- Name: COLUMN process_dc_metadata.created; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_dc_metadata.created IS 'Timestamp indication when document entered this process.';


--
-- Name: COLUMN process_dc_metadata.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_dc_metadata.state IS 'State of this process for each document.';


--
-- Name: COLUMN process_dc_metadata.finished; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_dc_metadata.finished IS 'Timestamp indicationg when this process finished for a document.';


--
-- Name: process_import; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE process_import (
    did integer NOT NULL,
    state process_status NOT NULL,
    created timestamp without time zone,
    finished timestamp without time zone
);


ALTER TABLE public.process_import OWNER TO balikator;

--
-- Name: TABLE process_import; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE process_import IS 'Process of importing the package to a DSpace import directory.';


--
-- Name: COLUMN process_import.did; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_import.did IS 'Document identifier from SIS database. Unique identifier.';


--
-- Name: COLUMN process_import.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_import.state IS 'State of this process for each document.';


--
-- Name: COLUMN process_import.created; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_import.created IS 'Timestamp indicating when this process started on a document.';


--
-- Name: COLUMN process_import.finished; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_import.finished IS 'Timestamp indicating when this process ended on a document.';


--
-- Name: process_ingest; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE process_ingest (
    did integer NOT NULL,
    state process_status NOT NULL,
    created timestamp without time zone,
    finished timestamp without time zone
);


ALTER TABLE public.process_ingest OWNER TO balikator;

--
-- Name: TABLE process_ingest; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE process_ingest IS 'Process of ingesting a document into the DSpace repository.';


--
-- Name: COLUMN process_ingest.did; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_ingest.did IS 'Document identifier from SIS database. Unique identifier of the document.';


--
-- Name: COLUMN process_ingest.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_ingest.state IS 'State of this process for a document.';


--
-- Name: COLUMN process_ingest.created; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_ingest.created IS 'Timestamp indicating when this process started for a document.';


--
-- Name: COLUMN process_ingest.finished; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_ingest.finished IS 'Timestamp indication when this process ended for a document.';


--
-- Name: process_ingest_check; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE process_ingest_check (
    did integer NOT NULL,
    state process_status NOT NULL,
    created timestamp without time zone,
    finished timestamp without time zone
);


ALTER TABLE public.process_ingest_check OWNER TO balikator;

--
-- Name: TABLE process_ingest_check; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE process_ingest_check IS 'Process of checking whether the document was ingested to DSpace or not.';


--
-- Name: COLUMN process_ingest_check.did; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_ingest_check.did IS 'Document identifier from SIS database. Unique identifier of the document.';


--
-- Name: COLUMN process_ingest_check.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_ingest_check.state IS 'State of this process for a document.';


--
-- Name: COLUMN process_ingest_check.created; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_ingest_check.created IS 'Timestamp indicating when this process started for a document.';


--
-- Name: COLUMN process_ingest_check.finished; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_ingest_check.finished IS 'Timestamp indicating when the process ended for the document.';


--
-- Name: process_package; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE process_package (
    did integer NOT NULL,
    state process_status NOT NULL,
    created timestamp without time zone,
    finished timestamp without time zone
);


ALTER TABLE public.process_package OWNER TO balikator;

--
-- Name: TABLE process_package; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE process_package IS 'Process of creating a ingest package for a DSpace repository.';


--
-- Name: COLUMN process_package.did; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_package.did IS 'Document identifier from SIS database. Unique identifier of a document.';


--
-- Name: COLUMN process_package.state; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_package.state IS 'State of this process on a document.';


--
-- Name: COLUMN process_package.created; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_package.created IS 'Timestamp indicating when this process started on the document.';


--
-- Name: COLUMN process_package.finished; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN process_package.finished IS 'Timestamp indicating when this process ended on the document.';


--
-- Name: workflow; Type: TABLE; Schema: public; Owner: balikator; Tablespace: 
--

CREATE TABLE workflow (
    id integer NOT NULL,
    name character varying(32) NOT NULL,
    started timestamp without time zone,
    stopped timestamp without time zone,
    state workflow_status
);


ALTER TABLE public.workflow OWNER TO balikator;

--
-- Name: TABLE workflow; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON TABLE workflow IS 'Workflow information';


--
-- Name: COLUMN workflow.id; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN workflow.id IS 'ID of the workflow';


--
-- Name: COLUMN workflow.name; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN workflow.name IS 'Name of the workflow';


--
-- Name: COLUMN workflow.started; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN workflow.started IS 'Date and time when workflow was started for the last time.';


--
-- Name: COLUMN workflow.stopped; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON COLUMN workflow.stopped IS 'Time and date when the workflow was stopped for the last time.';


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY batch_audit ALTER COLUMN id SET DEFAULT nextval('batch_audit_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY document_audit ALTER COLUMN id SET DEFAULT nextval('document_audit_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY errors_batch ALTER COLUMN id SET DEFAULT nextval('errors_batch_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY errors_document ALTER COLUMN id SET DEFAULT nextval('errors_document_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY errors_workflow ALTER COLUMN id SET DEFAULT nextval('errors_workflow_id_seq'::regclass);


--
-- Name: batch_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY batch_audit
    ADD CONSTRAINT batch_audit_pkey PRIMARY KEY (id);


--
-- Name: document_audit_id_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY document_audit
    ADD CONSTRAINT document_audit_id_pkey PRIMARY KEY (id);


--
-- Name: CONSTRAINT document_audit_id_pkey ON document_audit; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON CONSTRAINT document_audit_id_pkey ON document_audit IS 'Primary key of the document_audit table.';


--
-- Name: document_did_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY document_handles
    ADD CONSTRAINT document_did_pkey PRIMARY KEY (did);


--
-- Name: document_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY document
    ADD CONSTRAINT document_pkey PRIMARY KEY (did);


--
-- Name: CONSTRAINT document_pkey ON document; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON CONSTRAINT document_pkey ON document IS 'Primary key of document table.';


--
-- Name: errors_batch_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY errors_batch
    ADD CONSTRAINT errors_batch_pkey PRIMARY KEY (id);


--
-- Name: CONSTRAINT errors_batch_pkey ON errors_batch; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON CONSTRAINT errors_batch_pkey ON errors_batch IS 'errors_batch primary key';


--
-- Name: errors_document_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY errors_document
    ADD CONSTRAINT errors_document_pkey PRIMARY KEY (id);


--
-- Name: errors_workflow_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY errors_workflow
    ADD CONSTRAINT errors_workflow_pkey PRIMARY KEY (id);


--
-- Name: uuid_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY batch
    ADD CONSTRAINT uuid_pkey PRIMARY KEY (uuid);


--
-- Name: workflow_id_pkey; Type: CONSTRAINT; Schema: public; Owner: balikator; Tablespace: 
--

ALTER TABLE ONLY workflow
    ADD CONSTRAINT workflow_id_pkey PRIMARY KEY (id);


--
-- Name: fki_document_uuid_batch_uuid_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_document_uuid_batch_uuid_fkey ON document USING btree (batch_uuid);


--
-- Name: fki_errors_document_batch_uuid_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_errors_document_batch_uuid_fkey ON errors_document USING btree (batch_uuid);


--
-- Name: fki_process_contents_file_document_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_process_contents_file_document_fkey ON process_contents_file USING btree (did);


--
-- Name: fki_process_dc_metadata_document_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_process_dc_metadata_document_fkey ON process_dc_metadata USING btree (did);


--
-- Name: fki_process_import_document_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_process_import_document_fkey ON process_import USING btree (did);


--
-- Name: fki_process_ingest_check_document_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_process_ingest_check_document_fkey ON process_ingest_check USING btree (did);


--
-- Name: fki_process_ingest_document_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_process_ingest_document_fkey ON process_ingest USING btree (did);


--
-- Name: fki_process_package_document_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_process_package_document_fkey ON process_package USING btree (did);


--
-- Name: fki_workflow_id_errors_w_id_fkey; Type: INDEX; Schema: public; Owner: balikator; Tablespace: 
--

CREATE INDEX fki_workflow_id_errors_w_id_fkey ON errors_workflow USING btree (workflow_id);


--
-- Name: _RETURN; Type: RULE; Schema: public; Owner: balikator
--

CREATE RULE "_RETURN" AS ON SELECT TO batch_info_doc_count DO INSTEAD SELECT batch.uuid, batch.name, batch.batch_process, batch.created, batch.finished, batch.state, sum(CASE WHEN ((document.batch_uuid = batch.uuid) AND (document.state = 'planned'::process_status)) THEN 1 ELSE 0 END) AS state_planned, sum(CASE WHEN ((document.batch_uuid = batch.uuid) AND (document.state = 'started'::process_status)) THEN 1 ELSE 0 END) AS state_started, sum(CASE WHEN ((document.batch_uuid = batch.uuid) AND (document.state = 'finished'::process_status)) THEN 1 ELSE 0 END) AS state_finished, sum(CASE WHEN ((document.batch_uuid = batch.uuid) AND (document.state = 'failed'::process_status)) THEN 1 ELSE 0 END) AS state_failed FROM batch, document GROUP BY batch.uuid, document.did, document.batch_uuid;


--
-- Name: document_batch_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY document
    ADD CONSTRAINT document_batch_uuid_fkey FOREIGN KEY (batch_uuid) REFERENCES batch(uuid) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: document_handles_did_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY document_handles
    ADD CONSTRAINT document_handles_did_fkey FOREIGN KEY (did) REFERENCES document(did);


--
-- Name: errors_document_batch_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY errors_document
    ADD CONSTRAINT errors_document_batch_uuid_fkey FOREIGN KEY (batch_uuid) REFERENCES batch(uuid);


--
-- Name: CONSTRAINT errors_document_batch_uuid_fkey ON errors_document; Type: COMMENT; Schema: public; Owner: balikator
--

COMMENT ON CONSTRAINT errors_document_batch_uuid_fkey ON errors_document IS 'Foreign key - batch uuid from batch table.';


--
-- Name: process_contents_file_document_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY process_contents_file
    ADD CONSTRAINT process_contents_file_document_fkey FOREIGN KEY (did) REFERENCES document(did) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: process_dc_metadata_document_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY process_dc_metadata
    ADD CONSTRAINT process_dc_metadata_document_fkey FOREIGN KEY (did) REFERENCES document(did) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: process_import_document_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY process_import
    ADD CONSTRAINT process_import_document_fkey FOREIGN KEY (did) REFERENCES document(did) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: process_ingest_check_document_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY process_ingest_check
    ADD CONSTRAINT process_ingest_check_document_fkey FOREIGN KEY (did) REFERENCES document(did) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: process_ingest_document_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY process_ingest
    ADD CONSTRAINT process_ingest_document_fkey FOREIGN KEY (did) REFERENCES document(did) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: process_package_document_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY process_package
    ADD CONSTRAINT process_package_document_fkey FOREIGN KEY (did) REFERENCES document(did) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: workflow_id_errors_w_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: balikator
--

ALTER TABLE ONLY errors_workflow
    ADD CONSTRAINT workflow_id_errors_w_id_fkey FOREIGN KEY (workflow_id) REFERENCES workflow(id);


-- --
-- -- Name: public; Type: ACL; Schema: -; Owner: postgres
-- --

-- REVOKE ALL ON SCHEMA public FROM PUBLIC;
-- REVOKE ALL ON SCHEMA public FROM postgres;
-- GRANT ALL ON SCHEMA public TO postgres;
-- GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

