#!/usr/bin/python
import os,sys
if __name__ == '__main__':
	os.chdir(os.path.dirname(os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))))
try:
	import pygtk
	pygtk.require("2.0")
except:
	pass
try:
	import gtk, gtk.glade
except:
	print 'Missing GTK and gtk.glade.  Aborting.'
	sys.exit(1)


import time, os, misc, gettext, locale, gobject, dbus, dbus.service

if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
	import dbus.glib

#declare the connections to the daemon, so that they may be accessed
#in any class
bus = dbus.SystemBus()
try:
	print 'attempting to connect daemon...'
	proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
	print 'success'
except:
	print 'daemon not running, running gksudo ./daemon.py...'
	misc.PromptToStartDaemon()
	time.sleep(1)
	try:
		proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
	except:
		print 'daemon still not running, aborting.'
daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')
wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')
wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
config = dbus.Interface(proxy_obj, 'org.wicd.daemon.config')

#Translation stuff
#borrowed from an excellent post on how to do this on
#http://www.learningpython.com/2006/12/03/translating-your-pythonpygtk-application/
#which is also under GPLv2

#Get the local directory since we are not installing anything
local_path = os.path.realpath(os.path.dirname(sys.argv[0])) + '/translations'
# Init the list of languages to support
langs = list()
#Check the default locale
lc, encoding = locale.getdefaultlocale()
if (lc):
	#If we have a default, it's the first in the list
	langs = [lc]
# Now lets get all of the supported languages on the system
osLanguage = os.environ.get('LANGUAGE', None)
if (osLanguage):
	#langage comes back something like en_CA:en_US:en_GB:en
	#on linuxy systems, on Win32 it's nothing, so we need to
	#split it up into a list
	langs += osLanguage.split(":")

#Now add on to the back of the list the translations that we
#know that we have, our defaults
langs += ["en_US"] # I add english because a lot of people can read it
#Now langs is a list of all of the languages that we are going
#to try to use.  First we check the default, then what the system
#told us, and finally the 'known' list

gettext.bindtextdomain('wicd', local_path)
gettext.textdomain('wicd')
# Get the language to use
lang = gettext.translation('wicd', local_path, languages=langs, fallback = True)

#map _() to self.lang.gettext() which will translate them.
_ = lang.gettext

#keep all the language strings in a dictionary
#by the english words
#I'm not sure this is the best way to do it
#but it works and makes it easy for me :)
##########
# translations are done at
# http://wicd.sourceforge.net/wiki/doku.php?id=translations
# please translate if you can!
##########
language = {}
language['connect'] = _("Connect")
language['ip'] = _("IP")
language['netmask'] = _("Netmask")
language['gateway'] = _('Gateway')
language['dns'] = _('DNS')
language['use_static_ip'] = _('Use Static IPs')
language['use_static_dns'] = _('Use Static DNS')
language['use_encryption'] = _('Use Encryption')
language['advanced_settings'] = _('Advanced Settings')
language['wired_network'] = _('Wired Network')
language['wired_network_instructions'] = _('To connect to a wired network, you must create a network profile.  To create a network profile, type a name that describes this network, and press Add.')
language['automatic_connect'] = _('Automatically connect to this network')
language['secured'] = _('Secured')
language['unsecured'] = _('Unsecured')
language['channel'] = _('Channel')
language['preferences'] = _('Preferences')
language['wpa_supplicant_driver'] = _('WPA Supplicant Driver')
language['wireless_interface'] = _('Wireless Interface')
language['wired_interface'] = _('Wired Interface')
language['hidden_network'] = _('Hidden Network')
language['hidden_network_essid'] = _('Hidden Network ESSID')
language['connected_to_wireless'] = _('Connected to $A at $B% (IP: $C)')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['not_connected'] = _('Not connected')
language['no_wireless_networks_found'] = _('No wireless networks found.')
language['key'] = _('Key')
language['username'] = _('Username')
language['password'] = _('Password')
language['anonymous_identity'] = _('Anonymous Identity')
language['identity'] = _('Identity')
language['authentication'] = _('Authentication')
language['path_to_pac_file'] = _('Path to PAC File')
language['select_a_network'] = _('Choose from the networks below:')
language['connecting'] = _('Connecting...')
language['wired_always_on'] = _('Always show wired interface')
language['auto_reconnect'] = _('Automatically reconnect on connection loss')

language['0'] = _('0')
language['1'] = _('1')
language['2'] = _('2')
language['3'] = _('3')
language['4'] = _('4')
language['5'] = _('5')
language['6'] = _('6')
language['7'] = _('7')
language['8'] = _('8')
language['9'] = _('9')

language['interface_down'] = _('Putting interface down...')
language['resetting_ip_address'] = _('Resetting IP address...')
language['interface_up'] = _('Putting interface up...')
language['removing_old_connection'] = _('Removing old connection...')
language['generating_psk'] = _('Generating PSK...')
language['generating_wpa_config'] = _('Generating WPA configuration file...')
language['flushing_routing_table'] = _('Flushing the routing table...')
language['configuring_interface'] = _('Configuring wireless interface...')
language['setting_broadcast_address'] = _('Setting broadcast address...')
language['setting_static_dns'] = _('Setting static DNS servers...')
language['setting_static_ip'] = _('Setting static IP addresses...')
language['running_dhcp'] = _('Obtaining IP address...')
language['create_adhoc_network'] = _('Create an Ad-Hoc Network')
language['essid'] = _('ESSID')


