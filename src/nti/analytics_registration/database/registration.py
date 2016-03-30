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
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import ForeignKey

from sqlalchemy.schema import Sequence
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from nti.analytics_database.meta_mixins import BaseTableMixin

from nti.analytics_database import Base
from nti.analytics_database import NTIID_COLUMN_TYPE

from nti.analytics.database import get_analytics_db
from nti.analytics.database import resolve_objects
from nti.analytics.database.query_utils import get_filtered_records

# FIXME: JZ - Table creation disabled for now
Base = object()

class Registrations(Base):
	"""
	Holds the registration identifier for a given string registration.
	"""
	__tablename__ = 'Registrations'

	registration_id = Column('registration_id', Integer,
							Sequence('registration_id_seq'),
							index=True, nullable=False, primary_key=True)

	registration_ds_id = Column('registration_ds_id', String(128),
								nullable=False, index=True, autoincrement=False)

	registration_sessions = relationship( 'RegistrationSessions', lazy="select" )
	registration_rules = relationship( 'RegistrationEnrollmentRules', lazy="select" )

class RegistrationMixin(object):

	@declared_attr
	def registration_id(cls):
		return Column('registration_id',
					   Integer,
					   ForeignKey("Registrations.registration_id"),
					   nullable=False,
					   index=True)

class RegistrationSessions(Base, RegistrationMixin):
	"""
	Holds session dates feed information for a registration.
	"""
	__tablename__ = 'RegistrationSessions'

	registration_session_id = Column('registration_session_id', Integer,
							Sequence('registration_session_id_seq'),
							index=True, nullable=False, primary_key=True)

	session_range = Column('session_range', String(32),
							nullable=False, index=True, autoincrement=False)
	curriculum = Column( 'curriculum', String(32), nullable=False, index=False )
	# This does not need to be mapped to our Courses table. We just expose this
	# to clients and use this information for enrollment. Plus it allows these
	# courses to not exist at insertion time.
	course_ntiid = Column( 'course_ntiid', NTIID_COLUMN_TYPE, nullable=False, index=False )

class RegistrationEnrollmentRules(Base, RegistrationMixin):
	"""
	Contains rules about which registration data map to NT courses.
	"""
	__tablename__ = 'RegistrationEnrollmentRules'

	registration_rule_id = Column('registration_rule_id', Integer,
							Sequence('registration_rule_id_seq'),
							index=True, nullable=False, primary_key=True)

	school = Column( 'school', String(128), nullable=False, index=False )
	grade_teaching = Column( 'grade_teaching', String(32), nullable=False, index=False )
	curriculum = Column( 'curriculum', String(32), nullable=False, index=False )
	# See note in `RegistrationSessions`.
	course_ntiid = Column( 'course_ntiid', NTIID_COLUMN_TYPE, nullable=False, index=False )

class UserRegistrations(Base, BaseTableMixin, RegistrationMixin):
	"""
	Hold user registration information.
	XXX: i2 specific? place in site?
	"""
	__tablename__ = 'UserRegistrations'

	user_registration_id = Column('user_registration_id', Integer,
							Sequence('user_registration_id_seq'),
							index=True, nullable=False, primary_key=True)

	school = Column( 'school', String(128), nullable=True, index=False )
	grade_teaching = Column( 'grade_teaching', String(32), nullable=True, index=False )
	curriculum = Column( 'curriculum', String(32), nullable=True, index=False )
	phone = Column( 'phone', String(16), nullable=True, index=False )
	session_range = Column('session_range', String(32),
							nullable=False, index=True, autoincrement=False)

class RegistrationSurveysTaken(Base, BaseTableMixin):
	"""
	Contains information when users submit RegistrationSurvey responses. The
	survey is a one-to-one mapping to the registration process.
	"""
	__tablename__ = 'RegistrationSurveysTaken'

	registration_survey_taken_id = Column('registration_survey_taken_id', Integer,
										Sequence('registration_survey_taken_id_seq'),
										index=True, nullable=False, primary_key=True)

	user_registration_id = Column('user_registration_id',
					  			Integer,
					 			ForeignKey("UserRegistration.user_registration_id"),
					  			nullable=False,
					  			index=True)

	details = relationship( 'RegistrationSurveyDetails', lazy="select" )

