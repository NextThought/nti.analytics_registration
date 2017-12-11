#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import has_key
from hamcrest import assert_that

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests.mock_dataserver import mock_db_trans


class TestFunctionalInstall(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test_installed(self):
        with mock_db_trans(self.ds) as conn:

            root = conn.root()
            generations = root['zope.generations']
            assert_that(generations, 
                        has_key('nti.dataserver-analytics_registration'))
