"""Credential-safe database access and bounded snapshot fingerprints."""

import hashlib
import os
import shutil
import subprocess

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from deploy.release.baseline_artifact import BaselineError, canonical

RECEIPT_TABLE = "deployment_baseline"
LOCK_ID = 247249


def connection_parameters(dsn_env="DAYLOOM_DB_URL"):
    supplied = os.environ.get(dsn_env)
    if supplied:
        parameters = conninfo_to_dict(supplied)
    else:
        parameters = {
            "host": os.environ.get("DAYLOOM_DB_HOST", "127.0.0.1"),
            "port": os.environ.get("DAYLOOM_DB_PORT", "5432"),
            "dbname": os.environ.get("DAYLOOM_DB_NAME", "dayloom"),
            "user": os.environ.get("DAYLOOM_DB_USER", "dayloom"),
            "password": os.environ.get("DAYLOOM_DB_PASSWORD", ""),
        }
        if not parameters["password"]:
            raise BaselineError("Provide database connection settings")
    if not parameters.get("dbname"):
        raise BaselineError("The database connection must specify its database")
    parameters.setdefault("connect_timeout", "10")
    return parameters


def connect(parameters):
    connection = psycopg.connect(**parameters, autocommit=True)
    connection.execute("SET timezone = 'UTC'")
    connection.execute("SET datestyle = 'ISO, YMD'")
    connection.execute("SET extra_float_digits = 3")
    connection.execute("SET search_path = pg_catalog")
    return connection


def tool_environment(parameters):
    environment = dict(os.environ)
    names = {
        "host": "PGHOST", "hostaddr": "PGHOSTADDR", "port": "PGPORT",
        "dbname": "PGDATABASE", "user": "PGUSER", "password": "PGPASSWORD",
        "sslmode": "PGSSLMODE", "sslrootcert": "PGSSLROOTCERT", "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY", "connect_timeout": "PGCONNECT_TIMEOUT", "options": "PGOPTIONS",
        "application_name": "PGAPPNAME", "passfile": "PGPASSFILE", "service": "PGSERVICE",
    }
    # Never let ambient libpq settings silently select a different target.
    for key in list(environment):
        if key.startswith("PG"):
            environment.pop(key)
    for key, value in parameters.items():
        if key not in names:
            raise BaselineError("Unsupported database connection option for PostgreSQL tools")
        environment[names[key]] = str(value)
    return environment


