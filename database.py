import os
import re
import sqlite3
import pymysql
from pymysql.cursors import DictCursor
import config

class DatabaseManager:
    def __init__(self):
        self.engine = config.DB_ENGINE
        self.host = config.DB_HOST
        self.port = config.DB_PORT
        self.user = config.DB_USER
        self.password = config.DB_PASSWORD
        self.database = config.DB_NAME
        self.sqlite_path = str(config.SQLITE_PATH)

    def set_config(self, engine=None, host=None, port=None, user=None, password=None, database=None):
        if engine: self.engine = engine.lower()
        if host: self.host = host
        if port: self.port = int(port)
        if user: self.user = user
        if password is not None: self.password = password
        if database: self.database = database

    def get_connection(self):
        if self.engine == 'auto':
            # Test if MySQL connects; if not, use SQLite
            test_m = self.test_connection(engine='mysql')
            if test_m['success']:
                self.engine = 'mysql'
            else:
                self.engine = 'sqlite'

        if self.engine == 'mysql':
            try:
                conn = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    charset='utf8mb4',
                    cursorclass=DictCursor,
                    autocommit=False
                )
                return conn
            except Exception as e:
                # Resilient fallback: fallback to sqlite so app stays up, but keep mysql config ready
                print(f"[!] Warning: MySQL connection error ({e}). Temporarily using SQLite fallback.")
                self.engine = 'sqlite'
                conn = sqlite3.connect(self.sqlite_path)
                conn.row_factory = sqlite3.Row
                return conn
        else:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn

    def test_connection(self, host=None, port=None, user=None, password=None, database=None, engine=None):
        engine = (engine or self.engine).lower()
        if engine == 'mysql':
            h = host if host is not None else self.host
            p = int(port) if port is not None else self.port
            u = user if user is not None else self.user
            pwd = password if password is not None else self.password
            db = database if database is not None else self.database
            try:
                conn = pymysql.connect(
                    host=h, port=p, user=u, password=pwd,
                    database=db if db else None,
                    connect_timeout=3
                )
                with conn.cursor() as cur:
                    cur.execute("SELECT VERSION()")
                    ver = cur.fetchone()[0]
                conn.close()
                return {"success": True, "engine": "mysql", "version": ver, "message": f"Connected to MySQL {ver} successfully"}
            except Exception as e:
                return {"success": False, "engine": "mysql", "error": str(e)}
        else:
            try:
                conn = sqlite3.connect(self.sqlite_path)
                cur = conn.cursor()
                cur.execute("SELECT sqlite_version()")
                ver = cur.fetchone()[0]
                conn.close()
                return {"success": True, "engine": "sqlite", "version": ver, "message": f"Connected to SQLite {ver} successfully"}
            except Exception as e:
                return {"success": False, "engine": "sqlite", "error": str(e)}

    def execute_query(self, sql, params=None, fetch='all', commit=False):
        """
        Universal query executor.
        Normalizes %s to ? when using SQLite.
        """
        conn = self.get_connection()
        try:
            if self.engine == 'mysql':
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    if commit:
                        conn.commit()
                        return cursor.lastrowid or cursor.rowcount
                    
                    if fetch == 'all':
                        res = cursor.fetchall()
                        # Convert dicts into standard serializable list
                        return list(res)
                    elif fetch == 'one':
                        return cursor.fetchone()
                    else:
                        return cursor.rowcount
            else: # sqlite
                sqlite_sql = sql
                # Convert MySQL specific functions / keywords to SQLite
                sqlite_sql = re.sub(r'%s', '?', sqlite_sql)
                sqlite_sql = re.sub(r'\bAUTO_INCREMENT\b', 'AUTOINCREMENT', sqlite_sql, flags=re.IGNORECASE)
                sqlite_sql = re.sub(r'\bNOW\(\)', "datetime('now')", sqlite_sql, flags=re.IGNORECASE)
                sqlite_sql = re.sub(r'\bCURRENT_TIMESTAMP\b', "datetime('now')", sqlite_sql, flags=re.IGNORECASE)

                cursor = conn.cursor()
                cursor.execute(sqlite_sql, params or ())
                if commit:
                    conn.commit()
                    last_id = cursor.lastrowid
                    row_count = cursor.rowcount
                    cursor.close()
                    conn.close()
                    return last_id or row_count

                if fetch == 'all':
                    rows = cursor.fetchall()
                    res = [dict(row) for row in rows]
                    cursor.close()
                    conn.close()
                    return res
                elif fetch == 'one':
                    row = cursor.fetchone()
                    res = dict(row) if row else None
                    cursor.close()
                    conn.close()
                    return res
                else:
                    cnt = cursor.rowcount
                    cursor.close()
                    conn.close()
                    return cnt
        except Exception as e:
            if self.engine == 'mysql':
                try: conn.rollback()
                except Exception: pass
            raise e
        finally:
            if self.engine == 'mysql':
                try: conn.close()
                except Exception: pass

    def execute_transaction(self, query_param_list):
        """
        Executes a sequence of queries inside a single atomic transaction.
        query_param_list: list of tuples (sql, params, fetch_last_id_into_var_name)
        """
        conn = self.get_connection()
        last_ids = {}
        try:
            if self.engine == 'mysql':
                with conn.cursor() as cursor:
                    for item in query_param_list:
                        sql = item[0]
                        params = list(item[1]) if item[1] else []
                        var_name = item[2] if len(item) > 2 else None

                        # Resolve any parameterized last_ids
                        for idx, p in enumerate(params):
                            if isinstance(p, str) and p.startswith('$'):
                                ref_var = p[1:]
                                if ref_var in last_ids:
                                    params[idx] = last_ids[ref_var]

                        cursor.execute(sql, tuple(params))
                        if var_name:
                            last_ids[var_name] = cursor.lastrowid
                    conn.commit()
                return {"success": True, "last_ids": last_ids}
            else: # sqlite
                cursor = conn.cursor()
                for item in query_param_list:
                    sql = item[0]
                    params = list(item[1]) if item[1] else []
                    var_name = item[2] if len(item) > 2 else None

                    # Translate %s to ?
                    sql = re.sub(r'%s', '?', sql)

                    for idx, p in enumerate(params):
                        if isinstance(p, str) and p.startswith('$'):
                            ref_var = p[1:]
                            if ref_var in last_ids:
                                params[idx] = last_ids[ref_var]

                    cursor.execute(sql, tuple(params))
                    if var_name:
                        last_ids[var_name] = cursor.lastrowid
                conn.commit()
                conn.close()
                return {"success": True, "last_ids": last_ids}
        except Exception as e:
            if self.engine == 'mysql':
                try: conn.rollback()
                except Exception: pass
            else:
                try: conn.rollback(); conn.close()
                except Exception: pass
            raise e
        finally:
            if self.engine == 'mysql':
                try: conn.close()
                except Exception: pass

    def get_tables(self):
        if self.engine == 'mysql':
            tables = self.execute_query("SHOW TABLES")
            key = f"Tables_in_{self.database}"
            res = []
            for t in tables:
                tname = list(t.values())[0]
                # Count rows
                cnt = self.execute_query(f"SELECT COUNT(*) AS c FROM `{tname}`", fetch='one')
                res.append({"name": tname, "rows": cnt['c'] if cnt else 0})
            return res
        else:
            tables = self.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            res = []
            for t in tables:
                tname = t['name']
                cnt = self.execute_query(f"SELECT COUNT(*) AS c FROM `{tname}`", fetch='one')
                res.append({"name": tname, "rows": cnt['c'] if cnt else 0})
            return res

    def get_table_schema(self, table_name):
        # Prevent SQL injection in table name
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '', table_name)
        if self.engine == 'mysql':
            return self.execute_query(f"DESCRIBE `{safe_name}`")
        else:
            cols = self.execute_query(f"PRAGMA table_info(`{safe_name}`)")
            formatted = []
            for c in cols:
                formatted.append({
                    "Field": c['name'],
                    "Type": c['type'],
                    "Null": 'NO' if c['notnull'] else 'YES',
                    "Key": 'PRI' if c['pk'] else '',
                    "Default": c['dflt_value']
                })
            return formatted

    def get_table_data(self, table_name, limit=50, offset=0):
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '', table_name)
        return self.execute_query(f"SELECT * FROM `{safe_name}` LIMIT {int(limit)} OFFSET {int(offset)}")

    def run_raw_sql(self, sql_query):
        """
        Executes raw SQL query from the Database Studio tab.
        Returns execution time, columns, rows, or affected count.
        """
        import time
        start_time = time.time()
        conn = self.get_connection()
        clean_sql = sql_query.strip().rstrip(';')

        is_select = clean_sql.upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'PRAGMA'))
        try:
            if self.engine == 'mysql':
                with conn.cursor() as cursor:
                    cursor.execute(clean_sql)
                    elapsed = round((time.time() - start_time) * 1000, 2)
                    if is_select:
                        rows = cursor.fetchall()
                        cols = [d[0] for d in cursor.description] if cursor.description else []
                        return {
                            "success": True,
                            "type": "SELECT",
                            "columns": cols,
                            "rows": list(rows),
                            "count": len(rows),
                            "time_ms": elapsed
                        }
                    else:
                        conn.commit()
                        return {
                            "success": True,
                            "type": "DML",
                            "affected_rows": cursor.rowcount,
                            "last_insert_id": cursor.lastrowid,
                            "time_ms": elapsed
                        }
            else: # sqlite
                cursor = conn.cursor()
                cursor.execute(clean_sql)
                elapsed = round((time.time() - start_time) * 1000, 2)
                if is_select:
                    rows = cursor.fetchall()
                    cols = [d[0] for d in cursor.description] if cursor.description else []
                    dict_rows = [dict(r) for r in rows]
                    conn.close()
                    return {
                        "success": True,
                        "type": "SELECT",
                        "columns": cols,
                        "rows": dict_rows,
                        "count": len(dict_rows),
                        "time_ms": elapsed
                    }
                else:
                    conn.commit()
                    aff = cursor.rowcount
                    last_id = cursor.lastrowid
                    conn.close()
                    return {
                        "success": True,
                        "type": "DML",
                        "affected_rows": aff,
                        "last_insert_id": last_id,
                        "time_ms": elapsed
                    }
        except Exception as e:
            if self.engine == 'mysql':
                try: conn.rollback()
                except Exception: pass
            return {"success": False, "error": str(e), "time_ms": round((time.time() - start_time) * 1000, 2)}
        finally:
            if self.engine == 'mysql':
                try: conn.close()
                except Exception: pass

db = DatabaseManager()
