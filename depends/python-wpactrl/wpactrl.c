/*
 * python-wpactrl
 * --------------
 * A Python extension for wpa_supplicant/hostapd control interface access
 *
 * Copyright (c) 2008 Kel Modderman <kel@otaku42.de>
 * License: GPL v2
 *
 * This is based on (a fork of) pywpa:
 *   http://downloads.emperorlinux.com/contrib/pywpa/
 * Copyright (c) 2006 Jeremy Moles <jeremy@emperorlinux.com>
 * License: LGPL v2.1
 *
 */

#include <Python.h>
#include <structmember.h>
#include <osdefs.h>

#include "wpa_ctrl.h"

#define WPACTRL_MAJ_VER 1
#define WPACTRL_MIN_VER 0
#define WPACTRL_MIC_VER 1

#define UNUSED __attribute__ (( __unused__ ))

/* ------------------------------------------------------------------------------------- WPACtrl */
typedef struct {
	PyObject_HEAD
	struct wpa_ctrl* ctrl_iface;
	char* ctrl_iface_path;
	int attached;
} WPACtrl;

/* -------------------------------------------------------------------------Function Definitions */
static PyObject* wpactrl_version(PyObject*, PyObject*);

static int       WPACtrl_open(WPACtrl*, PyObject*, PyObject*);
static PyObject* WPACtrl_request(WPACtrl*, PyObject*, PyObject*);
static PyObject* WPACtrl_attach(WPACtrl*);
static PyObject* WPACtrl_detach(WPACtrl*);
static PyObject* WPACtrl_pending(WPACtrl*);
static PyObject* WPACtrl_recv(WPACtrl*);
static PyObject* WPACtrl_scanresults(WPACtrl*);
static void      WPACtrl_close(WPACtrl*);
static PyObject* WPACtrl_error;

/* -------------------------------------------------------------------------- WPACTRL_DOC_STRING */
static char* WPACTRL_DOC_STRING =
	"wpactrl defines a single class, WPACtrl, that must be instantiated\n"
	"with the pathname of a UNIX domain socket control interface of a\n"
	"wpa_supplicant/hostapd daemon.\n"
	"\n"
	"Once a WPACtrl object has been instantiated, it may call several\n"
	"helper methods to interact with the wpa_supplicant/hostapd daemon.\n"
	"If an error occurs, a wpactrl.error exception is raised.\n"
	"\n"
	"The destructor of a WPACtrl instance closes the connection to the\n"
	"control interface socket.\n"
	"\n"
	"Recommendations for the use of wpa_supplicant/hostapd control\n"
	"interface access in external programs are at:\n"
	"    <http://w1.fi/wpa_supplicant/devel/ctrl_iface_page.html>\n"
;

/* ----------------------------------------------------------------------------- wpactrl_version */
static PyObject* wpactrl_version(UNUSED PyObject* u1, UNUSED PyObject* u2)
{
	return Py_BuildValue("(iii)", WPACTRL_MAJ_VER, WPACTRL_MIN_VER, WPACTRL_MIC_VER);
}

/* -------------------------------------------------------------------------------- WPACtrl_open */
static int WPACtrl_open(WPACtrl* self, PyObject* args, UNUSED PyObject* kargs)
{
	char* path;

	if (!PyArg_ParseTuple(args, "s", &path)) {
		PyErr_SetString(WPACtrl_error, "failed to parse ctrl_iface_path string");
		return -1;
	}

	if (strlen(path) >= MAXPATHLEN) {
		PyErr_SetString(WPACtrl_error, "ctrl_iface_path string length too long");
		return -1;
	}

	self->ctrl_iface_path = malloc(MAXPATHLEN);

	if (!self->ctrl_iface_path) {
		PyErr_SetString(WPACtrl_error, "failed to allocate memory for ctrl_iface_path");
		return -1;
	}

	strcpy(self->ctrl_iface_path, path);

	self->ctrl_iface = wpa_ctrl_open(self->ctrl_iface_path);

	if (!self->ctrl_iface) {
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_open failed");
		return -1;
	}

	self->attached = 0;

	return 0;
}

