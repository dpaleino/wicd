/*
 *  Copyright (c) 2008 Kel Modderman <kel@otaku42.de>
 *  License: LGPL v2.1
 *
 *  This is a fork of pyiw: http://downloads.emperorlinux.com/contrib/pyiw/
 *  by jeremy@emperorlinux.com
 *
 *  This module was inspired by (and uses) the iw library that comes with the Linux Wireless Tools
 *  package. Portions of this module are moderately modified snippets of iwlist.c
 */

#include <Python.h>
#include <structmember.h>
#include <iwlib.h>

#define IWSCAN_VERSION_MAJOR  0
#define IWSCAN_VERSION_MINOR  7
#define IWSCAN_VERSION_MICRO  0

/* ------------------------------------------------------------------------------- from iwlist.c */

#define IWSCAN_ARRAY_LEN(x) (sizeof(x) / sizeof((x)[0]))

/* Values for the IW_IE_CIPHER_* in GENIE */
static const char* iwscan_ie_cypher_name[] = {
	"none",
	"WEP-40",
	"TKIP",
	"WRAP",
	"CCMP",
	"WEP-104",
};
#define IWSCAN_IE_CYPHER_NUM IWSCAN_ARRAY_LEN(iwscan_ie_cypher_name)

/* Values for the IW_IE_KEY_MGMT_* in GENIE */
static const char* iwscan_ie_key_mgmt_name[] = {
	"none",
	"802.1x",
	"PSK",
};
#define IWSCAN_IE_KEY_MGMT_NUM IWSCAN_ARRAY_LEN(iwscan_ie_key_mgmt_name)

/* --------------------------------------------------------------------------- WirelessInterface */
typedef struct {
	PyObject_HEAD
	wireless_info info;
	char*         ifname;
	int sock;
} WirelessInterface;

typedef enum {
	IWSCAN_KE_BSSID,
	IWSCAN_KE_FREQUENCY,
	IWSCAN_KE_CHANNEL,
	IWSCAN_KE_MODE,
	IWSCAN_KE_PROTOCOL,
	IWSCAN_KE_ESSID,
	IWSCAN_KE_ENC,
	IWSCAN_KE_BITRATE,
	IWSCAN_KE_QUAL,
	IWSCAN_KE_STATS,
	IWSCAN_KE_IE
} WirelessInterfaceKeyEnum;

typedef struct {
	WirelessInterfaceKeyEnum keys[2];
	PyObject*                objs[2];
	int num;
} WirelessInterfaceScanData;

static char* WirelessInterfaceKeys[] = {
	"bssid",
	"frequency",
	"channel",
	"mode",
	"protocol",
	"essid",
	"enc",
	"bitrate",
	"qual",
	"stats",
	"ie",
};
#define IWSCAN_INTERFACE_KEYS IWSCAN_ARRAY_LEN(WirelessInterfaceKeys)

/* ------------------------------------------------------------------------ Function Definitions */
typedef struct iw_event iwevent;
typedef struct iwreq iwreq;
typedef struct ifreq ifreq;
typedef struct timeval timeval;
typedef WirelessInterface wiface;
typedef WirelessInterfaceScanData wifacesd;

static PyObject* iwscan_version(PyObject*, PyObject*);
static PyObject* iwscan_iw_version(PyObject*, PyObject*);
static PyObject* iwscan_we_version(PyObject*, PyObject*);
static PyObject* iwscan_enum_devices(PyObject*, PyObject*);

static int       WirelessInterface_init(wiface*, PyObject*, PyObject*);
static void      WirelessInterface_dealloc(wiface*);
static void      WirelessInterface_refresh(wiface*);
static int       WirelessInterface_len(PyObject*);
static PyObject* WirelessInterface_seqitem(PyObject*, int);

