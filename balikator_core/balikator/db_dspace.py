#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

from sqlalchemy import *
from sqlalchemy.dialects.postgresql import *
from sqlalchemy.orm import create_session
from sqlalchemy.ext.declarative import declarative_base

__all__ = ['reflect_dspace']


def reflect_dspace(engine):
    Base = declarative_base()
    metadata = MetaData(bind=engine)

    metadata.reflect(views=True)

    return metadata