def run_tool(name, arguments, parameters, *, input_stream=None, output_stream=None):
    executable = shutil.which(name)
    if not executable:
        raise BaselineError("PostgreSQL 17 client tools are required")
    result = subprocess.run(
        [executable, *arguments], env=tool_environment(parameters), stdin=input_stream,
        stdout=output_stream or subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        # libpq/pg_restore errors may contain connection details and private rows.
        raise BaselineError(name + " failed; target data was not marked installed")
    return result.stdout


def server_identity(connection):
    major = int(connection.execute("SHOW server_version_num").fetchone()[0]) // 10000
    extensions = [{"name": name, "version": version, "schema": schema}
                  for name, version, schema in connection.execute(
        "SELECT e.extname,e.extversion,n.nspname FROM pg_extension e "
        "JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname <> 'plpgsql' "
        "ORDER BY e.extname"
    )]
    return {"server_major": major, "extensions": extensions}


def require_compatibility(connection, expected):
    actual = server_identity(connection)
    if actual["server_major"] != expected["server_major"]:
        raise BaselineError("PostgreSQL major version does not match the baseline")
    available = dict(connection.execute("SELECT name,version FROM pg_available_extension_versions"))
    for extension in expected["extensions"]:
        if extension["name"] == "vector" and extension["version"] != available.get("vector"):
            versions = {row[0] for row in connection.execute(
                "SELECT version FROM pg_available_extension_versions WHERE name='vector'"
            )}
            if extension["version"] not in versions:
                raise BaselineError("Required vector extension version is unavailable")


def tables(connection):
    return list(connection.execute(
        "SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE c.relkind='r' AND n.nspname !~ '^pg_' "
        "AND n.nspname <> 'information_schema' "
        "AND NOT (n.nspname='app' AND c.relname=%s) ORDER BY n.nspname,c.relname",
        (RECEIPT_TABLE,),
    ))



def is_empty_database(connection):
    """Shared first-restore admission for factory and private backups."""
    return not connection.execute(
        "SELECT 1 FROM pg_namespace WHERE nspname !~ '^pg_' "
        "AND nspname NOT IN ('information_schema','public') "
        "UNION ALL SELECT 1 FROM pg_depend d JOIN pg_namespace n ON n.oid=d.refobjid "
        "WHERE d.refclassid='pg_namespace'::regclass AND n.nspname='public' "
        "UNION ALL SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql' LIMIT 1"
    ).fetchone() and _unsupported_catalog_object(connection) is None


def _unsupported_catalog_object(connection):
    # v1 predates complete catalog fingerprints. Keep its manifest identity stable:
    # reject unrepresented objects/state, rather than silently calling them an exact match.
    # Extension members and their internal objects (not arbitrary dependents) are
    # identified by the separately pinned extension version and namespace.
    return connection.execute("""
        WITH RECURSIVE extension_owned(classid,objid) AS (
            SELECT classid,objid FROM pg_depend WHERE deptype='e'
            UNION
            SELECT d.classid,d.objid FROM pg_depend d JOIN extension_owned e
                ON d.refclassid=e.classid AND d.refobjid=e.objid WHERE d.deptype='i'
        ), user_namespaces AS (
            SELECT oid FROM pg_namespace
            WHERE nspname !~ '^pg_' AND nspname <> 'information_schema'
        ), supported_types(oid) AS (
            SELECT t.oid FROM pg_type t JOIN pg_class c ON c.oid=t.typrelid
                WHERE t.typtype='c' AND c.relkind IN ('r','v')
            UNION SELECT objid FROM extension_owned WHERE classid='pg_type'::regclass
            UNION SELECT t.oid FROM pg_type t JOIN supported_types s ON s.oid=t.typelem
                WHERE t.typtype='b' AND t.typcategory='A' AND EXISTS (
                    SELECT 1 FROM pg_depend d WHERE d.classid='pg_type'::regclass
                    AND d.objid=t.oid AND d.refclassid='pg_type'::regclass
                    AND d.refobjid=s.oid AND d.deptype='i')
        ), unsupported(classid,objid,category) AS (
            SELECT 'pg_type'::regclass,t.oid,'custom type'
                FROM pg_type t JOIN user_namespaces n ON n.oid=t.typnamespace
                WHERE NOT EXISTS (SELECT 1 FROM supported_types s WHERE s.oid=t.oid)
            UNION ALL
            SELECT 'pg_class'::regclass,c.oid,'relation kind or table settings'
                FROM pg_class c JOIN user_namespaces n ON n.oid=c.relnamespace
                WHERE c.relkind NOT IN ('r','i','v') OR c.relpersistence <> 'p'
                    OR c.relrowsecurity OR c.relforcerowsecurity OR c.relispartition
                    OR (c.relkind IN ('r','v') AND c.reloptions IS NOT NULL)
                    OR (c.relkind='r' AND (c.relreplident <> 'd'
                        OR c.relam <> (SELECT oid FROM pg_am WHERE amname='heap')))
            UNION ALL
            SELECT 'pg_class'::regclass,a.attrelid,'column settings'
                FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
                JOIN user_namespaces n ON n.oid=c.relnamespace
                JOIN pg_type t ON t.oid=a.atttypid
                WHERE a.attnum>0 AND NOT a.attisdropped
                    AND (a.attoptions IS NOT NULL OR a.attfdwoptions IS NOT NULL
                        OR a.attstorage <> t.typstorage OR a.attcompression <> ''
                        OR a.attcollation <> t.typcollation)
            UNION ALL
            SELECT 'pg_proc'::regclass,p.oid,'aggregate or window function'
                FROM pg_proc p JOIN user_namespaces n ON n.oid=p.pronamespace
                WHERE p.prokind NOT IN ('f','p')
            UNION ALL
            SELECT d.classid,d.objid,'schema object'
                FROM pg_depend d JOIN user_namespaces n ON n.oid=d.refobjid
                WHERE d.refclassid='pg_namespace'::regclass AND d.classid NOT IN (
                    'pg_class'::regclass,'pg_proc'::regclass,'pg_type'::regclass,
                    'pg_constraint'::regclass,'pg_extension'::regclass)
            UNION ALL
            SELECT 'pg_policy'::regclass,p.oid,'row policy' FROM pg_policy p
                JOIN pg_class c ON c.oid=p.polrelid
                JOIN user_namespaces n ON n.oid=c.relnamespace
            UNION ALL
            SELECT 'pg_rewrite'::regclass,r.oid,'rule or rule settings' FROM pg_rewrite r
                JOIN pg_class c ON c.oid=r.ev_class
                JOIN user_namespaces n ON n.oid=c.relnamespace
                WHERE NOT (c.relkind='v' AND r.rulename='_RETURN' AND r.ev_enabled='O')
            UNION ALL
            SELECT 'pg_trigger'::regclass,t.oid,'trigger settings' FROM pg_trigger t
                JOIN pg_class c ON c.oid=t.tgrelid
                JOIN user_namespaces n ON n.oid=c.relnamespace WHERE t.tgenabled <> 'O'
            UNION ALL
            SELECT 'pg_class'::regclass,i.inhrelid,'table inheritance' FROM pg_inherits i
                JOIN pg_class c ON c.oid=i.inhrelid
                JOIN user_namespaces n ON n.oid=c.relnamespace
            UNION ALL
            SELECT 'pg_class'::regclass,i.indexrelid,'index settings' FROM pg_index i
                JOIN pg_class c ON c.oid=i.indexrelid
                JOIN user_namespaces n ON n.oid=c.relnamespace
                WHERE NOT i.indisvalid OR NOT i.indisready OR NOT i.indislive
            UNION ALL
            SELECT 'pg_event_trigger'::regclass,oid,'event trigger' FROM pg_event_trigger
            UNION ALL
            SELECT 'pg_cast'::regclass,oid,'cast' FROM pg_cast WHERE oid>=16384
            UNION ALL
            SELECT 'pg_transform'::regclass,oid,'transform' FROM pg_transform WHERE oid>=16384
            UNION ALL
            SELECT 'pg_language'::regclass,oid,'language' FROM pg_language
                WHERE lanname NOT IN ('internal','c','sql','plpgsql')
            UNION ALL
            SELECT 'pg_am'::regclass,oid,'access method' FROM pg_am WHERE oid>=16384
            UNION ALL
            SELECT 'pg_foreign_data_wrapper'::regclass,oid,'foreign data wrapper'
                FROM pg_foreign_data_wrapper
            UNION ALL
            SELECT 'pg_foreign_server'::regclass,oid,'foreign server' FROM pg_foreign_server
            UNION ALL
            SELECT 'pg_publication'::regclass,oid,'publication' FROM pg_publication
            UNION ALL
            SELECT 'pg_subscription'::regclass,oid,'subscription' FROM pg_subscription
            UNION ALL
            SELECT 'pg_largeobject'::regclass,oid,'large object' FROM pg_largeobject_metadata
        )
        SELECT category FROM unsupported u WHERE NOT EXISTS (
            SELECT 1 FROM extension_owned e WHERE e.classid=u.classid AND e.objid=u.objid)
        LIMIT 1
    """).fetchone()


def require_supported_catalog(connection):
    """Fail closed before v1 fingerprints can be used as installation identity."""
    unsupported = _unsupported_catalog_object(connection)
    if unsupported:
        raise BaselineError(
            "Baseline v1 cannot verify " + unsupported[0]
            + "; use a supported snapshot/destination; existing data was preserved"
        )


def require_quiescent(connection):
    if connection.execute("SELECT to_regclass('app.planning_tasks')").fetchone()[0]:
        active = connection.execute(
            "SELECT count(*) FROM app.planning_tasks "
            "WHERE state IN ('pending','running','stopping')"
        ).fetchone()[0]
        if active:
            raise BaselineError("Wait for active planning tasks before exporting the baseline")


def _schema_fingerprint(connection):
    columns = list(connection.execute(
        "SELECT n.nspname,c.relname,a.attname,format_type(a.atttypid,a.atttypmod),"
        "a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid) "
        "FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum "
        "WHERE c.relkind IN ('r','p','v','m','S') AND a.attnum>0 AND NOT a.attisdropped "
        "AND n.nspname !~ '^pg_' AND n.nspname <> 'information_schema' "
        "AND NOT (n.nspname='app' AND c.relname=%s) ORDER BY n.nspname,c.relname,a.attnum",
        (RECEIPT_TABLE,),
    ))
    constraints = list(connection.execute(
        "SELECT n.nspname,c.relname,k.conname,pg_get_constraintdef(k.oid) "
        "FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema' "
        "AND NOT (n.nspname='app' AND c.relname=%s) ORDER BY n.nspname,c.relname,k.conname",
        (RECEIPT_TABLE,),
    ))
    triggers = list(connection.execute(
        "SELECT n.nspname,c.relname,t.tgname,pg_get_triggerdef(t.oid) "
        "FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE NOT t.tgisinternal AND n.nspname !~ '^pg_' "
        "AND n.nspname <> 'information_schema' ORDER BY n.nspname,c.relname,t.tgname"
    ))
    indexes = list(connection.execute(
        "SELECT n.nspname,c.relname,i.relname,pg_get_indexdef(i.oid) "
        "FROM pg_index x JOIN pg_class c ON c.oid=x.indrelid "
        "JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema' "
        "AND NOT (n.nspname='app' AND c.relname=%s) ORDER BY n.nspname,c.relname,i.relname",
        (RECEIPT_TABLE,),
    ))
    views = list(connection.execute(
        "SELECT n.nspname,c.relname,pg_get_viewdef(c.oid) FROM pg_class c "
        "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('v','m') "
        "AND n.nspname !~ '^pg_' AND n.nspname <> 'information_schema' "
        "ORDER BY n.nspname,c.relname"
    ))
    functions = list(connection.execute(
        "SELECT n.nspname,p.proname,pg_get_functiondef(p.oid) FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE p.prokind IN ('f','p') AND n.nspname !~ '^pg_' "
        "AND n.nspname <> 'information_schema' AND NOT EXISTS (SELECT 1 FROM pg_depend d "
        "WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e') "
        "ORDER BY n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)"
    ))
    payload = {"columns": columns, "constraints": constraints, "triggers": triggers,
               "indexes": indexes, "views": views, "functions": functions}
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


def _table_fingerprint(connection, schema, name):
    relation = sql.Identifier(schema, name)
    keys = [row[0] for row in connection.execute(
        "SELECT a.attname FROM pg_index i JOIN pg_attribute a "
        "ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) "
        "WHERE i.indrelid=to_regclass(%s) AND i.indisprimary ORDER BY a.attnum",
        (relation.as_string(connection),),
    )]
    ordering = (sql.SQL(',').join(map(sql.Identifier, keys)) if keys
                else sql.SQL('row_to_json(t)::text COLLATE "C"'))
    query = sql.SQL("COPY (SELECT * FROM {} t ORDER BY {}) TO STDOUT (FORMAT binary)").format(
        relation, ordering,
    )
    digest = hashlib.sha256()
    with connection.cursor().copy(query) as stream:
        for block in stream:
            digest.update(block)
    count = connection.execute(sql.SQL("SELECT count(*) FROM {}").format(relation)).fetchone()[0]
    return {"rows": count, "sha256": digest.hexdigest()}


def inventory(connection):
    require_supported_catalog(connection)
    result = server_identity(connection)
    result["schemas"] = [row[0] for row in connection.execute(
        "SELECT nspname FROM pg_namespace WHERE nspname !~ '^pg_' "
        "AND nspname <> 'information_schema' ORDER BY nspname"
    )]
    result["schema_sha256"] = _schema_fingerprint(connection)
    result["tables"] = {schema + "." + name: _table_fingerprint(connection, schema, name)
                        for schema, name in tables(connection)}
    return result