/* ----------------------------------------------------------------------------- WPACtrl_request */
static PyObject* WPACtrl_request(WPACtrl* self, PyObject* args, UNUSED PyObject* kargs)
{
	int ret;
	char* cmd;
	char buf[2048];
	size_t buflen = sizeof(buf) - 1;

	if (!PyArg_ParseTuple(args, "s", &cmd)) {
		PyErr_SetString(WPACtrl_error, "failed to parse request command string");
		return NULL;
	}

	ret = wpa_ctrl_request(self->ctrl_iface, cmd, strlen(cmd), buf, &buflen, NULL);

	switch (ret) {
	case 0:
		buf[buflen] = '\0';
		return Py_BuildValue("s", buf);
	case -1:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_request failed");
		break;
	case -2:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_request timed out");
		break;
	default:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_request returned unknown error");
		break;
	}

	return NULL;
}

/* ------------------------------------------------------------------------------ WPACtrl_attach */
static PyObject* WPACtrl_attach(WPACtrl* self)
{
	int ret;

	if (self->attached == 1)
		Py_RETURN_NONE;

	ret = wpa_ctrl_attach(self->ctrl_iface);

	switch (ret) {
	case 0:
		self->attached = 1;
		Py_RETURN_NONE;
	case -1:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_attach failed");
		break;
	case -2:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_attach timed out");
		break;
	default:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_attach returned unknown error");
		break;
	}

	return NULL;
}

/* ------------------------------------------------------------------------------ WPACtrl_detach */
static PyObject* WPACtrl_detach(WPACtrl* self)
{
	int ret;

	if (self->attached == 0)
		Py_RETURN_NONE;

	ret = wpa_ctrl_detach(self->ctrl_iface);

	switch (ret) {
	case 0:
		self->attached = 0;
		Py_RETURN_NONE;
	case -1:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_detach failed");
		break;
	case -2:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_detach timed out");
		break;
	default:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_detach returned unknown error");
		break;
	}

	return NULL;
}

/* ----------------------------------------------------------------------------- WPACtrl_pending */
static PyObject* WPACtrl_pending(WPACtrl* self)
{
	int ret;

	ret = wpa_ctrl_pending(self->ctrl_iface);

	switch (ret) {
	case 1:
		Py_RETURN_TRUE;
	case 0:
		Py_RETURN_FALSE;
	case -1:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_pending failed");
		break;
	default:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_pending returned unknown error");
		break;
	}

	return NULL;
}

/* -------------------------------------------------------------------------------- WPACtrl_recv */
static PyObject* WPACtrl_recv(WPACtrl* self)
{
	int ret;
	char buf[256];
	size_t buflen = sizeof(buf) - 1;

	Py_BEGIN_ALLOW_THREADS
	ret = wpa_ctrl_recv(self->ctrl_iface, buf, &buflen);
	Py_END_ALLOW_THREADS

	switch (ret) {
	case 0:
		buf[buflen] = '\0';
		return Py_BuildValue("s", buf);
	case -1:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_recv failed");
		break;
	default:
		PyErr_SetString(WPACtrl_error, "wpa_ctrl_recv returned unknown error");
		break;
	}

	return NULL;
}


/* ------------------------------------------------------------------------- WPACtrl_scanresults */
static PyObject* WPACtrl_scanresults(WPACtrl* self)
{
	int cell;
	PyObject* results = PyList_New(0);

	for (cell = 0; cell < 1000; cell++) {
		int ret;
		char bss[10];
		char buf[2048];
		size_t buflen = sizeof(buf) - 1;

		snprintf(bss, sizeof(bss), "BSS %d", cell);

		ret = wpa_ctrl_request(self->ctrl_iface, bss, sizeof(bss), buf, &buflen, NULL);

		switch (ret) {
		case 0:
			buf[buflen] = '\0';
			break;
		case -1:
			PyErr_SetString(WPACtrl_error, "wpa_ctrl_request failed");
			return NULL;
		case -2:
			PyErr_SetString(WPACtrl_error, "wpa_ctrl_request timed out");
			return NULL;
		default:
			PyErr_SetString(WPACtrl_error, "wpa_ctrl_request returned unknown error");
			return NULL;
		}

		if (strstr(buf, "bssid="))
			PyList_Append(results, Py_BuildValue("s", buf));
		else
			break;
	}

	return results;
}

/* ------------------------------------------------------------------------------- WPACtrl_close */
static void WPACtrl_close(WPACtrl* self)
{
	if (self->ctrl_iface) {
		if (self->attached == 1)
			WPACtrl_detach(self);

		wpa_ctrl_close(self->ctrl_iface);
		self->ctrl_iface = NULL;
	}

	if (self->ctrl_iface_path) {
		free(self->ctrl_iface_path);
		self->ctrl_iface_path = NULL;
	}

	if (self->ob_type)
		self->ob_type->tp_free((PyObject*)(self));
}

