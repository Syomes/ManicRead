from nicegui import ui
from datetime import datetime, date
import json
# from nicegui_toolkit import inject_layout_tool
# inject_layout_tool()

class UIRenderer():
    def __init__(self, db):
        self.db = db
        self.daily_total_statistics_container = None
        self.period_total_statistics_container = None
        self.inited = False # 只是用来看另一个tab是否加载
        pass

    def count_animate(self, label, h, m, s):
        """
        统计时长的增长动画
        """
        from time import time
        start = time()
        duration = 1.5  # 动画时长（秒）
        def update(h=h, m=m, s=s):
            now = time()
            t = min((now - start) / duration, 1.0)
            # 使用 ease-out 缓动函数
            t = 1 - (1 - t) ** 3
            cur_seconds = int(t * (h * 3600 + m * 60 + s))
            h = cur_seconds // 3600
            m = (cur_seconds % 3600) // 60
            s = cur_seconds % 60
            label.text = f"{h:02d}:{m:02d}:{s:02d}"
            if t < 1.0:
                ui.timer(0.02, update, once=True)
            else:
                label.text = f"{h:02d}:{m:02d}:{s:02d}"
        update()
    
    def daily_render(self, date_str=str(date.today())):
        common_segments, usage_all, offset = self.db.load_data(date_str)
        lock_segments = self.db.load_lock_data(date_str)
        segments = common_segments + lock_segments

        # 合并相邻同名且时间连续的 segments
        merged_segments = []
        for seg in segments:
            if merged_segments and seg[0] == merged_segments[-1][0] and seg[1] == merged_segments[-1][2]:
                # 合并：更新end_ms
                merged_segments[-1] = (merged_segments[-1][0], merged_segments[-1][1], seg[2], seg[3], seg[4])
            else:
                merged_segments.append(seg)
        segments = merged_segments

        if self.daily_total_statistics_container:
            with self.daily_total_statistics_container:
                self.daily_total_statistics_container.clear()
                with ui.card().style('align-self: stretch; height: 100%;'):
                    ui.label("Usage Summary").classes('text-h6').style('align-self: center;')
                    # 依 total_usage 降序排序
                    sorted_usage = sorted([(title, data) for title, data in usage_all.items()], key=lambda x: x[1]["total_usage"], reverse=True)

                    for title, data in sorted_usage:
                        total_usage = data["total_usage"]
                        hours = int(total_usage)
                        minutes = int((total_usage - hours) * 60)
                        seconds = int(((total_usage - hours) * 60 - minutes) * 60)
                        with ui.row().style('align-self: end'):
                            ui.label('■').style(f'color: {data["color"]}; margin-right: -10px;')
                            ui.label(f"{title}:").classes('ml-4').style('align-self: end; margin-left: 0; margin-right: -10px;')
                            label = ui.label(f"00:00:00").classes('ml-4').style('align-self: end; margin-left: 0;')
                            self.count_animate(label, hours, minutes, seconds)

        if not segments:
            date_str = ''

        data = [
            {
                'x': start_ms,
                'x2': end_ms,
                'y': 0,
                'name': title,
                'color': color,
                'rawTitle': raw_title
            }
            for title, start_ms, end_ms, raw_title, color in segments
        ]

        chart_data = json.dumps(data, ensure_ascii=False)
        categories = json.dumps([""], ensure_ascii=False)

        ui.run_javascript(f"""
            let chart = null;
            let hoveredPoint = null;
            let lastCursorTime = null;
            const screenshot_container = document.getElementById('daily-screenshot-container');
            function initChart(data, date_str) {{
                chart = Highcharts.chart('daily-gantt-graph', {{
                    time: {{
                        timezoneOffset: {-offset} * 60
                    }},
                    chart: {{ type: 'xrange', zoomType: 'x', height: 200 }},
                    title: {{ text: date_str + ' timeline' }},
                    xAxis: {{
                        type: 'datetime',
                        title: {{ text: 'time' }},
                        labels: {{ format: '{{value:%H:%M}}' }}
                    }},
                    yAxis: {{
                        categories: {categories},
                        reversed: true,
                        tickInterval: 1,
                        title: null,
                        labels: {{ enabled: false }},
                        gridLineWidth: 0
                    }},
                    tooltip: {{
                        useHTML: true,
                        formatter: function() {{
                            let cursorTimeStr = '';
                            if (lastCursorTime !== null) {{
                                cursorTimeStr = '<br><b>current time:</b> ' + Highcharts.dateFormat('%H:%M:%S', lastCursorTime);
                            }}
                            return '<b>' + this.point.name + '</b><br>' +
                                Highcharts.dateFormat('%H:%M:%S', this.point.x) +
                                ' → ' + Highcharts.dateFormat('%H:%M:%S', this.point.x2) +
                                cursorTimeStr;
                        }},
                        positioner: function(labelWidth, labelHeight, point) {{
                            // point.plotX/plotY 是相对于绘图区的坐标
                            return {{
                                x: point.plotX + this.chart.plotLeft - labelWidth / 2,
                                y: point.plotY + this.chart.plotTop - labelHeight
                            }};
                        }}
                    }},
                    plotOptions: {{
                        series: {{
                            point: {{
                                events: {{
                                    mouseOver: function() {{
                                        hoveredPoint = this;
                                    }},
                                    mouseOut: function() {{
                                        hoveredPoint = null;
                                        lastCursorTime = null;
                                    }}
                                }}
                            }}
                        }}
                    }},
                    series: [{{
                        name: 'activities',
                        data: {chart_data}
                    }}],
                    navigator: {{
                        enabled: true
                    }},
                    scrollbar: {{
                        enabled: true
                    }},
                    rangeSelector: {{
                        enabled: true
                    }}
                }});
                chart.container.addEventListener('mousemove', function(e) {{
                    if (hoveredPoint) {{
                        const rawTitle = hoveredPoint?.rawTitle;
                        const rect = chart.container.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const axisValue = chart.xAxis[0].toValue(x, false);
                        lastCursorTime = axisValue;
                        chart.tooltip.refresh(hoveredPoint); // 强制刷新tooltip
                        
                        // 插入懒加载图片
                        screenshot_container.innerHTML = `
                            <div style="font-size: 20px;">${{rawTitle}}</div>
                            <img src="/api/screenshot?date={date_str}&time=${{Highcharts.dateFormat('%H-%M-%S', lastCursorTime)}}" 
                                loading="lazy"
                                onerror="this.style.display='none'; this.remove();">
                        `;
                    }}
                }});
                Highcharts.setOptions({{
                    time: {{
                        timezoneOffset: {-offset} * 60
                    }}
                }});
            }}
        
            if (chart) {{
                chart.series[0].setData({chart_data});
            }} else {{
                initChart({chart_data}, '{date_str}');
            }}
        """)

    def period_render(self, start_date_str=None, end_date_str=None):
        if not start_date_str or not end_date_str and not self.inited:
            start_date_str = str(datetime.now().replace(day=1).date())
            end_date_str = str(datetime.now().date())
    
        self.inited = True

        usage_all = self.db.load_data_range(start_date_str, end_date_str)
    
        # 依时长从高到低排序，过滤低于 0.01 小时程式
        sorted_usage = sorted([(title, data) for title, data in usage_all.items()], key=lambda x: x[1]["total_usage"], reverse=True)[:10]
        categories_list = [title for title, _ in sorted_usage]
        categories = json.dumps(categories_list, ensure_ascii=False)
        series_data = [
            {
                "y": round(data["total_usage"], 2),
                "color": data["color"],
                "name": app
            }
            for app, data in sorted_usage
        ]
        chart_data = json.dumps(series_data, ensure_ascii=False)
    
        ui.run_javascript(f"""
            window.periodChart = Highcharts.chart('period-gantt-graph', {{
                chart: {{
                    type: 'column', height: 500
                }},
                title: {{
                    text: '{start_date_str} to {end_date_str} Usage Statistics'
                }},
                xAxis: {{
                    categories: {categories},
                    labels: {{
                        rotation: -45,
                        style: {{
                            fontSize: '12px'
                        }}
                    }}
                }},
                yAxis: {{
                    title: {{
                        text: 'Hours'
                    }}
                }},
                tooltip: {{
                    formatter: function() {{
                        return '<span style="color:' + this.point.color + '">\u25CF</span> ' +
                            '<b>' + this.point.name + '</b><br/>' +
                            this.y.toFixed(2) + ' hours';
                    }}
                }},
                plotOptions: {{
                    column: {{
                        dataLabels: {{
                            enabled: true,
                            format: '{'{point.y:.2f}'}'
                        }}
                    }}
                }},
                series: [{{
                    name: 'Total Usage',
                    data: {chart_data},
                    colorByPoint: false
                }}]
            }});
        """)

    def daily_chart_update(self, e):
        date_str = e.value
        self.daily_render(date_str)

    def period_chart_update(self, e):
        if type(e.value) is dict:
            start_date_str = e.value['from']
            end_date_str = e.value['to']
        elif type(e.value) is str:
            start_date_str = e.value
            end_date_str = e.value
        else:
            start_date_str = None
            end_date_str = None
        self.period_render(start_date_str, end_date_str)

    def create_interface(self):
        with ui.header(elevated=True).style('background-color: #3874c8; padding-top: 2px; padding-bottom: 2px;').classes('items-center justify-between'):
            ui.label('ManicRead').style('font-size: 24px; font-weight: bold;')
            with ui.tabs(on_change=lambda e: self.period_render() if e.value == 'Period' else None) as tabs:
                ui.tab('Daily', icon='schedule').props('no-caps style="font-size: 10px;"')
                ui.tab('Period', icon='equalizer').props('no-caps style="font-size: 10px;"')

        # 页面创建
        with ui.tab_panels(tabs, value='Daily').style('align-self: stretch;'):
            with ui.tab_panel('Daily'):
                with ui.column().style('align-self: stretch;'):
                    with ui.button(icon='calendar_month').props('round flat color="white').tooltip('Select a date'):
                        with ui.menu():
                            formatted_dates = {datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y/%m/%d") for date_str in self.db.get_available_dates()}
                            ui.date(value=date.today(), on_change=self.daily_chart_update).style('align-self: center;').props(f'''options="{formatted_dates}"''')

                    ui.card().style('align-self: stretch;').props('id=daily-gantt-graph') # 图像显示容器
                    with ui.row().style('align-self: stretch; animation: fade-out 1s ease forwards'):
                        with ui.card().style('min-width: 60%; max-width: 60%; align-self: stretch;'):
                            ui.label('Details').classes('text-h6').style('align-self: center;')
                            ui.element().props('id=daily-screenshot-container')   # 对应时间点截图容器
                        self.daily_total_statistics_container = ui.element().style('flex: 1; align-self: stretch;')  # 当日时长总统计容器

                    # 初次进入渲染当天数据
                    ui.timer(0.1, self.daily_render, once=True)

            with ui.tab_panel('Period'):
                with ui.column().style('align-self: stretch;'):
                    with ui.button(icon='calendar_month').props('round flat color="white').tooltip('Select a date'):
                        with ui.menu():
                            ui.date({'from': str(datetime.now().replace(day=1).date()), 'to': str(datetime.now().date())}, on_change=self.period_chart_update).style('align-self: center;').props('range')
                    
                    ui.card().style('align-self: stretch;').props('id=period-gantt-graph') # 阶段时长总统计容器