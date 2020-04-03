FROM postgres:12.2-alpine

ENV LANG en_US.utf8
ADD ./db_schema.sql /docker-entrypoint-initdb.d
RUN chown postgres:postgres /docker-entrypoint-initdb.d/db_schema.sql