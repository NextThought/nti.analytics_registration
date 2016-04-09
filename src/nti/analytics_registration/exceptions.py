#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

class NoUserRegistrationException( Exception ):
	"""
	Indicates the user has not registered.
	"""
	pass

class InvalidCourseMappingException( Exception ):
	"""
	Indicates the given course NTIID is invalid according
	to the registration rules.
	"""
	pass

class DuplicateUserRegistrationException( Exception ):
	"""
	Indicates the user has already registered.
	"""
	pass

class DuplicateRegistrationSurveyException( Exception ):
	"""
	Indicates the user has multiple registration surveys submitted.
	"""
	pass
