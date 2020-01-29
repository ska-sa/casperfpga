# include <Python.h>
#include <stdio.h>

struct module_state {
	    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
static struct module_state _state;
#endif

static char module_docstring[] =
    "This module provides a fast uploading interface for SKARABs.";
static char upload_docstring[] =
    "Upload the given bin file to the given list of SKARAB boards.";

static PyObject *casperfpga_progskaupload(PyObject *self, PyObject *args);

static PyMethodDef module_methods[] = {
    {"upload", casperfpga_progskaupload, METH_VARARGS, upload_docstring},
    {NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION >= 3

static int progska_traverse(PyObject *m, visitproc visit, void *arg) {
	Py_VISIT(GETSTATE(m)->error);
	return 0;
}

static int progska_clear(PyObject *m) {
	Py_CLEAR(GETSTATE(m)->error);
	return 0;
}


static struct PyModuleDef moduledef = {
	PyModuleDef_HEAD_INIT,
	"progska",
	module_docstring,
	sizeof(struct module_state),
	module_methods,
	NULL,
	progska_traverse,
	progska_clear,
	NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC PyInit_progska(void)

#else
#define INITERROR return

PyMODINIT_FUNC initprogska(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
	PyObject *module = PyModule_Create(&moduledef);
#else
	PyObject *module = Py_InitModule("progska", module_methods);
#endif

	if (module == NULL)
		INITERROR;
	struct module_state *st = GETSTATE(module);

	st->error = PyErr_NewException("progska.Error", NULL, NULL);
	if (st->error == NULL) {
		Py_DECREF(module);
		INITERROR;
	}

#if PY_MAJOR_VERSION >= 3
	return module;
#endif
}

static PyObject *casperfpga_progskaupload(PyObject *self, PyObject *args) {
    /*
    Process the arguments from Python and then pass them to the progska
    C method.
    */
    const char *binfile, *skarabname;
    PyObject *hostlist_obj, *host_list, *item;
    const char *packet_size;
    int host_ctr, num_hosts;
    int verbose;
    verbose = 0;
    // parse the input tuple
    if (!PyArg_ParseTuple(args, "sOs", &binfile, &hostlist_obj, &packet_size))
        return NULL;

    if(strlen(binfile) <= 0){
        PyErr_SetString(PyExc_RuntimeError,
            "Must provide a bin file to upload.");
        return NULL;
    }
    if(verbose > 0)
        printf("Programming: %s\n", binfile);

    host_list = PySequence_Fast(hostlist_obj, "Expected a list of hosts.");
    num_hosts = PySequence_Size(hostlist_obj);
    if(num_hosts <= 0){
        PyErr_SetString(PyExc_RuntimeError,
            "Must provide at least one host to which to upload the bin file.");
        return NULL;
    }
    if(verbose > 0)
        printf("Given %i hosts.\n", num_hosts);
    char **mainargs;
    int num_mainargs;
    num_mainargs = num_hosts + 5;
    mainargs = malloc(num_mainargs * sizeof(char*));
    const char *progska = "progksa";
    const char *dashs = "-s";
    const char *dashf = "-f";
    mainargs[0] = progska;
    mainargs[1] = dashs;
    mainargs[2] = packet_size;
    mainargs[3] = dashf;
    mainargs[4] = binfile;
    for (host_ctr = 0; host_ctr < num_hosts; host_ctr++) {
        item = PySequence_Fast_GET_ITEM(host_list, host_ctr);

#if PY_MAJOR_VERSION >= 3
        const char *hostname = PyUnicode_AsUTF8(item);
#else
        const char *hostname = PyString_AsString(item);
#endif
        mainargs[host_ctr + 5] = hostname;
        if(verbose > 0)
            printf("\t%s\n", hostname);
    }
    // call Marc's main function to do the upload
    int marcresult;
    marcresult = main(num_mainargs, mainargs);
    PyObject *ret = Py_BuildValue("i", marcresult);
    // Py_DECREF(host_list); - is this making the segfault
    // Py_DECREF(item);
    free(mainargs);
    return ret;
}

// end
