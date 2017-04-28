
sdnspawn_src = [
    'sdnspawn/main.c'
]

executable('sdnspawn-run',
           [sdnspawn_src],
           dependencies: [thread_dep,
                          glib_dep,
                          gobject_dep],
	   install: true,
	   install_dir: spark_runners_install_dir
)
