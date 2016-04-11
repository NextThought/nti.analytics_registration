#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 34
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 3

from sqlalchemy import String

from sqlalchemy import inspect

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.generations.utils import do_evolve

from nti.analytics.database import get_analytics_db

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite or db.engine.name == 'sqlite':
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)
	inspector = inspect( db.engine )
	schema = inspector.default_schema_name

	column_name = 'curriculum'
	tables = ['RegistrationSessions', 'RegistrationEnrollmentRules', 'UserRegistrations']

	for table in tables:
		op.alter_column( table, column_name, type_=String(128), nullable=False, index=False )
	logger.info( 'Extending column (%s) (%s)', column_name, schema )

def evolve( context ):
	"""
    Make the curriculum column larger.
    """
	do_evolve( context, evolve_job, generation )
	logger.info( 'Finished analytics evolve (%s)', generation )