static PyObject* WirelessInterface_Scan(wiface*);
static PyObject* WirelessInterface_ScanCypher(unsigned int);
static PyObject* WirelessInterface_ScanKeyMgt(unsigned int);
static PyObject* WirelessInterface_ScanIe(unsigned char*, int);
static int       WirelessInterface_ScanItem(wifacesd*, iwevent*, iwrange*, int);

static PyObject* IwScanError;

/* --------------------------------------------------------------------------- IWSCAN_DOC_STRING */
static char* IWSCAN_DOC_STRING =
	"IWSCAN defines a single class, WirelessInterface, that must be instantiated\n"
	"with the name of the real wireless interface you wish to operate on. If\n"
	"the interface you specify doesn't exist, or if it doesn't support wireless\n"
	"extensions, object creation will fail and iwscan.error will be raised. As an\n"
	"important side note: IWSCAN requires at least Wireless Extensions 18.\n\n"
	"import iwscan\n"
	"import sys\n\n"
	"try:\n"
	"	for w in iwscan.enum_devices():\n"
	"		print 'Scanning with %s:' % w\n"
	"		wi = iwscan.WirelessInterface(w)\n"
	"		wi.Scan()\n"
	"except iwscan.error, error:\n"
	"	print error\n"
	"	sys.exit(1)\n\n"
;

/* ---------------------------------------------------------------------- WirelessInterface_init */
static int WirelessInterface_init(wiface* self, PyObject* args, PyObject* kargs)
{
	const char*  ifname;
	const size_t ifnamesize;

	memset(&(self->info), 0, sizeof(wireless_info));

	self->ifname = NULL;
	self->sock   = 0;

	if (PyArg_ParseTuple(args, "s#", &ifname, &ifnamesize)) {
		self->sock = iw_sockets_open();

		if (self->sock != -1) {
			ifreq frq;

			self->ifname = malloc(ifnamesize + 1);

			strncpy(self->ifname, ifname, ifnamesize + 1);
			strncpy(frq.ifr_name, self->ifname, IFNAMSIZ);

			if (!ioctl(self->sock, SIOCGIFFLAGS, &frq)) {
				frq.ifr_flags |= IFF_UP | IFF_RUNNING;

				ioctl(self->sock, SIOCSIFFLAGS, &frq);

				WirelessInterface_refresh(self);

				return 0;
			}
			else
				PyErr_SetString(IwScanError, "Failed to find device");
		}
		else
			PyErr_SetString(IwScanError, "Failed to connect to libiw");
	}

	return -1;
}

/* ------------------------------------------------------------------- WirelessInterface_dealloc */
static void WirelessInterface_dealloc(wiface* self)
{
	if (self->ifname)
		free(self->ifname);

	iw_sockets_close(self->sock);
	self->ob_type->tp_free((PyObject*)(self));
}

/* ------------------------------------------------------------------- WirelessInterface_refresh */
static void WirelessInterface_refresh(wiface* self)
{
	iwreq wrq;

	iw_get_basic_config(self->sock, self->ifname, &(self->info.b));
	iw_get_range_info(self->sock, self->ifname, &(self->info.range));

	iw_get_ext(self->sock, self->ifname, SIOCGIWRATE, &wrq);
	memcpy(&(self->info.bitrate), &wrq.u.bitrate, sizeof(iwparam));

	iw_get_ext(self->sock, self->ifname, SIOCGIWAP, &wrq);
	memcpy(&(self->info.ap_addr), &wrq.u.ap_addr, sizeof(sockaddr));

	iw_get_stats(self->sock, self->ifname, &(self->info.stats),
		     &(self->info.range), self->info.has_range);
}

/* ----------------------------------------------------------------------- WirelessInterface_len */
static int WirelessInterface_len(PyObject* self)
{
	return IWSCAN_INTERFACE_KEYS;
}

/* ------------------------------------------------------------------- WirelessInterface_seqitem */
static PyObject* WirelessInterface_seqitem(PyObject* self, int index)
{
	if (index >= 0 && index < IWSCAN_INTERFACE_KEYS)
		return Py_BuildValue("s", WirelessInterfaceKeys[index]);

	return NULL;
}

