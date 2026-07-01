import pymysql
pymysql.install_as_MySQLdb()

# MySQL 8.x 호환: caching_sha2_password 인증 방식 대응
pymysql.converters.encoders[float] = pymysql.converters.escape_float