language['done'] = _('Done connecting...')

########################################
##### GTK EXTENSION CLASSES
########################################

class LinkButton(gtk.EventBox):
	label = None
	def __init__(self):
		gtk.EventBox.__init__(self)
		self.connect("realize",self.__setHandCursor) #set the hand cursor when the box is initalized
		label = gtk.Label()
		label.set_markup(" <span color=\"blue\">" + language['connect'] + "</span>") 
		label.set_alignment(0,.5)
		label.show()
		self.add(label)
		self.show_all()
		
	def __setHandCursor(self,widget):
		#we need this to set the cursor to a hand for the link labels
		#I'm not entirely sure what it does :P
		hand = gtk.gdk.Cursor(gtk.gdk.HAND1)
		widget.window.set_cursor(hand)

class SmallLabel(gtk.Label):
	def __init__(self,text=''):
		gtk.Label.__init__(self,text)
		self.set_size_request(50,-1)

class LabelEntry(gtk.HBox):
	'''a label on the left with a textbox on the right'''
	def __init__(self,text):
		gtk.HBox.__init__(self)
		self.entry = gtk.Entry()
		self.entry.set_size_request(200,-1)
		self.label = SmallLabel()
		self.label.set_text(text)
		self.label.set_size_request(170,-1)
		self.pack_start(self.label,fill=False,expand=False)
		self.pack_start(self.entry,fill=False,expand=False)
		self.label.show()
		self.entry.show()
		self.entry.connect('focus-out-event',self.hide_characters)
		self.entry.connect('focus-in-event',self.show_characters)
		self.auto_hide_text = False
		self.show()

	def set_text(self,text):
		#for compatibility...
		self.entry.set_text(text)

	def get_text(self):
		return self.entry.get_text()

	def set_auto_hidden(self,value):
		self.entry.set_visibility(False)
		self.auto_hide_text = value

	def show_characters(self,widget=None,event=None):
		#when the box has focus, show the characters
		if self.auto_hide_text and widget:
			self.entry.set_visibility(True)

	def hide_characters(self,widget=None,event=None):
		#when the box looses focus, hide them
		if self.auto_hide_text and widget:
			self.entry.set_visibility(False)
class GreyLabel(gtk.Label):
	def __init__(self):
		gtk.Label.__init__(self)
	def set_label(self,text):
		self.set_markup("<span color=\"grey\"><i>" + text + "</i></span>")
		self.set_alignment(0,0)

########################################
##### OTHER RANDOM FUNCTIONS
########################################

def noneToString(text):
	'''used for putting text in a text box if the value to put in is 'None' the box will be blank'''
	if text == None or text == "None" or text == "":
		return "None" 
	else:
		return str(text)

def noneToBlankString(text):
	'''if text is None, 'None', or '' then return '', otherwise return str(text)'''
	if text == None or text == "None" or text == "":
		return ""
	else:
		return str(text)

def stringToNone(text):
	'''performs opposite function of noneToString'''
	if text == "" or text == "None" or text == None:
		return None
	else:
		return str(text)

def stringToBoolean(text):
	'''turns a "True" to True or a "False" to False otherwise returns the text'''
	if text == "True":
		return True
	if text == "False":
		return False
	return text

########################################
##### NETWORK LIST CLASSES
######################################## 


class PrettyNetworkEntry(gtk.HBox):
	'''adds an image and a connect button to a NetworkEntry'''
	def __init__(self,expander):
		gtk.HBox.__init__(self)
		#add the stuff to the hbox (self)
		self.expander = expander
		self.expander.show()
		self.expander.higherLevel = self #do this so that the expander can access the stuff inside me
		self.tempVBox = gtk.VBox(False,1)
		self.tempVBox.show()
		self.connectButton = LinkButton()
		self.connectButton.show()
		self.tempVBox.pack_start(self.expander,fill=False,expand=False)
		self.tempVBox.pack_start(self.connectButton,fill=False,expand=False)
		self.pack_end(self.tempVBox)

class PrettyWiredNetworkEntry(PrettyNetworkEntry):
	def __init__(self):
		PrettyNetworkEntry.__init__(self,WiredNetworkEntry())
		#center the picture and pad it a bit
		self.image = gtk.Image()
		self.image.set_alignment(.5,0)

		self.image.set_size_request(60,-1)
		self.image.set_from_icon_name("network-wired",6) 
		self.image.show()
		self.pack_start(self.image,fill=False,expand=False)
		self.show()
		self.expander.checkEnable()
		self.expander.show()


class PrettyWirelessNetworkEntry(PrettyNetworkEntry):
	def __init__(self,networkID):
		PrettyNetworkEntry.__init__(self,WirelessNetworkEntry(networkID))
		self.image = gtk.Image()
		self.image.set_padding(0,0)
		self.image.set_alignment(.5,0)
		self.image.set_size_request(60,-1)
		self.image.set_from_icon_name("network-wired",6) 
		self.pack_start(self.image,fill=False,expand=False)
		self.setSignalStrength(wireless.GetWirelessProperty(networkID,'quality'))
		self.setMACAddress(wireless.GetWirelessProperty(networkID,'bssid'))
		self.setMode(wireless.GetWirelessProperty(networkID,'mode'))
		self.setChannel(wireless.GetWirelessProperty(networkID,'channel'))
		self.setEncryption(wireless.GetWirelessProperty(networkID,'encryption'),wireless.GetWirelessProperty(networkID,'encryption_method'))
		#show everything
		self.show_all()
	
	def setSignalStrength(self,strength):
		strength = int(strength)
		if strength > 75:
			self.image.set_from_file("images/signal-100.png")
		elif strength > 50:
			self.image.set_from_file("images/signal-75.png")
		elif strength > 25:
			self.image.set_from_file("images/signal-50.png")
		else:
			self.image.set_from_file("images/signal-25.png")
		self.expander.setSignalStrength(strength)
		
	def setMACAddress(self,address):
		self.expander.setMACAddress(address)

	def setEncryption(self,on,type):
		self.expander.setEncryption(on,type)

	def setChannel(self,channel):
		self.expander.setChannel(channel)

	def setMode(self,mode):
		self.expander.setMode(mode)