/* ---------------------------------------------------------------------- WirelessInterface_Scan */
static PyObject* WirelessInterface_Scan(wiface* self)
{
	iwreq wrq;
	unsigned char* buffer = NULL;
	int buflen            = IW_SCAN_MAX_DATA;
	iwrange range;
	int has_range;
	timeval tv;
	int timeout           = 15000000;
	PyObject* scan_list   = NULL;

	has_range = (iw_get_range_info(self->sock, self->ifname, &range) >= 0);

	tv.tv_sec          = 0;
	tv.tv_usec         = 250000;
	wrq.u.data.pointer = NULL;
	wrq.u.data.flags   = 0;
	wrq.u.data.length  = 0;

	if (iw_set_ext(self->sock, self->ifname, SIOCSIWSCAN, &wrq) < 0) {
		if (errno != EPERM) {
			PyErr_SetString(IwScanError, "Interface doesn't support scanning");
			return NULL;
		}

		tv.tv_usec = 0;
	}

	timeout -= tv.tv_usec;

	while (1) {
		fd_set rfds;
		int last_fd;
		int ret;

		FD_ZERO(&rfds);
		last_fd = -1;

		ret = select(last_fd + 1, &rfds, NULL, NULL, &tv);

		if (ret < 0) {
			if (errno == EAGAIN || errno == EINTR)
				continue;
			else {
				PyErr_SetString(IwScanError, "Unknown scanning error");
				return NULL;
			}
		}

		if (!ret) {
			unsigned char* newbuf;

 realloc:
			newbuf = realloc(buffer, buflen);

			if (!newbuf) {
				if (buffer)
					free(buffer);

				PyErr_SetString(IwScanError, "Memory allocation failure in scan");
				return NULL;
			}

			buffer = newbuf;

			wrq.u.data.pointer = buffer;
			wrq.u.data.flags   = 0;
			wrq.u.data.length  = buflen;

			if (iw_get_ext(self->sock, self->ifname, SIOCGIWSCAN, &wrq) < 0) {
				if ((errno == E2BIG)) {
					if (wrq.u.data.length > buflen)
						buflen = wrq.u.data.length;
					else
						buflen *= 2;

					goto realloc;
				}

				if (errno == EAGAIN) {
					tv.tv_sec   = 0;
					tv.tv_usec  = 100000;
					timeout    -= tv.tv_usec;

					if (timeout > 0)
						continue;
				}

				free(buffer);

				PyErr_SetString(IwScanError, "Unable to read scan data");
				return NULL;
			}
			else
				break;
		}
	}

	if (wrq.u.data.length) {
		iwevent iwe;
		stream_descr stream;
		int ret;
		PyObject* scan_dict = NULL;

		scan_list = PyList_New(0);

		iw_init_event_stream(&stream, (char*)(buffer), wrq.u.data.length);

		do {
			ret = iw_extract_event_stream(&stream, &iwe, range.we_version_compiled);

			if (ret > 0) {
				wifacesd sd;
				int sr = WirelessInterface_ScanItem(&sd, &iwe, &range, has_range);

				if (sr) {
					int i;

					if (scan_dict) {
						PyList_Append(scan_list, scan_dict);
						Py_DECREF(scan_dict);
					}

					scan_dict = PyDict_New();

					for (i = 0; i < IWSCAN_INTERFACE_KEYS; i++) {
						PyMapping_SetItemString(scan_dict,
									WirelessInterfaceKeys[i],
									Py_BuildValue(""));
					}
				}

				if (sd.num) {
					int i;

					for (i = 0; i < sd.num; i++) {
						PyMapping_SetItemString(scan_dict,
									WirelessInterfaceKeys[sd.keys[i]],
									sd.objs[i]);

						Py_DECREF(sd.objs[i]);
					}
				}
			}
		} while (ret > 0);

		PyList_Append(scan_list, scan_dict);
		Py_XDECREF(scan_dict);
	}
	else
		return Py_BuildValue("[]");

	free(buffer);

	return scan_list;
}

