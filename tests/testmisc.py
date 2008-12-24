#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
from wicd import misc

class TestMisc(unittest.TestCase):
    def test_misc_run(self):
        output = misc.Run(['echo', 'hi']).strip()
        self.assertEquals('hi', output)

    def test_valid_ip_1(self):
        self.assertTrue(misc.IsValidIP('0.0.0.0'))

    def test_valid_ip_2(self):
        self.assertTrue(misc.IsValidIP('255.255.255.255'))

    def test_valid_ip_3(self):
        self.assertTrue(misc.IsValidIP('10.0.1.1'))

    def test_invalid_ip_1(self):
        self.assertFalse(misc.IsValidIP('-10.0.-1.-1'))

    def test_invalid_ip_2(self):
        self.assertFalse(misc.IsValidIP('256.0.0.1'))

    def test_invalid_ip_3(self):
        self.assertFalse(misc.IsValidIP('1000.0.0.1'))

    def test_run_valid_regex(self):
        import re
        regex = re.compile('.*(ABC.EFG).*')
        found = misc.RunRegex(regex, '01234ABCDEFG56789')
        self.assertEquals(found, 'ABCDEFG')

    def test_run_invalid_regex(self):
        import re
        regex = re.compile('.*(ABC.EFG).*')
        found = misc.RunRegex(regex, '01234ABCEDFG56789')
        self.assertEquals(found, None)

    def test_to_boolean_false(self):
        self.assertFalse(misc.to_bool('False'))

    def test_to_boolean_0(self):
        self.assertFalse(misc.to_bool('0'))

    def test_to_boolean_true(self):
        self.assertTrue(misc.to_bool('True'))

    def test_to_boolean_true(self):
        self.assertTrue(misc.to_bool('1'))

    def test_noneify_1(self):
        self.assertEquals(misc.Noneify('None'), None)

    def test_noneify_2(self):
        self.assertEquals(misc.Noneify(''), None)

    def test_noneify_3(self):
        self.assertEquals(misc.Noneify(None), None)

    def test_noneify_4(self):
        self.assertFalse(misc.Noneify('False'))

    def test_noneify_5(self):
        self.assertFalse(misc.Noneify('0'))

    def test_noneify_6(self):
        self.assertFalse(misc.Noneify(False))

    def test_noneify_7(self):
        self.assertTrue(misc.Noneify('True'))

    def test_noneify_8(self):
        self.assertTrue(misc.Noneify('1'))

    def test_noneify_9(self):
        self.assertTrue(misc.Noneify(True))

    def test_noneify_10(self):
        self.assertEquals(misc.Noneify('randomtext'), 'randomtext')

    def test_noneify_11(self):
        self.assertEquals(misc.Noneify(5), 5)

    def test_none_to_string_1(self):
        self.assertEquals(misc.noneToString(None), 'None')

    def test_none_to_string_2(self):
        self.assertEquals(misc.noneToString(''), 'None')

    def test_none_to_string_3(self):
        self.assertEquals(misc.noneToString(None), 'None')

    ####################################################################
    # misc.to_unicode actually converts to utf-8, which is type str    #
    ####################################################################

    def test_to_unicode_1(self):
        self.assertEquals(misc.to_unicode('邪悪'), '邪悪')

    def test_to_unicode_2(self):
        self.assertEquals(misc.to_unicode(u'邪悪'), '邪悪')

    def test_to_unicode_3(self):
        self.assertEquals(misc.to_unicode(u'abcdef'), 'abcdef')

    def test_to_unicode_4(self):
        self.assertEquals(type(misc.to_unicode('abcdef'.encode('latin-1'))), str)

    def test_to_unicode_5(self):
        self.assertEquals(misc.to_unicode("berkåk"), "berkåk")

    def test_to_unicode_6(self):
        self.assertEquals(misc.to_unicode('berk\xe5k'), "berkåk")

    def test_none_to_blank_string_1(self):
        self.assertEquals(misc.noneToBlankString(None), '')

    def test_none_to_blank_string_2(self):
        self.assertEquals(misc.noneToBlankString('None'), '')

    def test_string_to_none_1(self):
        self.assertEquals(misc.stringToNone(''), None)

    def test_string_to_none_2(self):
        self.assertEquals(misc.stringToNone('None'), None)

    def test_string_to_none_3(self):
        self.assertEquals(misc.stringToNone(None), None)

    def test_string_to_none_4(self):
        self.assertEquals(misc.stringToNone('abcdef'), 'abcdef')

def suite():
	suite = unittest.TestSuite()
	tests = []
	[ tests.append(test) for test in dir(TestMisc) if test.startswith('test') ]
	for test in tests:
		suite.addTest(TestMisc(test))
	return suite

if __name__ == '__main__':
	unittest.main()
