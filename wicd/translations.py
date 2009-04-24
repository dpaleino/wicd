#!/usr/bin/env python
# -* coding: utf-8 -*-

#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
#   Copyright (C) 2009        Andrew Psaltis
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License Version 2 as
#   published by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import locale
import os
import wpath
import gettext


def get_gettext():
    """ Set up gettext for translations. """
    # Borrowed from an excellent post on how to do this at
    # http://www.learningpython.com/2006/12/03/translating-your-pythonpygtk-application/
    local_path = wpath.translations
    langs = []
    osLanguage = os.environ.get('LANGUAGE', None)
    if osLanguage:
        langs += osLanguage.split(":")
    osLanguage = None
    osLanguage = os.environ.get('LC_MESSAGES', None)
    if osLanguage:
        langs += osLanguage.split(":")
    try:
        # This avoids a bug: locale.getdefaultlocale() prefers
        # LC_CTYPE over LANG/LANGUAGE
        lc, encoding = locale.getdefaultlocale(envvars=('LC_MESSAGES', 
                                                        'LC_ALL', 'LANG', 
                                                        'LANGUAGE'))
    except ValueError, e:
        print str(e)
        print "Default locale unavailable, falling back to en_US"
    if (lc):
        langs += [lc]
    langs += ["en_US"]
    lang = gettext.translation('wicd', local_path, languages=langs, 
                               fallback=True)
    _ = lang.gettext
    return _

_ = get_gettext()
language = {}
language['connect'] = _('Connect')
language['ip'] = _('IP')
language['netmask'] = _('Netmask')
language['gateway'] = _('Gateway')
language['dns'] = _('DNS')
language['use_static_ip'] = _('Use Static IPs')
language['use_static_dns'] = _('Use Static DNS')
language['use_encryption'] = _('Use Encryption')
language['advanced_settings'] = _('Advanced Settings')
language['properties'] = _('Properties')
language['wired_network'] = _('Wired Network')
language['wired_network_instructions'] = _('To connect to a wired network,'
' you must create a network profile. To create a network profile, type a'
' name that describes this network, and press Add.')
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
language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
language['tray_connected_to_wireless'] = _('Wireless Network\n$A at $B\nSpeed: $C\nIP $D')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['tray_connected_to_wired'] = _('Wired Network\nIP: $A')
language['not_connected'] = _('Not connected')
language['conn_info_wired'] = _('Wired\nIP:\t\t$A\nRX:\t\t$B KB/s\nTX:\t\t$C KB/s\n\n\n')
language['conn_info_wireless'] = _('Wireless\nSSID:\t$A\nSpeed\t$B\nIP:\t\t$C\nStrength:\t$D\nRX:\t\t$E KB/s\nTX:\t\t$F KB/s')
language['no_wireless_networks_found'] = _('No wireless networks found.')
language['killswitch_enabled'] = _('Wireless Kill Switch Enabled')
language['key'] = _('Key')
language['username'] = _('Username')
language['password'] = _('Password')
language['anonymous_identity'] = _('Anonymous Identity')
language['identity'] = _('Identity')
language['authentication'] = _('Authentication')
language['path_to_pac_file'] = _('Path to PAC File')
language['select_a_network'] = _('Choose from the networks below:')
#language['connecting...'] = _('Connecting...')
language['wired_always_on'] = _('Always show wired interface')
language['auto_reconnect'] = _('Automatically reconnect on connection loss')
language['create_adhoc_network'] = _('Create an Ad-Hoc Network')
language['essid'] = _('ESSID')
language['use_wep_encryption'] = _('Use Encryption (WEP only)')
language['before_script'] = _('Run script before connect')
language['after_script'] = _('Run script after connect')
language['disconnect_script'] = _('Run disconnect script')
language['script_settings'] = _('Scripts')
language['use_ics'] = _('Activate Internet Connection Sharing')
language['madwifi_for_adhoc'] = _('Check if using madwifi/atheros drivers')
language['default_wired'] = _('Use as default profile (overwrites any previous default)')
language['use_debug_mode'] = _('Enable debug mode')
language['use_global_dns'] = _('Use global DNS servers')
language['use_default_profile'] = _('Use default profile on wired autoconnect')
language['show_wired_list'] = _('Prompt for profile on wired autoconnect')
language['use_last_used_profile'] = _('Use last used profile on wired autoconnect')
language['choose_wired_profile'] = _('Select or create a wired profile to connect with')
language['wired_network_found'] = _('Wired connection detected')
language['stop_showing_chooser'] = _('Stop Showing Autoconnect pop-up temporarily')
language['display_type_dialog'] = _('Use dBm to measure signal strength')
language['scripts'] = _('Scripts')
language['invalid_address'] = _('Invalid address in $A entry.')
language['global_settings'] = _('Use these settings for all networks sharing this essid')
language['encrypt_info_missing'] = _('Required encryption information is missing.')
language['enable_encryption'] = _('This network requires encryption to be enabled.')
language['wicd_auto_config'] = _('Automatic (recommended)')
language["gen_settings"] = _('General Settings')
language["ext_programs"] = _('External Programs')
language["dhcp_client"] = _('DHCP Client')
language["wired_detect"] = _('Wired Link Detection')
language["route_flush"] = _('Route Table Flushing')
language["backend"] = _('Backend')
language["backend_alert"] = _('Changes to your backend won\'t occur until the daemon is restarted.')
language['dns_domain'] = _('DNS domain')
language['search_domain'] = _('Search domain')
language['global_dns_not_enabled'] = _('Global DNS has not been enabled in general preferences.')
language['scripts_need_pass'] = _('You must enter your password to configure scripts')
language['no_sudo_prog'] = _('Could not find a graphical sudo program.  The script editor could not be launched.' +
                             '  You\'ll have to edit scripts directly your configuration file.')