/* -------------------------------------------------------------------- Member/Method Structures */
static PyMethodDef module_methods[] = {
	{
		"version", wpactrl_version, METH_NOARGS,
		"Returns a version tuple of wpactrl consisting of 3 integers; major version,\n"
		"minor version and micro version."
	},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef WPACtrl_methods[] = {
	{
		"request", (PyCFunction)(WPACtrl_request), METH_VARARGS,
		"Send a command to wpa_supplicant/hostapd. Returns the command response\n"
		"in a string."
	},
	{
		"attach", (PyCFunction)(WPACtrl_attach), METH_NOARGS,
		"Register as an event monitor for the control interface."
	},
	{
		"detach", (PyCFunction)(WPACtrl_detach), METH_NOARGS,
		"Unregister event monitor from the control interface."
	},
	{
		"pending", (PyCFunction)(WPACtrl_pending), METH_NOARGS,
		"Check if any events/messages are pending. Returns True if messages are pending,\n"
		"otherwise False."
	},
	{
		"recv", (PyCFunction)(WPACtrl_recv), METH_NOARGS,
		"Recieve a pending event/message from ctrl socket. Returns a message string."
	},
	{
		"scanresults", (PyCFunction)(WPACtrl_scanresults), METH_NOARGS,
		"Return list of scan results. Each element of the scan result list is a string\n"
		"of properties for a single BSS. This method is specific to wpa_supplicant."
	},
	{ NULL, NULL, 0, NULL }
};

static PyMemberDef WPACtrl_members[] = {
	{
		"attached", T_INT, offsetof(WPACtrl, attached), READONLY,
		"Set to value of 1 if instance has registered as an event monitor via\n"
		"the attached() method, otherwise 0."
	},
	{
		"ctrl_iface_path", T_STRING, offsetof(WPACtrl, ctrl_iface_path), READONLY,
		"Pathname of WPACtrl control interface socket."
	},
	{ NULL }
};

/* ------------------------------------------------------------------------------ PyType_WPACtrl */
static PyTypeObject PyType_WPACtrl = {
	PyObject_HEAD_INIT(NULL)
	0,                                              /* ob_size */
	"wpactrl.WPACtrl",                              /* tp_name */
	sizeof(WPACtrl),                                /* tp_basicsize */
	0,                                              /* tp_itemsize */
	(destructor)(WPACtrl_close),                    /* tp_dealloc */
	0,                                              /* tp_print */
	0,                                              /* tp_getattr */
	0,                                              /* tp_setattr */
	0,                                              /* tp_compare */
	0,                                              /* tp_repr */
	0,                                              /* tp_as_number */
	0,                                              /* tp_as_sequence */
	0,                                              /* tp_as_mapping */
	0,                                              /* tp_hash */
	0,                                              /* tp_call */
	0,                                              /* tp_str */
	PyObject_GenericGetAttr,                        /* tp_getattro */
	PyObject_GenericSetAttr,                        /* tp_setattro */
	0,                                              /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,       /* tp_flags */
	0,                                              /* tp_doc */
	0,                                              /* tp_traverse */
	0,                                              /* tp_clear */
	0,                                              /* tp_richcompare */
	0,                                              /* tp_weaklistoffset */
	0,                                              /* tp_iter */
	0,                                              /* tp_iternext */
	WPACtrl_methods,                                /* tp_methods */
	WPACtrl_members,                                /* tp_members */
	0,                                              /* tp_getset */
	0,                                              /* tp_base */
	0,                                              /* tp_dict */
	0,                                              /* tp_descr_get */
	0,                                              /* tp_descr_set */
	0,                                              /* tp_dictoffset */
	(initproc)(WPACtrl_open),                       /* tp_init */
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

/* --------------------------------------------------------------------------------- initwpactrl */
PyMODINIT_FUNC initwpactrl(void)
{
	PyObject* module;

	PyType_Ready(&PyType_WPACtrl);

	module = Py_InitModule3("wpactrl", module_methods, WPACTRL_DOC_STRING);
	WPACtrl_error = PyErr_NewException("wpactrl.error", NULL, NULL);

	Py_INCREF(&PyType_WPACtrl);
	Py_INCREF(WPACtrl_error);

	PyModule_AddObject(module, "WPACtrl", (PyObject*)(&PyType_WPACtrl));
	PyModule_AddObject(module, "error", WPACtrl_error);
}
