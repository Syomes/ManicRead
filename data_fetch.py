from datetime import datetime
import sqlite3

class DataBase():
    def __init__(self, data_path):
        self.db_path = data_path

    def load_data(self, date_str):
        """
        用于查找指定日期的数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 映射 CommonGroupId 到分组名称
        cursor.execute("SELECT CommonId, Name FROM Ar_CommonGroup")
        common_map = dict(cursor.fetchall())
        cursor.execute("SELECT CommonId, Color FROM Ar_CommonGroup")
        color_map = dict(cursor.fetchall())

        # 提取活动记录，包括原始标题
        cursor.execute("""
            SELECT CommonGroupId, StartLocalTime, EndLocalTime, StartUtcTime, Name
            FROM Ar_Activity
            WHERE CommonGroupId IS NOT NULL AND StartLocalTime LIKE ? AND EndLocalTime IS NOT NULL
        """, (f"{date_str}%",))
        rows = cursor.fetchall()
        conn.close()

        segments = []
        usage = {}
        utc_offset = 0

        for gid, start, end, utc_start, raw_title in rows:
            title = common_map.get(gid, "(unknown window)")
            color = "#" + color_map.get(gid, "000000")
            t1 = datetime.fromisoformat(start)
            t2 = datetime.fromisoformat(end)
            utc_t1 = datetime.fromisoformat(utc_start)
            utc_offset = (t1 - utc_t1).total_seconds() // 3600
            if t2 > t1:
                segments.append((title, int(t1.timestamp() * 1000), int(t2.timestamp() * 1000), raw_title, color))
                duration = (t2 - t1).total_seconds() / 3600  # 转换为小时
            else:
                duration = 0

            if title in usage:
                usage[title]['total_usage'] += duration
            else:
                usage[title] = { 'total_usage': duration, 'color': color }

        return segments, usage, utc_offset

    
    def load_lock_data(self, date_str):
        """
        用于查找指定日期的无活动记录
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 精选 Ar_Group 中名称为 'Away' 和 'Session lock' 的 GroupId
        cursor.execute("SELECT GroupId, Name FROM Ar_Group WHERE Name IN ('Away', 'Session lock')")
        special_gid_map = dict(cursor.fetchall())
        cursor.execute("SELECT GroupId, Color FROM Ar_Group WHERE Name IN ('Away', 'Session lock')")
        special_color_map = dict(cursor.fetchall())

        if special_gid_map:
            placeholder = ",".join(["?"] * len(special_gid_map))
            cursor.execute(f"""
                SELECT GroupId, StartLocalTime, EndLocalTime
                FROM Ar_Activity
                WHERE GroupId IN ({placeholder}) AND StartLocalTime LIKE ? AND EndLocalTime IS NOT NULL AND CommonGroupId IS NULL
            """, list(special_gid_map.keys()) + [f"{date_str}%"])

            special_rows = cursor.fetchall()
            segments = []

            for gid, start, end in special_rows:
                name = special_gid_map.get(gid, "(special)")
                color = "#" + special_color_map.get(gid, "000000")
                try:
                    t1 = datetime.fromisoformat(start)
                    t2 = datetime.fromisoformat(end)
                    if t2 > t1:
                        segments.append((name, int(t1.timestamp() * 1000), int(t2.timestamp() * 1000), '', color)) # 空字符串代表空 title
                except Exception:
                    continue
        return segments
    
    def load_data_range(self, start_date_str, end_date_str):
        """
        用于查找指定日期范围内的数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT CommonId, Name FROM Ar_CommonGroup")
        common_map = dict(cursor.fetchall())
        cursor.execute("SELECT CommonId, Color FROM Ar_CommonGroup")
        color_map = dict(cursor.fetchall())
        cursor.execute("""
            SELECT CommonGroupId, StartLocalTime, EndLocalTime
            FROM Ar_Activity
            WHERE CommonGroupId IS NOT NULL
            AND EndLocalTime IS NOT NULL
            AND StartLocalTime BETWEEN ? AND ?
        """, (f"{start_date_str} 00:00:00", f"{end_date_str} 23:59:59"))
        rows = cursor.fetchall()
        conn.close()

        usage = {}

        for gid, start, end in rows:
            title = common_map.get(gid, "(unknown window)")
            color = "#" + color_map.get(gid, "000000")
            t1 = datetime.fromisoformat(start)
            t2 = datetime.fromisoformat(end)
            
            if t2 > t1:
                duration = (t2 - t1).total_seconds() / 3600  # 转换为小时
            else:
                duration = 0

            if title in usage:
                usage[title]['total_usage'] += duration
            else:
                usage[title] = {'total_usage': duration, 'color': color}
        return usage

    def get_available_dates(self):
        """
        有数据的日期列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT substr(StartLocalTime, 1, 10) AS date
            FROM Ar_Activity
            WHERE CommonGroupId IS NOT NULL AND EndLocalTime IS NOT NULL
        """)
        rows = cursor.fetchall()
        conn.close()
        return {row[0] for row in rows}