class NetworkEntry(gtk.Expander):
	'''the basis for the entries in the network list'''
	def __init__(self):
		#make stuff exist, this is pretty long and boring
		gtk.Expander.__init__(self)
		self.txtIP = LabelEntry(language['ip'])
		self.txtIP.entry.connect('focus-out-event',self.setDefaults)
		self.txtNetmask = LabelEntry(language['netmask'])
		self.txtGateway = LabelEntry(language['gateway'])
		self.txtDNS1 = LabelEntry(language['dns'] + language['1'])
		self.txtDNS2 = LabelEntry(language['dns'] + language['2'])
		self.txtDNS3 = LabelEntry(language['dns'] + language['3'])
		self.checkboxStaticIP = gtk.CheckButton(language['use_static_ip'])
		self.checkboxStaticDNS = gtk.CheckButton(language['use_static_dns'])
		self.expanderAdvanced = gtk.Expander(language['advanced_settings'])
		self.vboxTop = gtk.VBox(False,0)
		self.vboxAdvanced = gtk.VBox(False,0)
		self.vboxAdvanced.pack_start(self.checkboxStaticIP,fill=False,expand=False)
		self.vboxAdvanced.pack_start(self.txtIP,fill=False,expand=False)
		self.vboxAdvanced.pack_start(self.txtNetmask,fill=False,expand=False)
		self.vboxAdvanced.pack_start(self.txtGateway,fill=False,expand=False)
		self.vboxAdvanced.pack_start(self.checkboxStaticDNS,fill=False,expand=False)
		self.vboxAdvanced.pack_start(self.txtDNS1,fill=False,expand=False)
		self.vboxAdvanced.pack_start(self.txtDNS2,fill=False,expand=False)
		self.vboxAdvanced.pack_start(self.txtDNS3,fill=False,expand=False)
		self.vboxTop.pack_end(self.expanderAdvanced,fill=False,expand=False)
		self.expanderAdvanced.add(self.vboxAdvanced)
		#connect the events to the actions
		self.checkboxStaticIP.connect("toggled",self.toggleIPCheckbox)
		self.checkboxStaticDNS.connect("toggled",self.toggleDNSCheckbox)
		self.add(self.vboxTop)
		#start with all disabled, then they will be enabled later
		self.checkboxStaticIP.set_active(False)
		self.checkboxStaticDNS.set_active(False)
	
	def setDefaults(self,widget=None,event=None):
		#after the user types in the IP address,
		#help them out a little
		ipAddress = self.txtIP.get_text() #for easy typing :)
		netmask = self.txtNetmask
		gateway = self.txtGateway
		
		if ipAddress != None: #make sure the is an IP in the box
			if ipAddress.count('.') == 3: #make sure the IP can be parsed
				ipNumbers = ipAddress.split('.') #split it up
				if not '' in ipNumbers: #make sure the IP isn't something like 127..0.1
					if stringToNone(gateway.get_text()) == None: #make sure the gateway box is blank
						#fill it in with a .1 at the end
						gateway.set_text('.'.join(ipNumbers[0:3]) + '.1') 

					if stringToNone(netmask.get_text()) == None: #make sure the netmask is blank
						netmask.set_text('255.255.255.0') #fill in the most common one


	def resetStaticCheckboxes(self):
		#enable the right stuff
		if not stringToNone(self.txtIP.get_text()) == None:
			self.checkboxStaticIP.set_active(True)
			self.checkboxStaticDNS.set_active(True)
			self.checkboxStaticDNS.set_sensitive(False)
			print 'enabling ip'
		else:
			self.checkboxStaticIP.set_active(False)
			self.checkboxStaticDNS.set_active(False)
			self.checkboxStaticDNS.set_sensitive(True)
			print 'disabling ip'

		if not stringToNone(self.txtDNS1.get_text()) == None:
			self.checkboxStaticDNS.set_active(True)
			print 'enabling dns'
		else:
			self.checkboxStaticDNS.set_active(False)
			print 'disabling dns'

		#blankify stuff!
		#this will properly disable
		#unused boxes
		self.toggleIPCheckbox()
		self.toggleDNSCheckbox()

	def toggleIPCheckbox(self,widget=None):
		#should disable the static IP text boxes
		#and also enable the DNS checkbox when
		#disabled and disable when enabled

		if self.checkboxStaticIP.get_active():
			self.checkboxStaticDNS.set_active(True)
			self.checkboxStaticDNS.set_sensitive(False)
		else:
			self.checkboxStaticDNS.set_sensitive(True)

		self.txtIP.set_sensitive(self.checkboxStaticIP.get_active())
		self.txtNetmask.set_sensitive(self.checkboxStaticIP.get_active())
		self.txtGateway.set_sensitive(self.checkboxStaticIP.get_active())

	def toggleDNSCheckbox(self,widget=None):
		#should disable the static DNS boxes
		if self.checkboxStaticIP.get_active() == True:
			self.checkboxStaticDNS.set_active(self.checkboxStaticIP.get_active())
			self.checkboxStaticDNS.set_sensitive(False)
			
		self.txtDNS1.set_sensitive(self.checkboxStaticDNS.get_active())
		self.txtDNS2.set_sensitive(self.checkboxStaticDNS.get_active())
		self.txtDNS3.set_sensitive(self.checkboxStaticDNS.get_active())