class RegistrationSurveyDetails(Base):
	"""
	Stores survey submission details in a simple key/value store.
	"""
	__tablename__ = 'RegistrationSurveyDetails'

	registration_survey_detail_id = Column('registration_survey_detail_id', Integer,
										Sequence('registration_survey_detail_id_seq'),
										index=True, nullable=False, primary_key=True)

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

def get_registration( registration_ds_id ):
	db = get_analytics_db()
	registration = db.session.query(Registrations).filter(
									Registrations.registration_ds_id == registration_ds_id).first()
	return registration

def get_or_create_registration( registration_ds_id ):
	registration = get_registration( registration_ds_id )
	if registration is None:
		db = get_analytics_db()
		registration = Registrations( registration_ds_id=registration_ds_id )
		db.session.add( registration )
		db.session.flush()
	return registration

def store_registration_rules( registration_ds_id, rules, truncate=True ):
	"""
	Store the given registration rules, optionally truncating previous data.
	No validation is done here.
	"""
	db = get_analytics_db()
	if truncate:
		deleted_count = db.session.query( RegistrationEnrollmentRules ).delete()
		logger.info( 'Truncated RegistrationEnrollmentRules (%s)', deleted_count )
	registration = get_or_create_registration( registration_ds_id )
	for rule in rules:
		rule_record = RegistrationEnrollmentRules( registration_id=registration.registration_id,
												   school=rule.school,
												   curriculum=rule.curriculum,
												   grade_teaching=rule.grade,
												   course_ntiid=rule.course_ntiid)
		db.session.add( rule_record )
	return len( rules )

def store_registration_sessions( registration_ds_id, sessions, truncate=True ):
	"""
	Store the given registration sessions, optionally truncating previous data.
	No validation is done here.
	"""
	db = get_analytics_db()
	if truncate:
		deleted_count = db.session.query( RegistrationSessions ).delete()
		logger.info( 'Truncated RegistrationSessions (%s)', deleted_count )
	registration = get_or_create_registration( registration_ds_id )
	for session in sessions:
		session_record = RegistrationSessions( registration_id=registration.registration_id,
										       session_range=session.school,
											   curriculum=session.curriculum,
											   course_ntiid=session.course_ntiid)
		db.session.add( session_record )
	return len( sessions )

# FIXME: Implement
def store_registration_data( user, registration_id, data ):
	# FIXME: One submission per user validation
	pass

def store_registration_survey_data( user, registration_id, data ):
	pass

def _resolve_registration( row, user=None ):
	if user is not None:
		row.user = user
	return row

def get_user_registrations( user=None, registration_id=None, **kwargs ):
	"""
 	Get all registrations, optionally by user and/or registration_id.
	"""
	filters = ()
	if registration_id:
		registration = get_registration( registration_id )
		if registration is None:
			return ()
		filters = (UserRegistrations.registration_id == registration.registration_id,)
	results = get_filtered_records( user, UserRegistrations, filters=filters, **kwargs )
	return resolve_objects( _resolve_registration, results, user=user )

def get_registration_rules( registration_ds_id, sort=True, sort_descending=False ):
	"""
 	Get the registration rules for the given registration id. By
 	default, sorted by insertion order ascending.
	"""
	registration = get_registration( registration_ds_id )
	results = None
	if registration and registration.registration_rules:
		results = registration.registration_rules
		if sort:
			results = sorted( results,
							  key=lambda x: x.registration_rule_id,
							  reverse=sort_descending )
	return results

def get_registration_sessions( registration_ds_id, sort=True, sort_descending=False ):
	"""
 	Get the registration sessions for the given registration id. By
 	default, sorted by insertion order ascending.
	"""
	registration = get_registration( registration_ds_id )
	if registration and registration.registration_sessions:
		results = registration.registration_rules
		if sort:
			results = sorted( results,
							  key=lambda x: x.registration_session_id,
							  reverse=sort_descending )
	return results
