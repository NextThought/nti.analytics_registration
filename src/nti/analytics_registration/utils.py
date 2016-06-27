#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.courses.utils import get_course_instructors

def get_all_course_instructors():
	"""
	Return the usernames of all instructors in all courses.
	"""
	# XXX: May need to limit to only certain courses by registration id.
	result = set()
	course_catalog = component.getUtility( ICourseCatalog )
	for entry in course_catalog.iterCatalogEntries():
		course = ICourseInstance(entry, None)
		if course is None:
			continue
		instructors = get_course_instructors( course )
		result.update( instructors )
	return result