class WiredNetworkEntry(NetworkEntry):
	#creates the wired network expander
	def __init__(self):
		NetworkEntry.__init__(self)
		self.set_label(language['wired_network'])
		self.resetStaticCheckboxes()
		self.comboProfileNames = gtk.combo_box_entry_new_text()
		profileList = config.GetWiredProfileList()
		if profileList: #make sure there is something in it...
			for x in config.GetWiredProfileList(): #add all the names to the combobox
				self.comboProfileNames.append_text(x)
		hboxTemp = gtk.HBox(False,0)
		self.profileHelp = gtk.Label(language['wired_network_instructions'])
		self.profileHelp.set_width_chars(5) #the default is a tad too long
		self.profileHelp.set_padding(10,10)
		self.profileHelp.set_justify(gtk.JUSTIFY_LEFT)
		self.profileHelp.set_line_wrap(True)
		self.vboxTop.pack_start(self.profileHelp,fill=False,expand=False)
		hboxTemp.pack_start(self.comboProfileNames,fill=True,expand=True)
		buttonOK = gtk.Button(stock=gtk.STOCK_ADD)
		self.buttonDelete = gtk.Button(stock=gtk.STOCK_DELETE)
		hboxTemp.pack_start(buttonOK,fill=False,expand=False)
		hboxTemp.pack_start(self.buttonDelete,fill=False,expand=False)
		buttonOK.connect("clicked",self.addProfile) #hook up our buttons
		self.buttonDelete.connect("clicked",self.removeProfile)
		self.comboProfileNames.connect("changed",self.changeProfile)
		self.vboxTop.pack_start(hboxTemp)
		self.show_all()
		self.profileHelp.hide()
		if profileList != None:
			self.comboProfileNames.set_active(0)
			print "wired profiles found"
			self.set_expanded(False)
		else:
			print "no wired profiles found"
			if not wired.GetAlwaysShowWiredInterface():
				self.set_expanded(True)
			self.profileHelp.show()
	def checkEnable(self):
		profileList = config.GetWiredProfileList()
		if profileList == None:
			self.buttonDelete.set_sensitive(False)
			self.higherLevel.connectButton.set_sensitive(False)
			self.vboxAdvanced.set_sensitive(False)
	def addProfile(self,widget):
		print "adding profile"
		profileName = self.comboProfileNames.get_active_text()
		profileList = config.GetWiredProfileList()
		if profileList:
			if profileName in profileList:
				return False
		if profileName != "":
			self.profileHelp.hide()
			config.CreateWiredNetworkProfile(profileName)
			self.comboProfileNames.prepend_text(profileName)
			self.comboProfileNames.set_active(0)
			self.buttonDelete.set_sensitive(True)
			self.vboxAdvanced.set_sensitive(True)
			self.higherLevel.connectButton.set_sensitive(True)

	def removeProfile(self,widget):
		print "removing profile"
		config.DeleteWiredNetworkProfile(self.comboProfileNames.get_active_text())
		self.comboProfileNames.remove_text(self.comboProfileNames.get_active())
		self.comboProfileNames.set_active(0)
		if config.GetWiredProfileList() == None:
			self.profileHelp.show()
			entry = self.comboProfileNames.child
			entry.set_text("")
			self.buttonDelete.set_sensitive(False)
			self.vboxAdvanced.set_sensitive(False)
			self.higherLevel.connectButton.set_sensitive(False)
		else:
			self.profileHelp.hide()

	def changeProfile(self,widget):
		if self.comboProfileNames.get_active() > -1: #this way the name doesn't change
			#				     #everytime someone types something in
			print "changing profile..."
			profileName = self.comboProfileNames.get_active_text()
			print profileName
			config.ReadWiredNetworkProfile(profileName)
			
			self.txtIP.set_text(noneToBlankString(wired.GetWiredProperty("ip")))
			self.txtNetmask.set_text(noneToBlankString(wired.GetWiredProperty("netmask")))
			self.txtGateway.set_text(noneToBlankString(wired.GetWiredProperty("gateway")))

			self.txtDNS1.set_text(noneToBlankString(wired.GetWiredProperty("dns1")))
			self.txtDNS2.set_text(noneToBlankString(wired.GetWiredProperty("dns2")))
			self.txtDNS3.set_text(noneToBlankString(wired.GetWiredProperty("dns3")))

			self.resetStaticCheckboxes()
