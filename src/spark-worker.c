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

/**
 * SECTION: spark-worker
 * @short_description: A worker running the actual jobs.
 *
 * This class corrdinates the job execution. It is usually living in its private thread.
 */

#include "config.h"
#include "spark-worker.h"

#include <json-glib/json-glib.h>

typedef struct _SparkWorkerPrivate	SparkWorkerPrivate;
struct _SparkWorkerPrivate
{
	gchar *machine_id;   /* unique machine ID */
	gchar *machine_name; /* name of this machine */

	GMainLoop *loop;
};

G_DEFINE_TYPE_WITH_PRIVATE (SparkWorker, spark_worker, G_TYPE_OBJECT)
#define GET_PRIVATE(o) (spark_worker_get_instance_private (o))

/**
 * spark_worker_finalize:
 **/
static void
spark_worker_finalize (GObject *object)
{
	SparkWorker *worker = SPARK_WORKER (object);
	SparkWorkerPrivate *priv = GET_PRIVATE (worker);

	g_main_loop_unref (priv->loop);

	g_free (priv->machine_id);
	g_free (priv->machine_name);

	G_OBJECT_CLASS (spark_worker_parent_class)->finalize (object);
}

/**
 * spark_worker_init:
 **/
static void
spark_worker_init (SparkWorker *worker)
{
	SparkWorkerPrivate *priv = GET_PRIVATE (worker);

	priv->loop = g_main_loop_new (NULL, FALSE);
}

/**
 * spark_worker_class_init:
 **/
static void
spark_worker_class_init (SparkWorkerClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS (klass);
	object_class->finalize = spark_worker_finalize;
}

/**
 * spark_worker_run_thread:
 *
 * Internal worker thread.
 */
gpointer
spark_worker_run_thread (gpointer user_data)
{
	SparkWorker *worker = SPARK_WORKER (user_data);
	SparkWorkerPrivate *priv = GET_PRIVATE (worker);

	/* run the main event loop */
	g_main_loop_run (priv->loop);
	return NULL;
}


/**
 * spark_worker_run:
 *
 * Run the worker and allow it to accept jobs.
 */
void
spark_worker_run (SparkWorker *worker)
{
	g_assert (!spark_worker_is_running (worker));

	g_thread_new (NULL,
		      spark_worker_run_thread,
		      worker);
}

/**
 * spark_worker_is_running:
 *
 * Test whether this job is processing a job.
 */
gboolean
spark_worker_is_running (SparkWorker *worker)
{
	SparkWorkerPrivate *priv = GET_PRIVATE (worker);
	return g_main_loop_is_running (priv->loop);
}

/**
 * spark_worker_new:
 *
 * Creates a new #SparkWorker.
 *
 * Returns: (transfer full): a #SparkWorker
 *
 **/
SparkWorker*
spark_worker_new (void)
{
	SparkWorker *worker;
	worker = g_object_new (SPARK_TYPE_WORKER, NULL);
	return SPARK_WORKER (worker);
}
