
def run_tests():
    import unittest
    test_suite = unittest.TestSuite()

    import testwnettools
    test_suite.addTest(testwnettools.suite())

    unittest.TextTestRunner(verbosity=5).run(test_suite)