class WirelessNetworkEntry(NetworkEntry):
	#this class is respsponsible for creating the expander
	#in each wirelessnetwork entry
	def __init__(self,networkID):
		self.networkID = networkID
		#create the data labels
		NetworkEntry.__init__(self)
		print "ESSID : " + wireless.GetWirelessProperty(networkID,"essid")
		self.set_label(wireless.GetWirelessProperty(networkID,"essid"))
		self.essid = wireless.GetWirelessProperty(networkID,"essid")
		print "making a new network entry..."

		#make the vbox to hold the encryption stuff
		self.vboxEncryptionInformation = gtk.VBox(False,0)
		#make the combo box
		self.comboEncryption = gtk.combo_box_new_text()
		self.checkboxEncryption = gtk.CheckButton(language['use_encryption'])
		self.lblStrength = GreyLabel()
		self.lblEncryption = GreyLabel()
		self.lblMAC = GreyLabel()
		self.lblChannel = GreyLabel()
		self.lblMode = GreyLabel()
		self.hboxStatus = gtk.HBox(False,5)
		self.checkboxAutoConnect = gtk.CheckButton(language['automatic_connect'])
		self.checkboxAutoConnect.connect("toggled",self.updateAutoConnect) #so that the autoconnect box is
										   #toggled

		self.hboxStatus.pack_start(self.lblStrength,fill=False,expand=True)
		self.hboxStatus.pack_start(self.lblEncryption,fill=False,expand=True)
		self.hboxStatus.pack_start(self.lblMAC,fill=False,expand=True)
		self.hboxStatus.pack_start(self.lblMode,fill=False,expand=True)
		self.hboxStatus.pack_start(self.lblChannel,fill=False,expand=True)

		self.vboxTop.pack_start(self.checkboxAutoConnect,fill=False,expand=False)
		self.vboxTop.pack_start(self.hboxStatus,fill=True,expand=False)

		self.vboxAdvanced.pack_start(self.checkboxEncryption,fill=False,expand=False)

		self.txtIP.set_text(noneToBlankString(wireless.GetWirelessProperty(networkID,"ip")))
		self.txtNetmask.set_text(noneToBlankString(wireless.GetWirelessProperty(networkID,"netmask")))
		self.txtGateway.set_text(noneToBlankString(wireless.GetWirelessProperty(networkID,"gateway")))

		self.txtDNS1.set_text(noneToBlankString(wireless.GetWirelessProperty(networkID,"dns1")))
		self.txtDNS2.set_text(noneToBlankString(wireless.GetWirelessProperty(networkID,"dns2")))
		self.txtDNS3.set_text(noneToBlankString(wireless.GetWirelessProperty(networkID,"dns3")))

		self.resetStaticCheckboxes()
		encryptionTypes = misc.LoadEncryptionMethods()

		self.checkboxEncryption.set_active(False)
		self.comboEncryption.set_sensitive(False)

		if stringToBoolean(wireless.GetWirelessProperty(networkID,"automatic")) == True:
			self.checkboxAutoConnect.set_active(True)
		else:
			self.checkboxAutoConnect.set_active(False)
		#set it up right, with disabled stuff
		self.toggleEncryption()

		#add the names to the menu
		activeID = -1 #set the menu to this item when we are done
		for x in encryptionTypes:
			self.comboEncryption.append_text(encryptionTypes[x][0])
			if encryptionTypes[x][1] == wireless.GetWirelessProperty(networkID,"enctype"):
				activeID = x

		self.comboEncryption.set_active(activeID)
		if activeID != -1:
			self.checkboxEncryption.set_active(True)
			self.comboEncryption.set_sensitive(True)
			self.vboxEncryptionInformation.set_sensitive(True)
		else:
			self.comboEncryption.set_active(0)

		self.vboxAdvanced.pack_start(self.comboEncryption)
		self.vboxAdvanced.pack_start(self.vboxEncryptionInformation)
		self.changeEncryptionMethod()
		self.checkboxEncryption.connect("toggled",self.toggleEncryption)
		self.comboEncryption.connect("changed",self.changeEncryptionMethod)
		self.show_all()

	def updateAutoConnect(self,widget):
		wireless.SetWirelessProperty(self.networkID,"automatic",self.checkboxAutoConnect.get_active())
		config.SaveWirelessNetworkProperty(self.networkID,"automatic")

	def toggleEncryption(self,widget=None):
		active = self.checkboxEncryption.get_active()
		self.vboxEncryptionInformation.set_sensitive(active)
		self.comboEncryption.set_sensitive(active)

	def changeEncryptionMethod(self,widget=None):
		for z in self.vboxEncryptionInformation:
			z.destroy() #remove stuff in there already
		ID = self.comboEncryption.get_active()
		methods = misc.LoadEncryptionMethods()
		self.encryptionInfo = {}
		if ID == -1:
			#in case nothing is selected
			self.comboEncryption.set_active(0)
			ID == 0
		for x in methods[ID][2]:
			print x
			box = None
			if language.has_key(methods[ID][2][x][0]):
				box = LabelEntry(language[methods[ID][2][x][0].lower().replace(' ','_')])
			else:
				box = LabelEntry(methods[ID][2][x][0].replace('_',' '))
			box.set_auto_hidden(True)
			self.vboxEncryptionInformation.pack_start(box)
			#add the data to any array, so that the information
			#can be easily accessed by giving the name of the wanted
			#data
			self.encryptionInfo[methods[ID][2][x][1]] = box.entry

			box.entry.set_text(noneToBlankString(wireless.GetWirelessProperty(self.networkID,methods[ID][2][x][1])))
		self.vboxEncryptionInformation.show_all()

	def setSignalStrength(self,strength):
		self.lblStrength.set_label(str(strength) + "%")
		
	def setMACAddress(self,address):
		self.lblMAC.set_label(str(address))

	def setEncryption(self,on,type):
		if on and type:
			self.lblEncryption.set_label(language['secured'] + " " + str(type))
			self.set_use_markup(True)
			self.set_label(self.essid + ' <span color="grey">' + str(type) + '</span>')
		if on and not type:
			self.lblEncryption.set_label(language['secured'])
			self.set_label(self.essid + ' <span color="grey">Secured</span>')
		if not on:
			self.lblEncryption.set_label(language['unsecured'])

	def setChannel(self,channel):
		self.lblChannel.set_label(language['channel'] + ' ' + str(channel))
	
	def setMode(self,mode):
		self.lblMode.set_label(str(mode))

