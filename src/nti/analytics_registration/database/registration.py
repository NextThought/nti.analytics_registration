#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import json

from six import string_types

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

from nti.analytics.database.users import get_or_create_user

from nti.analytics_registration.exceptions import NoUserRegistrationException
from nti.analytics_registration.exceptions import InvalidCourseMappingException
from nti.analytics_registration.exceptions import DuplicateUserRegistrationException
from nti.analytics_registration.exceptions import DuplicateRegistrationSurveyException

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

COURSE_TITLE_LENGTH = 128

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
	curriculum = Column( 'curriculum', String(COURSE_TITLE_LENGTH), nullable=False, index=False )
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
	curriculum = Column( 'curriculum', String(COURSE_TITLE_LENGTH), nullable=False, index=False )
	# See note in `RegistrationSessions`.
	course_ntiid = Column( 'course_ntiid', NTIID_COLUMN_TYPE, nullable=False, index=False )

class UserRegistrations(Base, BaseTableMixin, RegistrationMixin):
	"""
	Hold user registration information.
	"""
	__tablename__ = 'UserRegistrations'

	user_registration_id = Column('user_registration_id', Integer,
							Sequence('user_registration_id_seq'),
							index=True, nullable=False, primary_key=True)

	school = Column( 'school', String(128), nullable=True, index=False )
	grade_teaching = Column( 'grade_teaching', String(32), nullable=True, index=False )
	curriculum = Column( 'curriculum', String(COURSE_TITLE_LENGTH), nullable=False, index=False )
	employee_id = Column( 'employee_id', String(32), nullable=True, index=False )
	phone = Column( 'phone', String(16), nullable=True, index=False )
	session_range = Column('session_range', String(32),
							nullable=False, index=True, autoincrement=False)

	survey_submission = relationship( 'RegistrationSurveysTaken',
									  cascade="all, delete-orphan",
									  lazy="select" )

