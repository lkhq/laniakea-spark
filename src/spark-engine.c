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
 * SECTION: spark-engine
 * @short_description: Job runner and communicator.
 *
 * This class communicates with a Lighthouse server and schedules tasks.
 */

#include "config.h"
#include "spark-engine.h"

#include <json-glib/json-glib.h>
#include <czmq.h>

#include "spark-worker.h"

typedef struct _SparkEnginePrivate	SparkEnginePrivate;
struct _SparkEnginePrivate
{
	gchar *machine_id;   /* unique machine ID */
	gchar *machine_name; /* name of this machine */

	gchar *lighthouse_server; /* endpoint to connect to to receive jobs */
	guint max_jobs;           /* maximum number of tasks we can take */

	gchar *client_cert_fname; /* filename of the private certificate used by this Spark instance */
	gchar *server_cert_fname; /* filename of the public certificate of the server we connect to */

	GPtrArray *workers;
	zsock_t *wsock;
	zsock_t *lhsock;

	GMainLoop *main_loop;
};

G_DEFINE_TYPE_WITH_PRIVATE (SparkEngine, spark_engine, G_TYPE_OBJECT)
#define GET_PRIVATE(o) (spark_engine_get_instance_private (o))

/* path to the global JSON configuration */
static const gchar *config_fname = "/etc/laniakea/spark.json";
static const gchar *certs_base_dir = "/etc/laniakea/keys/curve/";

/**
 * spark_engine_finalize:
 **/
static void
spark_engine_finalize (GObject *object)
{
	SparkEngine *engine = SPARK_ENGINE (object);
	SparkEnginePrivate *priv = GET_PRIVATE (engine);

	g_main_loop_unref (priv->main_loop);

	g_free (priv->machine_id);
	g_free (priv->machine_name);
	g_free (priv->lighthouse_server);
	g_ptr_array_unref (priv->workers);

	if (priv->lhsock != NULL)
		zsock_destroy (&priv->lhsock);
	zsock_destroy (&priv->wsock);

	G_OBJECT_CLASS (spark_engine_parent_class)->finalize (object);
}

/**
 * spark_engine_init:
 **/
static void
spark_engine_init (SparkEngine *engine)
{
	SparkEnginePrivate *priv = GET_PRIVATE (engine);

	priv->workers = g_ptr_array_new_with_free_func (g_object_unref);
	priv->main_loop = g_main_loop_new (NULL, FALSE);
	priv->max_jobs = 1;

	/* create internal socket for the worker processes to connect to */
	priv->wsock = zsock_new_pull ("inproc://workers");
	g_assert (priv->wsock);
}

/**
 * spark_engine_class_init:
 **/
static void
spark_engine_class_init (SparkEngineClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS (klass);
	object_class->finalize = spark_engine_finalize;
}

/**
 * spark_engine_compose_job_request:
 *
 * Compose a job request.
 */
static gchar*
spark_engine_compose_job_request (SparkEngine *engine)
{
	SparkEnginePrivate *priv = GET_PRIVATE (engine);
	g_autoptr(JsonBuilder) builder = NULL;
	g_autoptr(JsonGenerator) gen = NULL;
	g_autoptr(JsonNode) root = NULL;

	builder = json_builder_new ();

	json_builder_begin_object (builder);

	/* set that we request a job */
	json_builder_set_member_name (builder, "request");
	json_builder_add_string_value (builder, "job");

	/* set requester details */
	json_builder_set_member_name (builder, "machine_name");
	json_builder_add_string_value (builder, priv->machine_name);

	json_builder_set_member_name (builder, "machine_id");
	json_builder_add_string_value (builder, priv->machine_id);

	/* we currently accept all jobs */
	json_builder_set_member_name (builder, "accepts");
	json_builder_begin_array (builder);
	json_builder_add_string_value (builder, "*");
	json_builder_end_array (builder);

	json_builder_end_object (builder);

	/* write JSON string */
	gen = json_generator_new ();
	root = json_builder_get_root (builder);
	json_generator_set_root (gen, root);

	return json_generator_to_data (gen, NULL);
}

/**
 * spark_engine_request_jobs:
 *
 * Ask the master for new jobs in case we have capacity for them,
 * and enqueue the new jobs for running.
 */
