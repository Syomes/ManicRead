from nicegui import ui, app
from fastapi import Query
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime
from data_fetch import DataBase
from ui_show import UIRenderer
import os
import glob

db_path = os.path.expanduser("~/.config/manictime/ManicTimeReports.db")
db = DataBase(db_path)
renderer = UIRenderer(db)

# 加载 Highcharts 模块
ui.add_css("""
    @keyframes fade-out {
        from {
           opacity: 0;
        }
        to {
           opacity: 1;
        }
    }
""")

ui.add_head_html("""
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highcharts/11.4.3/highcharts.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highcharts/11.4.3/highcharts-more.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highcharts/11.4.3/modules/xrange.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highcharts/11.4.3/modules/exporting.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highcharts/11.4.3/modules/accessibility.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
""")

@app.get('/api/screenshot')
def get_screenshot(date: str = Query(...), time: str = Query(...)):
    """
    date = "YYYY-MM-DD", time = "HH-MM"
    """
    pattern = f"{date}_{time}*.jpg"
    screenshot_dir = os.path.expanduser(f"~/.config/manictime/Screenshots/{date}/")
    minute_prefix = time[:5]  # 只取 HH-MM，构造模糊匹配
    pattern = f"{date}_{minute_prefix}-*.jpg"
    candidate_paths = glob.glob(os.path.join(screenshot_dir, pattern))

    if not candidate_paths:
        return None

    # 提取出每个文件对应的时间戳，选出与目标最接近的
    if len(time.split("-")) == 2:
        time_full = time + "-00"
    else:
        time_full = time

    target_time = datetime.strptime(time_full, "%H-%M-%S")

    def extract_seconds(path):
        parts = os.path.basename(path).split("_")
        if len(parts) < 2:
            return float('inf')
        try:
            t = datetime.strptime(parts[1], "%H-%M-%S")
            return abs((t - target_time).total_seconds())
        except:
            return float('inf')

    nearest_path = min(candidate_paths, key=extract_seconds)
    if nearest_path is None:
        return JSONResponse(status_code=404, content={"message": "No matching screenshot found"})

    return FileResponse(nearest_path, media_type="image/jpeg")

renderer.create_interface()

ui.run(title='ManicRead')