class RegistrationSurveysTaken(Base, BaseTableMixin):
	"""
	Contains information when users submit RegistrationSurvey responses. The
	survey is a one-to-one mapping to the registration process.
	"""
	__tablename__ = 'RegistrationSurveysTaken'

	registration_survey_taken_id = Column('registration_survey_taken_id', Integer,
										Sequence('registration_survey_taken_id_seq'),
										index=True, nullable=False, primary_key=True)

	survey_version = Column( 'survey_version', String(32), nullable=True, index=False )

	user_registration_id = Column('user_registration_id',
					  			Integer,
					 			ForeignKey("UserRegistrations.user_registration_id"),
					  			nullable=False,
					  			index=True)

	details = relationship( 'RegistrationSurveyDetails',
							cascade="all, delete-orphan",
							lazy="select" )

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
	registration = get_or_create_registration( registration_ds_id )
	registration_id = registration.registration_id
	if truncate:
		deleted_count = db.session.query( RegistrationEnrollmentRules ).filter(
										  RegistrationEnrollmentRules.registration_id == registration_id ).delete()
		logger.info( 'Deleted RegistrationEnrollmentRules (%s) (%s)',
					 registration_ds_id, deleted_count )
	for rule in rules:
		rule_record = RegistrationEnrollmentRules( registration_id=registration_id,
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
	registration = get_or_create_registration( registration_ds_id )
	registration_id = registration.registration_id
	if truncate:
		deleted_count = db.session.query( RegistrationSessions ).filter(
										  RegistrationSessions.registration_id == registration_id ).delete()
		logger.info( 'Deleted RegistrationSessions (%s) (%s)',
					 registration_ds_id, deleted_count )
	for session in sessions:
		session_record = RegistrationSessions( registration_id=registration_id,
										       session_range=session.session_range,
											   curriculum=session.curriculum,
											   course_ntiid=session.course_ntiid)
		db.session.add( session_record )
	return len( sessions )

def _validate_registration( registration_id, registration_ds_id, data ):
	"""
	Validate we received a correct registration mapping to a course,
	returning the curriculum.
	"""
	db = get_analytics_db()
	school = data.school
	grade_teaching = data.grade_teaching
	course_ntiid = data.course_ntiid
	rule = db.session.query( RegistrationEnrollmentRules ).filter(
							 RegistrationEnrollmentRules.registration_id == registration_id,
							 RegistrationEnrollmentRules.school == school,
							 RegistrationEnrollmentRules.grade_teaching == grade_teaching,
							 RegistrationEnrollmentRules.course_ntiid == course_ntiid ).first()
	if rule is None:
		logger.info( 'No mapping for %s (school=%s) (grade=%s) (ntiid=%s)',
					 registration_ds_id, school, grade_teaching, course_ntiid)
		raise InvalidCourseMappingException()
	return rule.curriculum

def store_registration_data( user, timestamp, session_id, registration_ds_id, data ):
	"""
 	Store user registration data.
	"""
	if get_user_registrations( user, registration_ds_id ):
		raise DuplicateUserRegistrationException()
	registration = get_or_create_registration( registration_ds_id )
	registration_id = registration.registration_id
	curriculum = _validate_registration( registration_id, registration_ds_id, data )
	db = get_analytics_db()
	user = get_or_create_user( user )
	user_registration = UserRegistrations( user_id=user.user_id,
										   timestamp=timestamp,
										   session_id=session_id,
										   registration_id=registration_id,
										   school=data.school,
										   grade_teaching=data.grade_teaching,
										   phone=data.phone,
										   curriculum=curriculum,
										   employee_id=data.employee_id,
										   session_range=data.session_range)
	db.session.add( user_registration )
	db.session.flush()

def _get_response_str( response ):
	return json.dumps( response )

def store_registration_survey_data( user, timestamp, session_id, registration_ds_id, version, data ):
	"""
 	Store user survey data.
	"""
	user_registrations = get_user_registrations( user, registration_ds_id )
	if not user_registrations:
		raise NoUserRegistrationException()
	user_registration = user_registrations[0]
	if user_registration.survey_submission:
		raise DuplicateRegistrationSurveyException()

	user_reg_id = user_registration.user_registration_id
	db = get_analytics_db()
	user = get_or_create_user( user )
	survey_submission = RegistrationSurveysTaken( user_id=user.user_id,
												  timestamp=timestamp,
												  session_id=session_id,
												  survey_version=version,
												  user_registration_id=user_reg_id )
	db.session.add( survey_submission )
	db.session.flush()
	registration_survey_taken_id = survey_submission.registration_survey_taken_id
	for key, value in data.items():
		response = _get_response_str( value )
		survey_detail = RegistrationSurveyDetails(
							registration_survey_taken_id=registration_survey_taken_id,
							question_id=key,
							_response=response)
		db.session.add( survey_detail )

def _resolve_registration( row, user=None ):
	if user is not None:
		row.user = user
	return row

def get_user_registrations( user=None, registration_ds_id=None, course=None, **kwargs ):
	"""
 	Get all registrations, optionally by user and/or registration_id.
	"""
	filters = ()
	if registration_ds_id:
		registration = get_registration( registration_ds_id )
		if registration is None:
			return ()
		filters = (UserRegistrations.registration_id == registration.registration_id,)
	results = get_filtered_records( user, UserRegistrations, filters=filters, **kwargs )
	user_registrations = resolve_objects( _resolve_registration, results, user=user )
	if course is not None:
		entry = ICourseCatalogEntry( course )
		course_ntiid = entry.ntiid
		db = get_analytics_db()
		# Exclude registrations not mapped to our course
		# XXX: We could make this easier...
		def _do_include( user_registration ):
			rule_for_course = db.session.query( RegistrationEnrollmentRules ).filter(
								 RegistrationEnrollmentRules.registration_id == user_registration.registration_id,
								 RegistrationEnrollmentRules.school == user_registration.school,
								 RegistrationEnrollmentRules.grade_teaching == user_registration.grade_teaching,
								 RegistrationEnrollmentRules.course_ntiid == course_ntiid ).first()
			return rule_for_course is not None
		user_registrations = [x for x in user_registrations if _do_include(x)]
	return user_registrations

def get_all_survey_questions( registration ):
	"""
	Given a registration, return all survey questions we know about
	for that registration id.
	"""
	db = get_analytics_db()
	if isinstance( registration, string_types ):
		registration = get_registration( registration )
		registration_id = registration.registration_id if registration is not None else None
	else:
		registration_id = getattr( registration, 'registration_id', None )

	result = set()
	if registration_id:
		registrations = db.session.query( UserRegistrations ).filter(
								  		  UserRegistrations.registration_id == registration_id ).all()
		for registration in registrations:
			if registration.survey_submission:
				survey = registration.survey_submission[0]
				for detail in survey.details:
					result.add( detail.question_id )
	return result

def delete_user_registrations( user=None, registration_ds_id=None ):
	"""
 	Delete the registrations (and surveys etc) associated with the
 	given user and registration_id. Should probably only be used
 	by admins in test environments.
	"""
	user_registrations = get_user_registrations( user, registration_ds_id )
	result = []
	if user_registrations:
		db = get_analytics_db()
		for registration in user_registrations:
			logger.info( 'Deleting registration (user=%s) (registration=%s)',
						 user, registration_ds_id )
			db.session.delete( registration )
			course_ntiid = _get_course_for_registration( registration,
														 registration_ds_id )
			# Return tuples of registration and course_ntiid.
			result.append( (registration, course_ntiid) )
	return result

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
	results = None
	if registration and registration.registration_sessions:
		results = registration.registration_sessions
		if sort:
			results = sorted( results,
							  key=lambda x: x.registration_session_id,
							  reverse=sort_descending )
	return results

def _get_course_for_registration( user_registration, registration_ds_id ):
	"""
	Use the registration info to retrieve a course ntiid.
	"""
	db = get_analytics_db()
	result = None
	registration_id = user_registration.registration_id
	school = user_registration.school
	grade_teaching = user_registration.grade_teaching
	curriculum = user_registration.curriculum
	rules = db.session.query( RegistrationEnrollmentRules ).filter(
							  RegistrationEnrollmentRules.registration_id == registration_id,
							  RegistrationEnrollmentRules.school == school,
							  RegistrationEnrollmentRules.grade_teaching == grade_teaching,
							  RegistrationEnrollmentRules.curriculum == curriculum ).all()
	if rules:
		if len( rules ) > 1 and len( {x.course_ntiid for x in rules} ) > 1:
			# Data issue; return nothing.
			logger.warn( 'Multiple course ntiids mapping to registration (%s) (%s) (%s)',
						 school, grade_teaching, registration_ds_id )
		else:
			result = rules[0].course_ntiid
	return result