static void
spark_engine_request_jobs (SparkEngine *engine)
{
	SparkEnginePrivate *priv = GET_PRIVATE (engine);
	guint i;

	for (i = 0; i < priv->workers->len; i++) {
		SparkWorker *worker = SPARK_WORKER (g_ptr_array_index (priv->workers, i));

		/* test if we have capacity */
		if (!spark_worker_is_running (worker)) {
			g_autofree gchar *request_msg = NULL;
			g_autofree gchar *reply_msg = NULL;
			zmsg_t *msg;
			zpoller_t *poller = zpoller_new (priv->lhsock, NULL);

			request_msg = spark_engine_compose_job_request (engine);

			/* emit request */
			zstr_send (priv->lhsock, request_msg);

			/* wait for reply for 8sec */
			zpoller_wait (poller, 8 * 1000);
			if (zpoller_expired (poller)) {
				g_printerr ("Job request expired (the master server might be unreachable).\n");

				/* since the server is possibly unreachable, we sleep some time */
				usleep (20 * 1000 * 1000);
				zpoller_destroy (&poller);
				continue;
			} else if (zpoller_terminated (poller)) {
				g_printerr ("Job request was terminated.\n");
				zpoller_destroy (&poller);
				continue;
			}
			zpoller_destroy (&poller);

			/* unpack and parse the reply message */
			msg = zmsg_recv (priv->lhsock);
			if (msg == NULL) {
				g_printerr ("Received NULL reply.\n");
				continue;
			}
			reply_msg = zmsg_popstr (msg);
			if (reply_msg == NULL) {
				g_printerr ("Reply message was empty.");
				continue;
			}
			zmsg_destroy (&msg);

			spark_worker_set_job_from_json (worker, reply_msg);
			spark_worker_run (worker);
		}
	}
}

/**
 * spark_engine_route_messages:
 */
static gboolean
spark_engine_route_messages (gpointer user_data)
{
	SparkEngine *engine = SPARK_ENGINE (user_data);

	/* request fresh jobs if we have capacity */
	spark_engine_request_jobs (engine);

	return TRUE;
}

/**
 * spark_engine_load_config:
 */
static gboolean
spark_engine_load_config (SparkEngine *engine, GError **error)
{
	SparkEnginePrivate *priv = GET_PRIVATE (engine);
	g_autoptr(JsonParser) parser = NULL;
	JsonObject *root;
	g_autofree gchar *client_cert_basename = NULL;
	g_autofree gchar *server_cert_basename = NULL;

	/* fetch the machine ID first */
	if (!g_file_get_contents ("/etc/machine-id", &priv->machine_id, NULL, error))
		return FALSE;
	g_strdelimit (priv->machine_id, "\n", ' ');
	g_strstrip (priv->machine_id);

	parser = json_parser_new ();
	if (!json_parser_load_from_file (parser, config_fname, error))
		return FALSE;

	root = json_node_get_object (json_parser_get_root (parser));
	if (root == NULL) {
		g_set_error (error, SPARK_ENGINE_ERROR,
			     SPARK_ENGINE_ERROR_FAILED,
			     "The configuration in '%s' is not valid.", config_fname);
		return FALSE;
	}

	if (json_object_has_member (root, "MachineName")) {
		priv->machine_name = g_strdup (json_object_get_string_member (root, "MachineName"));
		g_strstrip (priv->machine_name);
	} else {
		/* we don't have a manually set machine name, take the hostname */
		if (!g_file_get_contents ("/etc/hostname", &priv->machine_name, NULL, error))
			return FALSE;
		g_strdelimit (priv->machine_name, "\n", ' ');
		g_strstrip (priv->machine_name);
	}

	priv->lighthouse_server = g_strdup (json_object_get_string_member (root, "LighthouseServer"));
	if (priv->lighthouse_server == NULL) {
		g_set_error (error, SPARK_ENGINE_ERROR,
			     SPARK_ENGINE_ERROR_FAILED,
			     "The configuration defines no Lighthouse server to connect to.");
		return FALSE;
	}

	if (json_object_has_member (root, "MaxJobs")) {
		priv->max_jobs = json_object_get_int_member (root, "MaxJobs");

		/* check values for sanity */
		if (priv->max_jobs <= 0 || priv->max_jobs > 100) {
			g_warning ("A number of %i jobs looks wrong. Resetting maximum job count to 1.", priv->max_jobs);
			priv->max_jobs = 1;
		}
	}

	/* determine certificate filenames */
	client_cert_basename = g_strdup_printf ("%s_private.sec", priv->machine_name);
	priv->client_cert_fname = g_build_filename (certs_base_dir, client_cert_basename, NULL);

	server_cert_basename = g_strdup_printf ("%s_lighthouse-server.pub", priv->machine_name);
	priv->server_cert_fname = g_build_filename (certs_base_dir, server_cert_basename, NULL);

	return TRUE;
}

