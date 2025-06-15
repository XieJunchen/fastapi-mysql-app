import sqlite3
import os
import re
import json
import csv
import io

# 获取项目根目录下 test.db 的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'test.db')
SQLITE_SQL_PATH = os.path.join(BASE_DIR, 'all_data_sqlite.sql')
MYSQL_SQL_PATH = os.path.join(BASE_DIR, 'all_data_mysql.sql')

def fix_json_inserts(line):
    # 只做语法兼容，不对字段内容做任何替换，直接返回原始 line
    return line

def sqlite_to_mysql(sqlite_line):
    line = sqlite_line
    # CREATE TABLE 语句加 IF NOT EXISTS
    if line.strip().startswith('CREATE TABLE'):
        line = line.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS', 1)
        line = re.sub(r'"([^"]+)"', r'`\1`', line)
        # 修正 text(N) 为 TEXT
        line = re.sub(r'TEXT\s*\(\s*\d+\s*\)', 'TEXT', line, flags=re.IGNORECASE)
        return line
    # INSERT 语句：表名用反引号，字段内容全部用双引号，且内容中的换行符替换为 \\n
    if line.strip().startswith('INSERT INTO'):
        line = re.sub(r'INSERT INTO "([^"]+)"', r'INSERT INTO `\1`', line)
        def single_to_double_and_escape_newline(m):
            content = m.group(1)
            # 替换内容中的换行符为 \\n
            content = content.replace('\\', '\\\\')  # 先转义反斜杠
            content = content.replace('\n', '\\n').replace('\r', '\\r')
            content = content.replace('\r\n', '\\n')
            content = content.replace('\n', '\\n').replace('\r', '\\r')
            content = content.replace('\u2028', '').replace('\u2029', '')
            content = content.replace('\t', '\\t')
            content = content.replace('\"', '"')  # 防止多重转义
            content = content.replace('"', '\\"')  # 转义双引号
            content = content.replace("'", "''")  # 单引号转义为两个单引号
            # 最终用双引号包裹
            return '"' + content + '"'
        # 用正则替换所有单引号包裹的字段内容为双引号，并处理换行
        line = re.sub(r"'((?:[^'\\]|\\.)*)'", single_to_double_and_escape_newline, line)
        return line
    # 其它结构语句做必要的 SQL 语法转换
    line = re.sub(r'AUTOINCREMENT', 'AUTO_INCREMENT', line)
    line = re.sub(r'INTEGER PRIMARY KEY', 'INT PRIMARY KEY AUTO_INCREMENT', line)
    line = re.sub(r'"([^"]+)"', r'`\1`', line)
    # 修正 text(N) 为 TEXT
    line = re.sub(r'TEXT\s*\(\s*\d+\s*\)', 'TEXT', line, flags=re.IGNORECASE)
    line = line.replace("''", "''")
    if 'BEGIN TRANSACTION' in line or 'COMMIT' in line:
        return ''
    if 'sqlite_sequence' in line:
        return ''
    line = line.replace('WITHOUT ROWID', '')
    line = re.sub(r'BOOLEAN', 'TINYINT(1)', line, flags=re.IGNORECASE)
    line = re.sub(r'DATETIME', 'DATETIME', line, flags=re.IGNORECASE)
    line = re.sub(r'TEXT', 'TEXT', line, flags=re.IGNORECASE)
    line = re.sub(r'BLOB', 'LONGBLOB', line, flags=re.IGNORECASE)
    line = line.replace('IF NOT EXISTS', '')
    # 修正 JSON 字段
    line = fix_json_inserts(line)
    return line

def export_sqlite_and_mysql(db_path, sqlite_sql_path, mysql_sql_path):
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    print(f"数据库文件存在: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        with open(sqlite_sql_path, 'w', encoding='utf-8') as f_sqlite, \
             open(mysql_sql_path, 'w', encoding='utf-8') as f_mysql:
            f_mysql.write('SET NAMES utf8mb4;\n')
            for line in conn.iterdump():
                f_sqlite.write(f'{line}\n')
                mysql_line = sqlite_to_mysql(line)
                if mysql_line.strip():
                    f_mysql.write(f'{mysql_line}\n')
        conn.close()
        print(f'导出完成：\n- SQLite: {sqlite_sql_path}\n- MySQL: {mysql_sql_path}')
    except Exception as e:
        print(f"导出失败: {e}")

if __name__ == '__main__':
    export_sqlite_and_mysql(DB_PATH, SQLITE_SQL_PATH, MYSQL_SQL_PATH)
