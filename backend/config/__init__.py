"""Use PyMySQL as the MySQLdb driver so we avoid the mysqlclient C build on Windows.

Django's mysql backend rejects driver versions below 1.4.3, so we spoof PyMySQL's
reported version before installing it. Harmless when the DB engine is sqlite.
"""

import pymysql

pymysql.version_info = (1, 4, 6, "final", 0)
pymysql.install_as_MySQLdb()