language['interface_down'] = _('Putting interface down...')
language['resetting_ip_address'] = _('Resetting IP address...')
language['interface_up'] = _('Putting interface up...')
language['setting_encryption_info'] = _('Setting encryption info')
language['removing_old_connection'] = _('Removing old connection...')
language['generating_psk'] = _('Generating PSK...')
language['generating_wpa_config'] = _('Generating WPA configuration file...')
language['flushing_routing_table'] = _('Flushing the routing table...')
language['configuring_interface'] = _('Configuring wireless interface...')
language['validating_authentication'] = _('Validating authentication...')
language['setting_broadcast_address'] = _('Setting broadcast address...')
language['setting_static_dns'] = _('Setting static DNS servers...')
language['setting_static_ip'] = _('Setting static IP addresses...')
language['running_dhcp'] = _('Obtaining IP address...')
language['dhcp_failed'] = _('Connection Failed: Unable to Get IP Address')
language['no_dhcp_offers'] = _('Connection Failed: No DHCP offers received.')
language['aborted'] = _('Connection Cancelled')
language['bad_pass'] = _('Connection Failed: Could not authenticate (bad password?)')
language['verifying_association'] = _("Verifying access point association...")
language['association_failed'] = _("Connection Failed: Could not contact the wireless access point.")
language['done'] = _('Done connecting...')
language['scanning'] = _('Scanning')
language['scanning_stand_by'] = _('Scanning networks... stand by...')
language['cannot_start_daemon'] = _('Unable to connect to wicd daemon DBus interface.  " + \
                                "This typically means there was a problem starting the daemon.  " + \
                                "Check the wicd log for more info')
