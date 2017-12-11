#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.analytics.stats.interfaces import IStats
from nti.analytics.stats.interfaces import IAnalyticsStatsSource

from nti.analytics_registration.registration import get_user_registrations
from nti.analytics_registration.registration import get_all_survey_questions

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IStats)
class _RegistrationStats(object):

    def __init__(self, record):
        self.phone = record.phone
        self.school = record.school
        self.grade_teaching = record.grade_teaching
        self.curriculum = record.curriculum
        self.employee_id = str(record.employee_id)
        self.session_range = record.session_range


def _get_question_key(question_id):
    # Remove whitespace
    result = '_'.join(question_id.split())
    return result


@interface.implementer(IStats)
class _SurveyStats(object):

    def __init__(self, survey_version, results, possible_questions):
        self.survey_version = survey_version
        seen = set()
        possible_questions = {_get_question_key(x) for x in possible_questions}
        for survey_question in results:
            var = _get_question_key(survey_question.question_id)
            seen.add(var)
            response = survey_question.response
            if isinstance(response, list):
                # Make sure our list response is readable.
                response = ', '.join((str(x) for x in response))
            setattr(self, var, response)
        # Make sure we have placeholder values for user.
        no_responses = possible_questions - seen
        for no_response in no_responses:
            setattr(self, no_response, '')


@interface.implementer(IAnalyticsStatsSource)
class _RegistrationStatsSource(object):
    """
    For a user's registration, build stats for registration and
    registration survey.
    """

    __external_class_name__ = "AnalyticsRegistrationStatsSource"
    mime_type = mimeType = 'application/vnd.nextthought.analytics_registration.registrationstatssource'

    display_name = 'Registration'

    def __init__(self, user, course=None):
        self.user = user
        self.course = course

    @Lazy
    def _registrations(self):
        records = get_user_registrations(user=self.user, course=self.course)
        return records[0] if records else None

    @Lazy
    def RegistrationStats(self):
        registration = self._registrations
        result = None
        if registration is not None:
            result = _RegistrationStats(registration)
        return result

    @Lazy
    def RegistrationSurveyStats(self):
        registration = self._registrations
        result = None
        # pylint: disable=no-member
        if registration is not None and registration.survey_submission:
            survey_submission = registration.survey_submission[0]
            survey_results = survey_submission.details
            all_questions = get_all_survey_questions(registration)
            survey_version = survey_submission.survey_version
            result = _SurveyStats(survey_version, survey_results, 
                                  all_questions)
        return result