/**
 * spark_engine_run:
 */
gboolean
spark_engine_run (SparkEngine *engine, GError **error)
{
	SparkEnginePrivate *priv = GET_PRIVATE (engine);
	g_autoptr(GMainLoop) loop = NULL;
	guint i;
	zcert_t *client_cert;
	zcert_t *server_cert;

	if (!spark_engine_load_config (engine, error))
		return FALSE;

	if (priv->lhsock != NULL)
		zsock_destroy (&priv->lhsock);
	priv->lhsock = zsock_new (ZMQ_DEALER);
	if (priv->lhsock == NULL) {
		g_set_error (error, SPARK_ENGINE_ERROR,
			     SPARK_ENGINE_ERROR_FAILED,
			     "Unable to connect: %s",
			     g_strerror (errno));
		return FALSE;
	}

	client_cert = zcert_load (priv->client_cert_fname);
	if (client_cert == NULL) {
		g_set_error (error, SPARK_ENGINE_ERROR,
			     SPARK_ENGINE_ERROR_FAILED,
			     "Unable to load client certificate '%s': %s",
			     priv->client_cert_fname,
			     g_strerror (errno));
		return FALSE;
	}

	server_cert = zcert_load (priv->server_cert_fname);
	if (server_cert == NULL) {
		g_set_error (error, SPARK_ENGINE_ERROR,
			     SPARK_ENGINE_ERROR_FAILED,
			     "Unable to load server public certificate '%s': %s",
			     priv->server_cert_fname,
			     g_strerror (errno));
		return FALSE;
	}

	/* makes tracing easier */
	zsock_set_identity (priv->lhsock, priv->machine_name);

	/* use our secret client certificate */
	zcert_apply (client_cert, priv->lhsock);
	zcert_destroy (&client_cert);

	/* we need to know who we are connecting to - set the public server certificate */
	zsock_set_curve_serverkey (priv->lhsock,
				   zcert_public_txt (server_cert));
	zcert_destroy (&server_cert);

	/* connect to Lighthouse */
	if (zsock_connect (priv->lhsock, priv->lighthouse_server) == -1) {
		g_set_error (error, SPARK_ENGINE_ERROR,
			     SPARK_ENGINE_ERROR_FAILED,
			     "Unable to connect to '%s': %s",
			     priv->lighthouse_server,
			     g_strerror (errno));
		return FALSE;
	}

	/* new main loop for the master thread */
	loop = g_main_loop_new (NULL, FALSE);

	for (i = 0; i < priv->max_jobs; i++) {
		SparkWorker *worker;

		worker = spark_worker_new ();
		g_ptr_array_add (priv->workers, worker);
	}

	g_print ("Running on %s (%s), job capacity: %i\n", priv->machine_name, priv->machine_id, priv->max_jobs);

	g_idle_add (spark_engine_route_messages, engine);
	g_main_loop_run (loop);

	/* wait for workers to finish and clean up */
	for (i = 0; i < priv->workers->len; i++) {
		SparkWorker *worker = SPARK_WORKER (g_ptr_array_index (priv->workers, i));

		while (spark_worker_is_running (worker)) { sleep (1000); }
	}

	return TRUE;
}

/**
 * spark_engine_new:
 *
 * Creates a new #SparkEngine.
 *
 * Returns: (transfer full): a #SparkEngine
 *
 **/
SparkEngine*
spark_engine_new (void)
{
	SparkEngine *engine;
	engine = g_object_new (SPARK_TYPE_ENGINE, NULL);
	return SPARK_ENGINE (engine);
}

/**
 * spark_engine_error_quark:
 *
 * Return value: An error quark.
 **/
GQuark
spark_engine_error_quark (void)
{
	static GQuark quark = 0;
	if (!quark)
		quark = g_quark_from_static_string ("SparkEngineError");
	return quark;
}
