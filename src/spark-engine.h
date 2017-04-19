/*
 * Copyright (C) 2017 Matthias Klumpp <matthias@tenstral.net>
 *
 * Licensed under the GNU Lesser General Public License Version 3
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the license, or
 * (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this software.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef _SPARK_ENGINE_H
#define _SPARK_ENGINE_H

#include <glib-object.h>
#include <gio/gio.h>

G_BEGIN_DECLS

#define SPARK_TYPE_ENGINE (spark_engine_get_type ())
G_DECLARE_DERIVABLE_TYPE (SparkEngine, spark_engine, SPARK, ENGINE, GObject)

struct _SparkEngineClass
{
	GObjectClass		parent_class;
	/*< private >*/
	void (*_as_reserved1)	(void);
	void (*_as_reserved2)	(void);
	void (*_as_reserved3)	(void);
	void (*_as_reserved4)	(void);
	void (*_as_reserved5)	(void);
	void (*_as_reserved6)	(void);
};

/**
 * SparkEngineError:
 * @SPARK_ENGINE_ERROR_FAILED:			Generic failure
 *
 * The error type.
 **/
typedef enum {
	SPARK_ENGINE_ERROR_FAILED,
	/*< private >*/
	SPARK_ENGINE_ERROR_LAST
} SparkEngineError;

#define SPARK_ENGINE_ERROR spark_engine_error_quark ()
GQuark			spark_engine_error_quark (void);

SparkEngine		*spark_engine_new (void);

gboolean		spark_engine_run (SparkEngine *engine,
					  GError **error);

G_END_DECLS

#endif /* _SPARK_ENGINE_H */
