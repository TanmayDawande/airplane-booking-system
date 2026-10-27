"""MySQL data-access layer.

The project deliberately uses one database so that the Flask app and MySQL
Workbench always show the same rows. All connections use the ``airline_db``
schema and the IST session timezone.
"""

import re
import time

import pymysql
from pymysql.cursors import DictCursor

import config


class DatabaseManager:
    def __init__(self):
        self.engine = 'mysql'
        self.host = config.DB_HOST
        self.port = config.DB_PORT
        self.user = config.DB_USER
        self.password = config.DB_PASSWORD
        self.database = config.DB_NAME

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------
    def get_connection(self):
        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=5,
            read_timeout=15,
            write_timeout=15,
        )
        # Make CURRENT_TIMESTAMP / triggers write IST instead of UTC.
        with conn.cursor() as cursor:
            cursor.execute("SET time_zone = %s", (config.TIMEZONE_OFFSET,))
        return conn

    def test_connection(self, host=None, port=None, user=None, password=None,
                        database=None, engine=None):
        h = host if host is not None else self.host
        p = int(port) if port is not None else self.port
        u = user if user is not None else self.user
        pwd = password if password is not None else self.password
        db = database if database is not None else self.database
        try:
            conn = pymysql.connect(
                host=h,
                port=p,
                user=u,
                password=pwd,
                database=db,
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=5,
            )
            with conn.cursor() as cursor:
                cursor.execute("SET time_zone = %s", (config.TIMEZONE_OFFSET,))
                cursor.execute(
                    "SELECT VERSION() AS version, "
                    "@@session.time_zone AS tz, NOW() AS server_now"
                )
                row = cursor.fetchone()
            conn.close()
            return {
                "success": True,
                "engine": "mysql",
                "version": row['version'],
                "time_zone": row['tz'],
                "server_now": row['server_now'],
                "message": f"Connected to MySQL {row['version']} ({db})",
            }
        except Exception as exc:
            return {"success": False, "engine": "mysql", "error": str(exc)}

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------
    def execute_query(self, sql, params=None, fetch='all', commit=False):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                if commit:
                    conn.commit()
                    return cursor.lastrowid or cursor.rowcount
                if fetch == 'all':
                    return list(cursor.fetchall())
                if fetch == 'one':
                    return cursor.fetchone()
                return cursor.rowcount
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def execute_transaction(self, query_param_list):
        """Run a sequence of (sql, params[, save_last_id_as]) statements."""
        conn = self.get_connection()
        last_ids = {}
        try:
            with conn.cursor() as cursor:
                for item in query_param_list:
                    sql = item[0]
                    params = list(item[1]) if item[1] else []
                    var_name = item[2] if len(item) > 2 else None

                    for index, value in enumerate(params):
                        if isinstance(value, str) and value.startswith('$'):
                            ref = value[1:]
                            if ref not in last_ids:
                                raise RuntimeError(
                                    f"Transaction reference {ref!r} is not available."
                                )
                            params[index] = last_ids[ref]

                    cursor.execute(sql, tuple(params))
                    if var_name:
                        last_ids[var_name] = cursor.lastrowid
                conn.commit()
            return {"success": True, "last_ids": last_ids}
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Schema browsing (used by the SQL Studio)
    # ------------------------------------------------------------------
    def get_tables(self):
        rows = self.execute_query(
            """
            SELECT table_name AS name, table_type AS type
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (self.database,),
        )
        result = []
        for row in rows:
            name = row['name']
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '', name)
            count_row = self.execute_query(
                f"SELECT COUNT(*) AS c FROM `{safe_name}`", fetch='one'
            )
            result.append({
                "name": name,
                "type": row['type'],
                "rows": count_row['c'] if count_row else 0,
            })
        return result

    def get_table_schema(self, table_name):
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '', table_name)
        return self.execute_query(f"DESCRIBE `{safe_name}`")

    def get_table_data(self, table_name, limit=50, offset=0):
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '', table_name)
        return self.execute_query(
            f"SELECT * FROM `{safe_name}` LIMIT %s OFFSET %s",
            (int(limit), int(offset)),
        )

    def run_raw_sql(self, sql_query):
        start = time.perf_counter()
        conn = self.get_connection()
        clean_sql = sql_query.strip().rstrip(';')
        is_select = clean_sql.upper().startswith(
            ('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'WITH', 'CALL')
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(clean_sql)
                elapsed = round((time.perf_counter() - start) * 1000, 2)
                if is_select and cursor.description:
                    rows = list(cursor.fetchall())
                    columns = [column[0] for column in cursor.description]
                    return {
                        "success": True,
                        "type": "SELECT",
                        "columns": columns,
                        "rows": rows,
                        "count": len(rows),
                        "time_ms": elapsed,
                    }
                conn.commit()
                return {
                    "success": True,
                    "type": "DML",
                    "affected_rows": cursor.rowcount,
                    "last_insert_id": cursor.lastrowid,
                    "time_ms": elapsed,
                }
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            return {
                "success": False,
                "error": str(exc),
                "time_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass


db = DatabaseManager()
