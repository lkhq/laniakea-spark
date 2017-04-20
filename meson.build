project('Laniakea Spark', 'c')

spark_version = '0.1'

compiler = meson.get_compiler('c')

#
# Sources
#
spark_src = [
    'src/main.c',
    'src/spark-engine.h',
    'src/spark-engine.c',
    'src/spark-worker.h',
    'src/spark-worker.c'
]

#
# Dependencies
#
thread_dep = dependency('threads')
glib_dep = dependency('glib-2.0')
gobject_dep = dependency('gobject-2.0')
czmq_dep = dependency('libczmq')
json_dep = dependency('json-glib-1.0')
math_lib = compiler.find_library('m')

#
# Configuration
#
conf = configuration_data()
conf.set_quoted('PACKAGE_NAME', 'Laniakea Spark')
conf.set_quoted('PACKAGE_VERSION', spark_version)

configure_file(input: 'config.h.in',
               output: 'config.h',
               configuration: conf
)

#
# Settings
#
add_global_arguments(['-Werror=implicit-function-declaration', '-Wno-unused-parameter'], language: 'c')

if (get_option('maintainer'))
    add_global_arguments(['-Werror', '-Wall', '-Wextra'], language: 'c')
endif

#
# Targets
#
executable('lk-spark',
           [spark_src],
           dependencies: [thread_dep,
                          glib_dep,
                          gobject_dep,
                          czmq_dep,
                          json_dep,
                          math_lib],
	   install: true
)