class appGui:

	def __init__(self):
		print "starting..."
		gladefile = "data/wicd.glade"
		self.windowname = "gtkbench"
		self.wTree = gtk.glade.XML(gladefile)

		dic = { "refresh_clicked" : self.refresh_networks, "quit_clicked" : self.exit, 'disconnect_clicked' : self.disconnect_wireless, "main_exit" : self.exit, "cancel_clicked" : self.cancel_connect, "connect_clicked" : self.connect_hidden, "preferences_clicked" : self.settings_dialog, "about_clicked" : self.about_dialog, 'create_adhoc_network_button_button' : self.create_adhoc_network}
		self.wTree.signal_autoconnect(dic)

		#set some strings in the GUI - they may be translated

		self.wTree.get_widget("label_instructions").set_label(language['select_a_network'])
		#I don't know how to translate a menu entry
		#more specifically, I don't know how to set a menu entry's text
		#self.wTree.get_widget("connect_button").modify_text(language['hidden_network'])
		self.wTree.get_widget("progressbar").set_text(language['connecting'])

		self.network_list = self.wTree.get_widget("network_list_vbox")
		self.status_area = self.wTree.get_widget("connecting_hbox")
		self.status_bar = self.wTree.get_widget("statusbar")
		self.refresh_networks(fresh=False)

		self.statusID = None

		gobject.timeout_add(300,self.update_statusbar)
		gobject.timeout_add(100,self.pulse_progress_bar)

	def create_adhoc_network(self,widget=None):
		#create a new adhoc network here.
		print 'create adhoc network'
		dialog = gtk.Dialog(title=language['create_adhoc_network'], flags = gtk.DIALOG_MODAL, buttons=(gtk.STOCK_OK,1,gtk.STOCK_CANCEL,2))
		dialog.set_has_separator(False)
		dialog.set_size_request(400,-1)
		self.useEncryptionCheckbox = gtk.CheckButton(language['use_encryption'])
		self.useEncryptionCheckbox.set_active(False)
		self.useEncryptionCheckbox.show()
		ipEntry = LabelEntry(language['ip'] + ':')
		essidEntry = LabelEntry(language['essid'] + ':')
		channelEntry = LabelEntry(language['channel'] + ':')
		self.keyEntry = LabelEntry(language['key'] + ':')
		self.keyEntry.set_sensitive(False)
		self.keyEntry.entry.set_visibility(False)

		self.useEncryptionCheckbox.connect("toggled",self.toggleEncryptionCheck)	
		channelEntry.entry.set_text('3')
		essidEntry.entry.set_text('My_Adhoc_Network')

		vboxA = gtk.VBox(False,0)
		vboxA.pack_start(self.useEncryptionCheckbox,fill=False,expand=False)
		vboxA.pack_start(self.keyEntry,fill=False,expand=False)
		vboxA.show()
		dialog.vbox.pack_start(essidEntry)
		dialog.vbox.pack_start(ipEntry)
		dialog.vbox.pack_start(channelEntry)
		dialog.vbox.pack_start(vboxA)
		dialog.vbox.set_spacing(5)
		response = dialog.run()
		if response == 1:
			wireless.CreateAdHocNetwork(essidEntry.entry.get_text(),channelEntry.entry.get_text(),ipEntry.entry.get_text(),"WEP",self.keyEntry.entry.get_text(),self.useEncryptionCheckbox.get_active())
		dialog.destroy()

	def toggleEncryptionCheck(self,widget=None):
		self.keyEntry.set_sensitive(self.useEncryptionCheckbox.get_active())

	def disconnect_wireless(self,widget=None):
		wireless.DisconnectWireless()		

	def about_dialog(self,widget,event=None):
		dialog = gtk.AboutDialog()
		dialog.set_name("Wicd")
		dialog.set_version(daemon.Hello())
		dialog.set_authors([ "Adam Blackburn" ])
		dialog.set_website("http://wicd.sourceforge.net")
		dialog.run()
		dialog.destroy()
		
	def settings_dialog(self,widget,event=None):
		dialog = gtk.Dialog(title=language['preferences'], flags=gtk.DIALOG_MODAL, buttons=(gtk.STOCK_OK,1,gtk.STOCK_CANCEL,2))
		dialog.set_has_separator(False)
		dialog.set_size_request(375,-1)
		wiredcheckbox = gtk.CheckButton(language['wired_always_on'])
		wiredcheckbox.set_active(wired.GetAlwaysShowWiredInterface())
		reconnectcheckbox = gtk.CheckButton(language['auto_reconnect'])
		reconnectcheckbox.set_active(wireless.GetAutoReconnect())
		wpadriverlabel = SmallLabel(language['wpa_supplicant_driver'] + ':')
		wpadrivercombo = gtk.combo_box_new_text()
		wpadrivercombo.set_size_request(50,-1)
		wpadrivers = [ "hostap","hermes","madwifi","atmel","wext","ndiswrapper","broadcom","ipw" ]
		i = 0
		found = False
		for x in wpadrivers:
			if x == daemon.GetWPADriver() and found == False:
				found = True
			else:
				if found == False:
					i+=1
			wpadrivercombo.append_text(x)
		#set active here.
		#if we set active an item to active, then add more items
		#it loses the activeness
		wpadrivercombo.set_active(i)
		#select wext as the default driver, because
		#it works for most cards
		wpabox = gtk.HBox(False,1)
		wpabox.pack_start(wpadriverlabel)
		wpabox.pack_start(wpadrivercombo)

		entryWirelessInterface = LabelEntry(language['wireless_interface'] + ':')
		entryWiredInterface = LabelEntry(language['wired_interface'] + ':')

		entryWirelessInterface.entry.set_text(daemon.GetWirelessInterface())
		entryWiredInterface.entry.set_text(daemon.GetWiredInterface())

		dialog.vbox.pack_start(wpabox)
		dialog.vbox.pack_start(entryWirelessInterface)
		dialog.vbox.pack_start(entryWiredInterface)
		dialog.vbox.pack_start(wiredcheckbox)
		dialog.vbox.pack_start(reconnectcheckbox)
		dialog.vbox.set_spacing(5)
		dialog.show_all()
		response = dialog.run()
		if response == 1:
			daemon.SetWirelessInterface(entryWirelessInterface.entry.get_text())
			daemon.SetWiredInterface(entryWiredInterface.entry.get_text())
			print "setting: " + wpadrivers[wpadrivercombo.get_active()]
			daemon.SetWPADriver(wpadrivers[wpadrivercombo.get_active()])
			wired.SetAlwaysShowWiredInterface(wiredcheckbox.get_active())
			wireless.SetAutoReconnect(reconnectcheckbox.get_active())
			print wiredcheckbox.get_active()
			print reconnectcheckbox.get_active()
			dialog.destroy()
		else:
			dialog.destroy()

	def connect_hidden(self,widget):
		#should display a dialog asking
		#for the ssid of a hidden network
		#and displaying connect/cancel buttons
		dialog = gtk.Dialog(title=language['hidden_network'], flags=gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CONNECT,1,gtk.STOCK_CANCEL,2))
		dialog.set_has_separator(False)
		dialog.lbl = gtk.Label(language['hidden_network_essid'])
		dialog.textbox = gtk.Entry()
		dialog.vbox.pack_start(dialog.lbl)
		dialog.vbox.pack_start(dialog.textbox)
		dialog.show_all()
		button = dialog.run()
		if button == 1:
			answer = dialog.textbox.get_text()
			dialog.destroy()
			self.refresh_networks(None,True,answer)
		else:
			dialog.destroy()

	def cancel_connect(self,widget):
		#should cancel a connection if there
		#is one in progress
		cancelButton = self.wTree.get_widget("cancel_button")
		cancelButton.set_sensitive(False)
		wireless.CancelConnect()
		wireless.SetForcedDisconnect(True) #Prevents automatic reconnecting if that option is enabled

	def pulse_progress_bar(self):
		self.wTree.get_widget("progressbar").pulse()
		return True

	def update_statusbar(self):
		#should update the status bar
		#every couple hundred milliseconds
		config.DisableLogging() #stop log file spam
		wireless_ip = wireless.GetWirelessIP() #do this so that it doesn't lock up.  don't know how or why this works
					 #but it does so we leave it alone :)
		wiredConnecting = wired.CheckIfWiredConnecting() 
		wirelessConnecting = wireless.CheckIfWirelessConnecting() 
		if wirelessConnecting == True or wiredConnecting == True:
			self.network_list.set_sensitive(False)
			self.status_area.show_all()
			if self.statusID:
				self.status_bar.remove(1,self.statusID)
			if wirelessConnecting:
				self.statusID = self.status_bar.push(1,language[str(wireless.CheckWirelessConnectingMessage())])
			if wiredConnecting:
				self.statusID = self.status_bar.push(1,language[str(wired.CheckWiredConnectingMessage())])
		else:
			self.network_list.set_sensitive(True)
			self.status_area.hide_all()
			if self.statusID:
				self.status_bar.remove(1,self.statusID)
			#use the chain approach to save calls to external programs
			#external programs are quite CPU intensive	
			if wireless_ip:
				network = wireless.GetCurrentNetwork()
				if network:
					strength = wireless.GetCurrentSignalStrength()
					if strength != None: #do this because if strength is 0, if strength: doesn't work
						network = str(network)
						strength = str(strength)
						ip = str(wireless_ip)
						self.statusID=self.status_bar.push(1,language['connected_to_wireless'].replace('$A',network).replace('$B',strength).replace('$C',wireless_ip))
						return True
			wired_ip = wired.GetWiredIP()
			if wired_ip:
				if wired.GetAlwaysShowWiredInterface() or wired.CheckPluggedIn():
					self.statusID = self.status_bar.push(1,language['connected_to_wired'].replace('$A',wired_ip))
				return True
			self.statusID = self.status_bar.push(1,language['not_connected'])
		config.EnableLogging() #reenable logging
		return True

	def refresh_networks(self,widget=None,fresh=True,hidden=None):
		print "refreshing..."
		
		printLine = False #so that we don't print the first line...
		#remove stuff already in there.
		for z in self.network_list:
			z.destroy()

		if wired.CheckPluggedIn() or wired.GetAlwaysShowWiredInterface():
			printLine = True #so that a horizontal line is printed if there are wireless networks
			wiredNetwork = PrettyWiredNetworkEntry()
			self.network_list.pack_start(wiredNetwork,fill=False,expand=False)
			wiredNetwork.connectButton.connect("button-press-event",self.connect,"wired",0,wiredNetwork)
		#scan!
		if fresh:
			#even if it is None, it can still be passed
			wireless.SetHiddenNetworkESSID(noneToString(hidden))
			wireless.Scan()

		print wireless.GetNumberOfNetworks()

		instructLabel = self.wTree.get_widget("label_instructions")
		if wireless.GetNumberOfNetworks() > 0:
			instructLabel.show()
			for x in range(0,wireless.GetNumberOfNetworks()):
				if printLine:
					sep = gtk.HSeparator()
					self.network_list.pack_start(sep,padding=10,expand=False,fill=False)
					sep.show()
				else:
					printLine = True
				tempNetwork = PrettyWirelessNetworkEntry(x)
				tempNetwork.show_all()
				self.network_list.pack_start(tempNetwork,expand=False,fill=False)
				tempNetwork.connectButton.connect("button-press-event",self.connect,"wireless",x,tempNetwork)
		else:
			instructLabel.hide()
			label = gtk.Label(language['no_wireless_networks_found'])
			self.network_list.pack_start(label)
			label.show()
		
	def connect(self,widget,event,type,networkid,networkentry):
		cancelButton = self.wTree.get_widget("cancel_button")
		cancelButton.set_sensitive(True)
		if type == "wireless":
			wireless.SetWirelessProperty(networkid,"automatic",noneToString(networkentry.expander.checkboxAutoConnect.get_active())) 
			if networkentry.expander.checkboxStaticIP.get_active() == True:
				wireless.SetWirelessProperty(networkid,"ip",noneToString(networkentry.expander.txtIP.get_text()))
				wireless.SetWirelessProperty(networkid,"netmask",noneToString(networkentry.expander.txtNetmask.get_text()))
				wireless.SetWirelessProperty(networkid,"gateway",noneToString(networkentry.expander.txtGateway.get_text()))
			else:
				#blank the values
				wireless.SetWirelessProperty(networkid,"ip",'')
				wireless.SetWirelessProperty(networkid,"netmask",'')
				wireless.SetWirelessProperty(networkid,"gateway",'')

			if networkentry.expander.checkboxStaticDNS.get_active() == True:
				wireless.SetWirelessProperty(networkid,"dns1",noneToString(networkentry.expander.txtDNS1.get_text()))
				wireless.SetWirelessProperty(networkid,"dns2",noneToString(networkentry.expander.txtDNS2.get_text()))
				wireless.SetWirelessProperty(networkid,"dns3",noneToString(networkentry.expander.txtDNS3.get_text()))
			else:
				#blank the values
				wireless.SetWirelessProperty(networkid,"dns1",'')
				wireless.SetWirelessProperty(networkid,"dns2",'')
				wireless.SetWirelessProperty(networkid,"dns3",'')

			
			if networkentry.expander.checkboxEncryption.get_active() == True:
				print "setting encryption info..."
				encryptionInfo = networkentry.expander.encryptionInfo
				#set the encryption type. without the encryption type, nothing is gonna happen
				wireless.SetWirelessProperty(networkid,"enctype",misc.LoadEncryptionMethods()[networkentry.expander.comboEncryption.get_active()][1])
				for x in encryptionInfo:
					wireless.SetWirelessProperty(networkid,x,noneToString(encryptionInfo[x].get_text()))
			else:
				print "no encryption specified..."
				wireless.SetWirelessProperty(networkid,"enctype",noneToString(None))

			print "connecting to wireless network..."
			config.SaveWirelessNetworkProfile(networkid)
			wireless.ConnectWireless(networkid)

		if type == "wired":
			print "wired"
			if networkentry.expander.checkboxStaticIP.get_active() == True:
				wired.SetWiredProperty("ip",noneToString(networkentry.expander.txtIP.get_text()))
				wired.SetWiredProperty("netmask",noneToString(networkentry.expander.txtNetmask.get_text()))
				wired.SetWiredProperty("gateway",noneToString(networkentry.expander.txtGateway.get_text()))
			else:
				wired.SetWiredProperty("ip",'')
				wired.SetWiredProperty("netmask",'')
				wired.SetWiredProperty("gateway",'')

			if networkentry.expander.checkboxStaticDNS.get_active() == True:
				wired.SetWiredProperty("dns1",noneToString(networkentry.expander.txtDNS1.get_text()))
				wired.SetWiredProperty("dns2",noneToString(networkentry.expander.txtDNS2.get_text()))
				wired.SetWiredProperty("dns3",noneToString(networkentry.expander.txtDNS3.get_text()))
			else:
				wired.SetWiredProperty("dns1",'')
				wired.SetWiredProperty("dns2",'')
				wired.SetWiredProperty("dns3",'')
			
			config.SaveWiredNetworkProfile(networkentry.expander.comboProfileNames.get_active_text())
			wired.ConnectWired()

	def exit(self,widget,event=None):
		sys.exit(0)

#start the app
app = appGui()
gtk.main()
