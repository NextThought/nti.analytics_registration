#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics_registration.database import registration as db_registration

from nti.analytics.common import timestamp_type
from nti.analytics.sessions import get_nti_session_id

get_user_registrations = db_registration.get_user_registrations
get_registration_rules = db_registration.get_registration_rules
get_all_survey_questions = db_registration.get_all_survey_questions
get_registration_sessions = db_registration.get_registration_sessions

store_registration_rules = db_registration.store_registration_rules
store_registration_sessions = db_registration.store_registration_sessions

delete_user_registrations = db_registration.delete_user_registrations

def store_registration_data( user, timestamp, registration_ds_id, data ):
	timestamp = timestamp_type( timestamp )
	session_id = get_nti_session_id()
	db_registration.store_registration_data( user, timestamp, session_id,
											 registration_ds_id, data )

def store_registration_survey_data( user, timestamp, registration_ds_id, version, data ):
	timestamp = timestamp_type( timestamp )
	session_id = get_nti_session_id()
	db_registration.store_registration_survey_data( user, timestamp, session_id,
													registration_ds_id,
													version, data )
