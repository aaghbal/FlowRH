"""
init.py
"""

# Django's MySQL backend imports `MySQLdb`, which is the C driver mysqlclient.
# It is the faster of the two drivers, so it wins when it is installed; PyMySQL
# stands in for it otherwise, since it is pure python and needs no build
# toolchain. Nothing happens here on SQLite or Postgres.
try:  # pragma: no cover - depends on which driver is installed
    import MySQLdb  # noqa: F401
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass

from horilla import (
    haystack_configuration,
    horilla_apps,
    horilla_context_processors,
    horilla_middlewares,
    horilla_settings,
    rest_conf,
)