/* ---------------------------------------------------------------- WirelessInterface_ScanCypher */
static PyObject* WirelessInterface_ScanCypher(unsigned int value)
{
	if (value >= IWSCAN_IE_CYPHER_NUM)
		return Py_BuildValue("");

	return Py_BuildValue("s", iwscan_ie_cypher_name[value]);
}

/* ---------------------------------------------------------------- WirelessInterface_ScanKeyMgt */
static PyObject* WirelessInterface_ScanKeyMgt(unsigned int value)
{
	if (value >= IWSCAN_IE_KEY_MGMT_NUM)
		return Py_BuildValue("");

	return Py_BuildValue("s", iwscan_ie_key_mgmt_name[value]);
}

/* -------------------------------------------------------------------- WirelessInterface_ScanIe */
static PyObject* WirelessInterface_ScanIe(unsigned char* iebuf, int buflen)
{
	int ielen  = iebuf[1] + 2;
	int offset = 2;
	unsigned char  wpa1_oui[3] = { 0x00, 0x50, 0xf2 };
	unsigned char  wpa2_oui[3] = { 0x00, 0x0f, 0xac };
	unsigned char* wpa_oui;
	int i;
	uint16_t ver = 0;
	uint16_t cnt = 0;
	PyObject*      auth_list  = PyList_New(0);
	PyObject*      pairwise_list  = PyList_New(0);
	PyObject*      wpa_dict  = PyDict_New();

	PyMapping_SetItemString(wpa_dict, "auth", auth_list);
	PyMapping_SetItemString(wpa_dict, "group", Py_BuildValue(""));
	PyMapping_SetItemString(wpa_dict, "pairwise", pairwise_list);
	PyMapping_SetItemString(wpa_dict, "type", Py_BuildValue(""));
	PyMapping_SetItemString(wpa_dict, "version", Py_BuildValue(""));
	if (ielen > buflen) {
		ielen = buflen;
	}

	switch (iebuf[0]) {
	case 0x30:
		if (ielen < 4) {
			return wpa_dict;
		}

		wpa_oui = wpa2_oui;
		break;
	case 0xdd:
		wpa_oui = wpa1_oui;

		if ((ielen < 8)
		    || (memcmp(&iebuf[offset], wpa_oui, 3) != 0)
		    || (iebuf[offset + 3] != 0x01))
			return wpa_dict;

		offset += 4;
		break;
	default:
		return wpa_dict;
	}

	ver = iebuf[offset] | (iebuf[offset + 1] << 8);
	offset += 2;

	PyMapping_SetItemString(wpa_dict, "version", Py_BuildValue("i", ver));
	if (iebuf[0] == 0xdd)
		PyMapping_SetItemString(wpa_dict, "type", Py_BuildValue("s", "WPA"));
	if (iebuf[0] == 0x30)
		PyMapping_SetItemString(wpa_dict, "type", Py_BuildValue("s", "IEEE 802.11i/WPA2"));

	if (ielen < (offset + 4)) {
		PyMapping_SetItemString(wpa_dict, "group", Py_BuildValue("s", "TKIP"));
		PyList_Append(pairwise_list, Py_BuildValue("s", "TKIP"));
		PyMapping_SetItemString(wpa_dict, "pairwise", pairwise_list);
		return wpa_dict;
	}

	if (memcmp(&iebuf[offset], wpa_oui, 3) != 0)
		PyMapping_SetItemString(wpa_dict, "group", Py_BuildValue("s", "Proprietary"));
	else
		PyMapping_SetItemString(wpa_dict, "group", WirelessInterface_ScanCypher(iebuf[offset + 3]));

	offset += 4;

	if (ielen < (offset + 2)) {
		PyList_Append(pairwise_list, Py_BuildValue("s", "TKIP"));
		PyMapping_SetItemString(wpa_dict, "pairwise", pairwise_list);
		return wpa_dict;
	}

	cnt = iebuf[offset] | (iebuf[offset + 1] << 8);
	offset += 2;

	if (ielen < (offset + 4 * cnt))
		return wpa_dict;

	for (i = 0; i < cnt; i++) {
		if (memcmp(&iebuf[offset], wpa_oui, 3) != 0)
			PyList_Append(pairwise_list, Py_BuildValue("s", "Proprietary"));
		else
			PyList_Append(pairwise_list, WirelessInterface_ScanCypher(iebuf[offset + 3]));

		offset += 4;
	}
	PyMapping_SetItemString(wpa_dict, "pairwise", pairwise_list);

	cnt = iebuf[offset] | (iebuf[offset + 1] << 8);
	offset += 2;

	if (ielen < (offset + 4 * cnt))
		return wpa_dict;

	for (i = 0; i < cnt; i++) {
		if (memcmp(&iebuf[offset], wpa_oui, 3) != 0)
			PyList_Append(auth_list, Py_BuildValue("s", "Proprietary"));
		else
			PyList_Append(auth_list, WirelessInterface_ScanKeyMgt(iebuf[offset + 3]));

		offset += 4;
	}
	PyMapping_SetItemString(wpa_dict, "auth", auth_list);

	return wpa_dict;
}

