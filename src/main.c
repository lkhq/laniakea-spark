/*
 * Copyright (C) 2017 Matthias Klumpp <matthias@tenstral.net>
 *
 * Licensed under the GNU General Public License Version 3
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the license, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <config.h>
#include <glib.h>
#include <czmq.h>

#include "spark-engine.h"

/**
 * main:
 */
int
main (int argc, char *argv[])
{
    GError *error = NULL;
    GOptionContext *opt_context;
    g_autoptr(SparkEngine) engine = NULL;

    static gboolean opt_show_version = FALSE;
    static gboolean opt_verbose_mode = FALSE;
    const GOptionEntry base_options[] = {
        { "version", 0, 0,
            G_OPTION_ARG_NONE,
            &opt_show_version,
            "Show the program version.",
            NULL },
        { "verbose", (gchar) 0, 0,
            G_OPTION_ARG_NONE,
            &opt_verbose_mode,
            "Show extra debugging information.",
            NULL },
        { NULL }
    };

    opt_context = g_option_context_new ("- Laniakea Spark");

    /* parse options */
    g_option_context_add_main_entries (opt_context, base_options, NULL);
    if (!g_option_context_parse (opt_context, &argc, &argv, &error)) {
        g_printerr ("option parsing failed: %s\n", error->message);
        return 1;
    }

    if (opt_show_version) {
        g_print ("%s %s\n", PACKAGE_NAME, PACKAGE_VERSION);
        return 0;
    }

    /* don't set default CZMQ signal handler, so CTRL+C works. */
    /* FIXME: We might want our own handler here. */
    zsys_handler_set (NULL);

    engine = spark_engine_new ();

    if (!spark_engine_run (engine, &error)) {
	    g_printerr ("Failure: %s\n", error->message);
	    return 2;
    }

    return 0;
}
