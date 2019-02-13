*WARNING: Historic project*

Please look at e.g. https://thespianpy.com/doc/ for maintained and
working solution to same problem (as of 2/2019).

# What is this? ( .. or was .. )

This is mpykka; a work-in-progress multiprocessing oriented version of
pykka, for use with e.g. computationally heavy loads so that CPU can
be saturated despite the GIL using pure Python goodness.

API is similar to Pykka, but somewhat different. E.g. concurrency
model is assumed to be Threading based one locally, and
multiprocessing is used between processes, but there are just
Actor+Future(+Process) classes that are user visible.


See https://github.com/jodal/pykka/ for usage.
