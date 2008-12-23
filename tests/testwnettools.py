import unittest
from wicd import wnettools

class TestWnettools(unittest.TestCase):
	def setUp(self):
		self.interface = wnettools.BaseInterface('eth0')
	
	def test_find_wireless_interface(self):
		interfaces = wnettools.GetWirelessInterfaces()
		# wlan0 may change depending on your system
		self.assertTrue('wlan0' in interfaces)
		
	def test_find_wired_interface(self):
		interfaces = wnettools.GetWiredInterfaces()
		# eth0 may change depending on your system
		self.assertTrue('eth0' in interfaces)
		
	def test_wext_is_valid_wpasupplicant_driver(self):
		self.assertTrue(wnettools.IsValidWpaSuppDriver('wext'))
		
	def test_needs_external_calls_not_implemented(self):
		self.assertRaises(NotImplementedError, wnettools.NeedsExternalCalls)
		
	def test_get_ip_not_implemented(self):
		self.assertRaises(NotImplementedError, self.interface.GetIP)
		
	def test_is_up_not_implemented(self):
		self.assertRaises(NotImplementedError, self.interface.IsUp)
		
	def test_enable_debug_mode(self):
		self.interface.SetDebugMode(True)
		self.assertTrue(self.interface.verbose)
		
	def test_disable_debug_mode(self):
		self.interface.SetDebugMode(False)
		self.assertFalse(self.interface.verbose)
		
	def test_interface_name_sanitation(self):
		interface = wnettools.BaseInterface('blahblah; uptime > /tmp/blah | cat')
		self.assertEquals(interface.iface, 'blahblahuptimetmpblahcat')
		
	def test_freq_translation_low(self):
		freq = '2.412 GHz'
		interface = wnettools.BaseWirelessInterface('wlan0')
		self.assertEquals(interface._FreqToChannel(freq), 1)
		
	def test_freq_translation_high(self):
		freq = '2.484 GHz'
		interface = wnettools.BaseWirelessInterface('wlan0')
		self.assertEquals(interface._FreqToChannel(freq), 14)
		
	def test_generate_psk(self):
		interface = wnettools.BaseWirelessInterface('wlan0')
		psk = interface.GeneratePSK({'essid' : 'Network 1', 'key' : 'arandompassphrase'})
		self.assertEquals(psk, 'd70463014514f4b4ebb8e3aebbdec13f4437ac3a9af084b3433f3710e658a7be')

def suite():
	suite = unittest.TestSuite()
	tests = []
	[ tests.append(test) for test in dir(TestWnettools) if test.startswith('test') ]
	for test in tests:
		suite.addTest(TestWnettools(test))
	return suite

if __name__ == '__main__':
	unittest.main()
