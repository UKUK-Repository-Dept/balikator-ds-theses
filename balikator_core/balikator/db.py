#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.orm import create_session
from sqlalchemy.ext.declarative import declarative_base

__all__ = ['reflect']


def reflect(engine):
    Base = declarative_base()
    metadata = MetaData(bind=engine, schema='STDOWNER')

    metadata.reflect(views=True)

    return metadata



