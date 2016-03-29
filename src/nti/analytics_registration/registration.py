#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics_registration.database import registration as db_registration

get_registrations = db_registration.get_registrations
store_registration_data = db_registration.store_registration_data
store_registration_rules = db_registration.store_registration_rules
store_registration_sessions = db_registration.store_registration_sessions
store_registration_survey_data = db_registration.store_registration_survey_data
