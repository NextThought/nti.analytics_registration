#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import json

from sqlalchemy import Text
from sqlalchemy import Float
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Boolean
from sqlalchemy import ForeignKey

from sqlalchemy.schema import Sequence
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from zope import component

from nti.common.property import alias

from nti.analytics_database.interfaces import IAnalyticsIntidIdentifier

from nti.analytics_database.meta_mixins import CourseMixin
from nti.analytics_database.meta_mixins import DeletedMixin
from nti.analytics_database.meta_mixins import BaseViewMixin
from nti.analytics_database.meta_mixins import BaseTableMixin
from nti.analytics_database.meta_mixins import TimeLengthMixin
from nti.analytics_database.meta_mixins import ResourceMixin
from nti.analytics_database.meta_mixins import FileMimeTypeMixin

from nti.analytics_database import Base
from nti.analytics_database import NTIID_COLUMN_TYPE
from nti.analytics_database import INTID_COLUMN_TYPE

from nti.analytics.database import get_analytics_db
from nti.analytics.database import resolve_objects
from nti.analytics.database.query_utils import get_filtered_records

# FIXME: JZ - Table creation disabled for now
Base = object()

class UserRegistration(Base, BaseTableMixin):
	"""
	Hold user registration information.
	XXX: i2 specific? place in site?
	"""
	__tablename__ = 'UserRegistration'

	# XXX: Unique by user and session_date?
	registration_id = Column('registration_id', Integer,
							Sequence('registration_id_seq'),
							index=True, nullable=False, primary_key=True)

	school = Column( 'school', String(128), nullable=True, index=False )
	grade_teaching = Column( 'grade_teaching', String(32), nullable=True, index=False )
	curriculum = Column( 'curriculum', String(64), nullable=True, index=False )
	session_date = Column( 'session_date', String(32), nullable=True, index=False )

class RegistrationSurveys(Base):
	"""
	Hold basic survey information.
	"""
	__tablename__ = 'RegistrationSurveys'

	#: This will not be an actual object (or NTIID), but
	#: may just be a URL of the survey form.
	registration_survey_ds_id = Column('registration_survey_ds_id', NTIID_COLUMN_TYPE,
										nullable=False, index=True, autoincrement=False)

	registration_survey_id = Column('registration_survey_id', Integer,
									Sequence('registration_survey_id_seq'),
									index=True, nullable=False, primary_key=True)

	submissions = relationship( 'RegistrationSurveysTaken', lazy="select" )

class RegistrationSurveysTaken(Base, BaseTableMixin):
	"""
	Contains information when users submit RegistrationSurvey responses.
	"""
	__tablename__ = 'RegistrationSurveysTaken'

	registration_survey_taken_id = Column('registration_survey_taken_id', Integer,
										Sequence('registration_survey_taken_id_seq'),
										index=True, nullable=False, primary_key=True)

	registration_survey_id = Column('registration_survey_id',
					  				Integer,
					 				ForeignKey("RegistrationSurveys.registration_survey_id"),
					  				nullable=False,
					  				index=True)

	details = relationship( 'RegistrationSurveyDetails', lazy="select" )

class RegistrationSurveyDetails(Base):
	"""
	Stores survey submission details in a simple key/value store.
	"""
	__tablename__ = 'RegistrationSurveyDetails'

	registration_survey_taken_id = Column('registration_survey_taken_id',
					 					Integer,
					  					ForeignKey("RegistrationSurveysTaken.registration_survey_taken_id"),
					  					nullable=False,
					  					index=True)

	#: Ex. 'survey_question1'
	question_id = Column( 'question_id', String(64), nullable=False, index=False )
	_response = Column( 'response', Text, nullable=True, index=False )

	@property
	def response( self ):
		"For a database response value, transform it into a useable state."
		response = json.loads( self._response )
		if isinstance( response, dict ):
			# Convert to int keys, if possible.
			# We currently do not handle mixed types of keys.
			try:
				response = {int( x ): y for x,y in response.items()}
			except ValueError:
				pass
		return response

def _get_response_str( response ):
	return json.dumps( response )

def store_registration_data( user, data ):
	pass

def store_registration_survey_data( user, data ):
	pass

def _resolve_registration( row, user=None ):
	if user is not None:
		row.user = user
	return row

def get_registrations( user=None, **kwargs ):
	results = get_filtered_records( user, RegistrationSurveysTaken, **kwargs )
	return resolve_objects( _resolve_registration, results, user=user )
