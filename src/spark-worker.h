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

#ifndef _SPARK_WORKER_H
#define _SPARK_WORKER_H

#include <glib-object.h>
#include <gio/gio.h>

G_BEGIN_DECLS

#define SPARK_TYPE_WORKER (spark_worker_get_type ())
G_DECLARE_DERIVABLE_TYPE (SparkWorker, spark_worker, SPARK, WORKER, GObject)

struct _SparkWorkerClass
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

SparkWorker		*spark_worker_new (void);

void			spark_worker_run (SparkWorker *worker);

gboolean		spark_worker_is_running (SparkWorker *worker);

G_END_DECLS

#endif /* _SPARK_WORKER_H */