/* ------------------------------------------------------------------ WirelessInterface_ScanItem */
static int WirelessInterface_ScanItem(wifacesd* data, iwevent* event, iwrange* range, int has_range)
{
	static char buf[128];

	memset(data, 0, sizeof(wifacesd));

	switch (event->cmd) {
	case SIOCGIWAP: {
		iw_ether_ntop((const struct ether_addr*)(event->u.ap_addr.sa_data), buf);

		data->keys[0] = IWSCAN_KE_BSSID;
		data->objs[0] = Py_BuildValue("s", buf);
		data->num     = 1;

		return 1;
	}

	case SIOCGIWFREQ: {
		double freq = iw_freq2float(&(event->u.freq));
		int channel;

		if (freq <= 14.0)
			channel = iw_channel_to_freq((int)(freq), &freq, range);
		else
			channel = iw_freq_to_channel(freq, range);

		iw_print_freq_value(buf, sizeof(buf), freq);

		data->keys[0] = IWSCAN_KE_FREQUENCY;
		data->keys[1] = IWSCAN_KE_CHANNEL;
		data->objs[0] = Py_BuildValue("s", buf);
		data->objs[1] = Py_BuildValue("i", channel);
		data->num     = 2;

		return 0;
	}

	case SIOCGIWMODE: {
		data->keys[0] = IWSCAN_KE_MODE;
		data->objs[0] = Py_BuildValue("s", iw_operation_mode[event->u.mode]);
		data->num     = 1;

		return 0;
	}

	case SIOCGIWNAME: {
		data->keys[0] = IWSCAN_KE_PROTOCOL;
		data->objs[0] = Py_BuildValue("s", event->u.name);
		data->num     = 1;

		return 0;
	}

	case SIOCGIWESSID: {
		memcpy(buf, event->u.essid.pointer, event->u.essid.length);
		buf[event->u.essid.length] = 0x0;

		data->keys[0] = IWSCAN_KE_ESSID;
		data->objs[0] = Py_BuildValue("s", buf);
		data->num     = 1;

		return 0;
	}

	case SIOCGIWENCODE: {
		PyObject* pybool;

		if (event->u.data.flags & IW_ENCODE_DISABLED) pybool = Py_False;
		else pybool = Py_True;

		Py_INCREF(pybool);

		data->keys[0] = IWSCAN_KE_ENC;
		data->objs[0] = pybool;
		data->num     = 1;

		return 0;
	}

	case SIOCGIWRATE: {
		iw_print_bitrate(buf, sizeof(buf), event->u.bitrate.value);

		data->keys[0] = IWSCAN_KE_BITRATE;
		data->objs[0] = Py_BuildValue("s", buf);
		data->num     = 1;

		return 0;
	}

	case IWEVQUAL: {
		iw_print_stats(buf, sizeof(buf), &event->u.qual, range, has_range);

		data->keys[0] = IWSCAN_KE_QUAL;
		data->keys[1] = IWSCAN_KE_STATS;
		data->objs[0] = Py_BuildValue("i", event->u.qual.qual);
		data->objs[1] = Py_BuildValue("s", buf);
		data->num     = 2;

		return 0;
	}

	case IWEVGENIE: {
		unsigned char* buffer = event->u.data.pointer;
		int buflen = event->u.data.length;
		int offset = 0;

		data->keys[0] = IWSCAN_KE_IE;

		//PyObject* ie_list = PyList_New(0);
		//data->objs[0] = ie_list;
		while (offset <= (buflen - 2)) {
			//PyList_Append(ie_list, WirelessInterface_ScanIe(buffer + offset, buflen));
			data->objs[0] = WirelessInterface_ScanIe(buffer + offset, buflen);
			offset += buffer[offset + 1] + 2;
		}

		data->num = 1;

		return 0;
	}

	default:
		return 0;
	}
}

