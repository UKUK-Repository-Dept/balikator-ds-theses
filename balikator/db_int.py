#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base

__all__ = ['reflect_internal']


def reflect_internal(engine):
    Base = declarative_base()
    metadata = MetaData(bind=engine)

    metadata.reflect(views=True)

    return metadata