language['lost_dbus'] = _('The wicd daemon has shut down, the UI will not function properly until it is restarted.')
language['access_denied'] = _("Unable to contact the wicd dameon due to an access denied error from DBus.  Please check your DBus configuration.")
language['configuring_wireless'] = _('Configuring preferences for wireless network "$A" ($B)')
language['configuring_wired'] = _('Configuring preferences for wired profile "$A"')
language['scan'] = _('Scan')
language['always_switch_to_wired'] = _('Always switch to wired connection when available')
language['wired_autoconnect_settings'] = _('Wired Autoconnect Settings')
language['always_use_wext'] = _('You should almost always use wext as the WPA supplicant driver')
language['debugging'] = _('Debugging')
language['wpa_supplicant'] = _('WPA Supplicant')
language['automatic_reconnection'] = _('Automatic Reconnection')
language['global_dns_servers'] = _('Global DNS servers')
language['network_interfaces'] = _('Network Interfaces')
language['connecting_to_daemon'] = _('Connecting to daemon...')
language['cannot_connect_to_daemon'] = _('Can\'t connect to the daemon, trying to start it automatically...')
language['could_not_connect'] = _('Could not connect to wicd\'s D-Bus interface. Check the wicd log for error messages.')
language["exception"] = _('EXCEPTION! Please report this to the maintainer and file a bug report with the backtrace below:')
language["brought_to_you"] = _('Brought to you by:')
language["add_new_profile"] = _('Add a new profile')
language["add_new_wired_profile"] = _('Add a new wired profile')
language["no_delete_last_profile"] = _('wicd-curses does not support deleting the last wired profile.  Try renaming it (\'F2\')')
language["rename_wired_profile"] = _('Rename wired profile')
language["select_hidden_essid"] = _('Select Hidden Network ESSID')
language["esc_to_cancel"] = _('Press ESC to cancel')
language["press_to_quit"] = _('Press F8 or Q to quit.')

language['terminated'] = _('Terminated by user')
language['wicd_curses'] = _('Wicd Curses Interface')
language['dbus_fail'] = _('DBus failure! This is most likely caused by the wicd daemon stopping while wicd-curses is running. Please restart the daemon, and then restart wicd-curses.')

# These are in the tray list, but not in the non-tray list
language['connecting'] = _('Connecting')
language['daemon_unavailable'] = _('The wicd daemon is unavailable, so your request cannot be completed')
language['no_daemon_tooltip'] = _('Wicd daemon unreachable')

# Translations added on Wed Mar  4 03:36:24 UTC 2009
language['make_wired_profile'] = _('To connect to a wired network, you must create a network profile.  To create a network profile, type a name that describes this network, and press Add.')
language['access_cards'] = _('Wicd needs to access your computer\'s network cards.')
#language['CHANGE_ME'] = _('Create Ad-Hoc network')
#language['CHANGE_ME'] = _('Wired Autoconnect Setting:')
language['bad_pass'] = _('Connection Failed: Bad password')
language['cannot_edit_scripts_1'] = _('To avoid various complications, wicd-curses does not support directly editing the scripts directly.  However, you can edit them manually.  First, (as root)", open the "$A" config file, and look for the section labeled by the $B in question.  In this case, this is:')
language['cannot_edit_scripts_2'] = _('Once there, you can adjust (or add) the "beforescript", "afterscript", and "disconnectscript" variables as needed, to change the preconnect, postconnect, and disconnect scripts respectively.  Note that you will be specifying the full path to the scripts - not the actual script contents.  You will need to add/edit the script contents separately.  Refer to the wicd manual page for more information.')
language['cannot_edit_scripts_3'] = _('You can also configure the wireless networks by looking for the "[<ESSID>]" field in the config file.')
language['wired_networks'] = _('Wired Networks')
language['wireless_networks'] = _('Wireless Networks')
language['about'] = _('About Wicd')
language['more_help'] = _('For more detailed help, consult the wicd-curses(8) man page.')
language['case_sensitive'] = _('All controls are case sensitive')
language['help_help'] = _('Display this help dialog')
language['connect_help'] = _('Connect to selected network')
language['disconn_help'] = _('Disconnect from all networks')
language['about_help'] = _('Stop a network connection in progress')
language['refresh_help'] = _('Refresh network list')
language['prefs_help'] = _('Preferences dialog')
language['scan_help'] = _('Scan for hidden networks')
language['scripts_help'] = _('Select scripts')
language['adhoc_help'] = _('Set up Ad-hoc network')
language['config_help'] = _('Configure Selected Network')
#language[''] = _('Press H or ? for help') # Defunct in curses-uimod
language['raw_screen_arg'] = _('use urwid\'s raw screen controller')
language['ok'] = _('OK')
language['cancel'] = _('Cancel')