/* -------------------------------------------------------------------- Member/Method Structures */
static PyMethodDef module_methods[] = {
	{
		"version", iwscan_version, METH_NOARGS,
		"Returns the current IwScan version."
	},
	{
		"iw_version", iwscan_iw_version, METH_NOARGS,
		"Returns the current Wireless Extnesions (libiw WE) version."
	},
	{
		"we_version", iwscan_we_version, METH_NOARGS,
		"Returns the current Wireless Extensions (kernel-level WE) version."
	},
	{
		"enum_devices", iwscan_enum_devices, METH_NOARGS,
		"Returns list of wireless devices."
	},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef WirelessInterface_methods[] = {
	{
		"Scan", (PyCFunction)(WirelessInterface_Scan), METH_NOARGS,
		"This function will attempt to scan any local AP's and return a tuple\n"
		"of objectes representing the data contained therein."
	},
	{ NULL, NULL, 0, NULL }
};

static PyMappingMethods WirelessInterface_mapping_methods = {
	WirelessInterface_len,    /* length */
};

static PySequenceMethods WirelessInterface_sequence_methods = {
	WirelessInterface_len,          /* sq_length */
	0,                              /* sq_concat */
	0,                              /* sq_repeat */
	WirelessInterface_seqitem,      /* sq_item */
	0,                              /* sq_slice */
	0,                              /* sq_ass_item */
	0,                              /* sq_ass_slice */
	0,                              /* sq_contains */
	0,                              /* sq_inplace_concat */
	0                               /* sq_inplace_repeat */
};

/* -------------------------------------------------------------------- PyType_WirelessInterface */
static PyTypeObject PyType_WirelessInterface = {
	PyObject_HEAD_INIT(NULL)
	0,                                              /* ob_size */
	"iwscan.WirelessInterface",                     /* tp_name */
	sizeof(WirelessInterface),                      /* tp_basicsize */
	0,                                              /* tp_itemsize */
	(destructor)(WirelessInterface_dealloc),        /* tp_dealloc */
	0,                                              /* tp_print */
	0,                                              /* tp_getattr */
	0,                                              /* tp_setattr */
	0,                                              /* tp_compare */
	0,                                              /* tp_repr */
	0,                                              /* tp_as_number */
	&WirelessInterface_sequence_methods,            /* tp_as_sequence */
	&WirelessInterface_mapping_methods,             /* tp_as_mapping */
	0,                                              /* tp_hash */
	0,                                              /* tp_call */
	0,                                              /* tp_str */
	0,                                              /* tp_getattro */
	0,                                              /* tp_setattro */
	0,                                              /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,       /* tp_flags */
	0,                                              /* tp_doc */
	0,                                              /* tp_traverse */
	0,                                              /* tp_clear */
	0,                                              /* tp_richcompare */
	0,                                              /* tp_weaklistoffset */
	0,                                              /* tp_iter */
	0,                                              /* tp_iternext */
	WirelessInterface_methods,                      /* tp_methods */
	0,                                              /* tp_members */
	0,                                              /* tp_getset */
	0,                                              /* tp_base */
	0,                                              /* tp_dict */
	0,                                              /* tp_descr_get */
	0,                                              /* tp_descr_set */
	0,                                              /* tp_dictoffset */
	(initproc)(WirelessInterface_init),             /* tp_init */
	0,                                              /* tp_alloc */
	PyType_GenericNew,                              /* tp_new */
	0,                                              /* tp_free */
	0,                                              /* tp_is_gc */
	0,                                              /* tp_bases */
	0,                                              /* tp_mro */
	0,                                              /* tp_cache */
	0,                                              /* tp_subclasses */
	0,                                              /* tp_weaklist */
	0                                               /* tp_del */
};

/* ---------------------------------------------------------------------------------- initiwscan */
PyMODINIT_FUNC initiwscan(void)
{
	PyObject* module;

	PyType_Ready(&PyType_WirelessInterface);

	module      = Py_InitModule3("iwscan", module_methods, IWSCAN_DOC_STRING);
	IwScanError = PyErr_NewException("iwscan.error", NULL, NULL);

	Py_INCREF(&PyType_WirelessInterface);
	Py_INCREF(IwScanError);

	PyModule_AddObject(module, "WirelessInterface", (PyObject*)(&PyType_WirelessInterface));
	PyModule_AddObject(module, "error", IwScanError);
}

static PyObject* iwscan_version(PyObject* u1, PyObject* u2)
{
	return Py_BuildValue("(iii)",
			     IWSCAN_VERSION_MAJOR,
			     IWSCAN_VERSION_MINOR,
			     IWSCAN_VERSION_MICRO);
}

static PyObject* iwscan_iw_version(PyObject* u1, PyObject* u2)
{
	return Py_BuildValue("i", WE_VERSION);
}

static PyObject* iwscan_we_version(PyObject* u1, PyObject* u2)
{
	return Py_BuildValue("i", iw_get_kernel_we_version());
}

static inline char* iwscan_get_ifname(char* name, int nsize, char* buf)
{
	char* end;

	while (isspace(*buf))
		buf++;

	end = strstr(buf, ": ");

	if ((end == NULL) || (((end - buf) + 1) > nsize))
		return NULL;

	memcpy(name, buf, (end - buf));
	name[end - buf] = '\0';

	return end;
}

static int iwscan_ifname_hasiwname(char* ifname)
{
	int ret = 0;
	int skfd;
	iwreq wrq;

	if ((skfd = iw_sockets_open()) >= 0) {
		if (iw_get_ext(skfd, ifname, SIOCGIWNAME, &wrq) >= 0)
			ret++;

		iw_sockets_close(skfd);
	}

	return ret;
}

static PyObject* iwscan_enum_devices(PyObject* u1, PyObject* u2)
{
	char buff[1024];
	FILE*     fh;
	PyObject* ifnames = PyList_New(0);

	fh = fopen(PROC_NET_WIRELESS, "r");

	if (fh != NULL) {
		fgets(buff, sizeof(buff), fh);
		fgets(buff, sizeof(buff), fh);

		while (fgets(buff, sizeof(buff), fh)) {
			char name[IFNAMSIZ + 1];
			char *s;

			if ((buff[0] == '\0') || (buff[1] == '\0'))
				continue;

			s = iwscan_get_ifname(name, sizeof(name), buff);

			if (!s)
				continue;

			if (iwscan_ifname_hasiwname(name) > 0)
				PyList_Append(ifnames, Py_BuildValue("s", name));
		}
		fclose(fh);
	}

	return ifnames;
}
