#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=import-error
from alembic.migration import MigrationContext

from alembic.operations import Operations

from sqlalchemy import Column
from sqlalchemy import String

from sqlalchemy import inspect

from zope.component.hooks import setHooks

from nti.analytics.generations.utils import do_evolve
from nti.analytics.generations.utils import mysql_column_exists

from nti.analytics.database import get_analytics_db

generation = 2

logger = __import__('logging').getLogger(__name__)


def evolve_job():
    setHooks()
    db = get_analytics_db()

    if db.defaultSQLite or db.engine.name == 'sqlite':
        return

    # Cannot use transaction with alter table scripts and mysql
    connection = db.engine.connect()
    mc = MigrationContext.configure(connection)
    op = Operations(mc)
    inspector = inspect(db.engine)
    schema = inspector.default_schema_name

    new_column_name = 'employee_id'

    if not mysql_column_exists(connection, schema, 'UserRegistrations', new_column_name):
        op.add_column('UserRegistrations',
                      Column(new_column_name, String(32),
                             nullable=True, index=False))
        logger.info('Adding column (%s) (%s)', new_column_name, schema)
    logger.info('Finished analytics evolve (%s)', generation)


def evolve(context):
    """
    Add the employee_id column to registrations.
    """
    do_evolve(context, evolve_job, generation)
