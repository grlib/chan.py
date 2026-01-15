"""
使用pyecharts绘制缠论分析图
支持多级别（1F, 5F, 30F, 日线, 周线, 月线）的笔、线段、中枢可视化
"""
from typing import Dict, List, Optional, Union

from pyecharts import options as opts
from pyecharts.charts import Graph, Kline, Line, Scatter
from pyecharts.commons.utils import JsCode
from pyecharts.globals import ThemeType
from pyecharts.options import GraphicItem, GraphicRect

from Chan import CChan
from Common.CEnum import KL_TYPE
from Plot.PlotMeta import CChanPlotMeta


class CPyEchartsPlotDriver:
    """使用pyecharts绘制缠论分析图"""
    
    # 颜色配置（按照图片要求）
    COLORS = {
        'orange': '#FFA500',      # 橙色
        'yellow': '#FFFF00',      # 黄色
        'light_blue': '#87CEEB',  # 浅蓝
        'red': '#FF0000',         # 红色
        'green': '#00FF00',       # 绿色
        'dark_blue': '#00008B',   # 深蓝
        'purple': '#800080',      # 紫色
        'dark_green': '#006400',  # 深绿
    }
    
    # 级别名称映射
    LEVEL_NAMES = {
        KL_TYPE.K_1M: '1F',
        KL_TYPE.K_3M: '3F',
        KL_TYPE.K_5M: '5F',
        KL_TYPE.K_15M: '15F',
        KL_TYPE.K_30M: '30F',
        KL_TYPE.K_60M: '60F',
        KL_TYPE.K_DAY: '日线',
        KL_TYPE.K_WEEK: '周线',
        KL_TYPE.K_MON: '月线',
        KL_TYPE.K_QUARTER: '季线',
        KL_TYPE.K_YEAR: '年线',
    }
    
    # 级别颜色配置（笔、线段、中枢）
    LEVEL_COLORS = {
        KL_TYPE.K_1M: {
            'bi': '#87CEEB',    # 浅蓝
            'seg': '#FF0000',   # 红色
            'zs': '#00FF00',    # 绿色
        },
        KL_TYPE.K_3M: {
            'bi': '#00008B',    # 深蓝
            'seg': '#800080',   # 紫色
            'zs': '#FFA500',    # 橙色
        },
        KL_TYPE.K_5M: {
            'bi': '#FFFF00',    # 黄色
            'seg': '#006400',   # 深绿
            'zs': '#FF0000',    # 红色
        },
        KL_TYPE.K_15M: {
            'bi': '#00FF00',    # 绿色
            'seg': '#FFA500',   # 橙色
            'zs': '#800080',    # 紫色
        },
        KL_TYPE.K_30M: {
            'bi': '#87CEEB',    # 浅蓝
            'seg': '#FF0000',   # 红色
            'zs': '#00FF00',    # 绿色
        },
        KL_TYPE.K_60M: {
            'bi': '#00008B',    # 深蓝
            'seg': '#800080',   # 紫色
            'zs': '#FFA500',    # 橙色
        },
        KL_TYPE.K_DAY: {
            'bi': '#FF0000',    # 红色
            'seg': '#00FF00',   # 绿色
            'zs': '#00008B',    # 深蓝
        },
        KL_TYPE.K_WEEK: {
            'bi': '#FFA500',    # 橙色
            'seg': '#800080',   # 紫色
            'zs': '#FFFF00',    # 黄色
        },
        KL_TYPE.K_MON: {
            'bi': '#006400',    # 深绿
            'seg': '#87CEEB',   # 浅蓝
            'zs': '#FF0000',    # 红色
        },
        KL_TYPE.K_QUARTER: {
            'bi': '#800080',    # 紫色
            'seg': '#FFA500',   # 橙色
            'zs': '#00FF00',    # 绿色
        },
        KL_TYPE.K_YEAR: {
            'bi': '#00008B',    # 深蓝
            'seg': '#006400',   # 深绿
            'zs': '#FFFF00',    # 黄色
        },
    }
    
    def get_level_colors(self, kl_type: KL_TYPE) -> Dict[str, str]:
        """
        获取指定级别的颜色配置
        
        Args:
            kl_type: K线级别
            
        Returns:
            包含bi、seg、zs颜色的字典
        """
        # 如果级别不在配置中，使用默认颜色
        default_colors = {
            'bi': self.COLORS['dark_blue'],
            'seg': self.COLORS['green'],
            'zs': self.COLORS['orange'],
        }
        return self.LEVEL_COLORS.get(kl_type, default_colors)
    
    def __init__(
        self,
        chan: CChan,
        plot_config: Union[str, dict, list] = '',
        plot_para: Optional[dict] = None
    ):
        """
        初始化绘图驱动
        
        Args:
            chan: CChan实例，包含缠论分析数据
            plot_config: 绘图配置
            plot_para: 绘图参数
        """
        self.chan = chan
        self.plot_config = plot_config or {}
        self.plot_para = plot_para or {}
        
        # 获取所有级别的元数据
        self.plot_metas: Dict[KL_TYPE, CChanPlotMeta] = {}
        for kl_type in chan.lv_list:
            self.plot_metas[kl_type] = CChanPlotMeta(chan[kl_type])
    
    def plot_multi_level_structure(self, output_path: str = "chan_analysis.html"):
        """
        绘制多级别缠论结构图（按照图片要求）
        显示不同时间周期下的笔、线段、中枢的层级关系
        采用阶梯状布局：每个级别横向排列笔、线段、中枢，不同级别纵向排列
        """
        # 创建Graph图表
        graph = Graph(init_opts=opts.InitOpts(
            width="1600px",
            height="1000px",
            theme=ThemeType.MACARONS
        ))
        
        # 构建节点和边
        nodes = []
        links = []
        
        # 为每个级别分配颜色（按照图片中的颜色顺序）
        level_colors = [
            self.COLORS['orange'],
            self.COLORS['yellow'],
            self.COLORS['light_blue'],
            self.COLORS['red'],
            self.COLORS['green'],
            self.COLORS['dark_blue'],
        ]
        
        # 布局参数
        base_x = 150  # 起始X坐标
        base_y = 100  # 起始Y坐标（从上往下）
        element_spacing_x = 180  # 同一级别内元素间距（笔、线段、中枢）
        level_spacing_y = 140  # 不同级别纵向间距
        
        # 存储每个级别的节点位置信息
        level_positions = {}
        
        for idx, kl_type in enumerate(self.chan.lv_list):
            level_name = self.LEVEL_NAMES.get(kl_type, str(kl_type))
            color = level_colors[idx % len(level_colors)]
            
            # 计算当前级别的Y坐标（从上往下排列）
            current_y = base_y + idx * level_spacing_y
            
            # 笔节点位置
            # 如果idx>0，笔的位置对齐上一级别的线段位置（向右下方偏移）
            if idx > 0:
                prev_seg_x = level_positions[idx - 1]['seg']['x']
                bi_x = prev_seg_x
            else:
                bi_x = base_x
            
            bi_y = current_y
            
            # 线段节点位置
            # 如果idx>0，线段的位置对齐上一级别的中枢位置（向右下方偏移）
            if idx > 0:
                prev_zs_x = level_positions[idx - 1]['zs']['x']
                seg_x = prev_zs_x
            else:
                seg_x = bi_x + element_spacing_x
            
            seg_y = current_y
            
            # 中枢节点位置（在当前级别内，线段右侧）
            zs_x = seg_x + element_spacing_x
            zs_y = current_y
            
            # 保存位置信息
            level_positions[idx] = {
                'bi': {'x': bi_x, 'y': bi_y},
                'seg': {'x': seg_x, 'y': seg_y},
                'zs': {'x': zs_x, 'y': zs_y}
            }
            
            # 创建笔节点
            bi_node_id = f"{level_name}_笔"
            nodes.append({
                "id": bi_node_id,
                "name": f"{level_name}\n笔",
                "symbolSize": 60,
                "category": idx,
                "itemStyle": {"color": color, "borderColor": "#333", "borderWidth": 2},
                "label": {"show": True, "fontSize": 16, "fontWeight": "bold"},
                "x": bi_x,
                "y": bi_y,
            })
            
            # 创建线段节点
            seg_node_id = f"{level_name}_线段"
            nodes.append({
                "id": seg_node_id,
                "name": f"{level_name}\n线段",
                "symbolSize": 70,
                "category": idx,
                "itemStyle": {"color": color, "borderColor": "#333", "borderWidth": 2},
                "label": {"show": True, "fontSize": 16, "fontWeight": "bold"},
                "x": seg_x,
                "y": seg_y,
            })
            
            # 创建中枢节点
            zs_node_id = f"{level_name}_中枢"
            nodes.append({
                "id": zs_node_id,
                "name": f"{level_name}\n中枢",
                "symbolSize": 80,
                "category": idx,
                "itemStyle": {"color": color, "borderColor": "#333", "borderWidth": 2},
                "label": {"show": True, "fontSize": 16, "fontWeight": "bold"},
                "x": zs_x,
                "y": zs_y,
            })
            
            # 在同一级别内连接笔->线段->中枢（实线）
            links.append({
                "source": bi_node_id,
                "target": seg_node_id,
                "lineStyle": {"color": color, "width": 3, "type": "solid"}
            })
            links.append({
                "source": seg_node_id,
                "target": zs_node_id,
                "lineStyle": {"color": color, "width": 3, "type": "solid"}
            })
            
            # 连接不同级别（虚线）
            if idx > 0:
                prev_level = self.chan.lv_list[idx - 1]
                prev_level_name = self.LEVEL_NAMES.get(prev_level, str(prev_level))
                
                # 当前级别的笔 -> 上一级别的线段（虚线）
                links.append({
                    "source": bi_node_id,
                    "target": f"{prev_level_name}_线段",
                    "lineStyle": {
                        "color": self.COLORS['purple'],
                        "width": 2,
                        "type": "dashed",
                        "opacity": 0.6
                    }
                })
                
                # 当前级别的线段 -> 上一级别的中枢（虚线）
                links.append({
                    "source": seg_node_id,
                    "target": f"{prev_level_name}_中枢",
                    "lineStyle": {
                        "color": self.COLORS['purple'],
                        "width": 2,
                        "type": "dashed",
                        "opacity": 0.6
                    }
                })
        
        # 设置图表选项
        graph.add(
            "",
            nodes,
            links,
            repulsion=8000,
            gravity=0.1,
            layout="none",  # 使用固定布局
            linestyle_opts=opts.LineStyleOpts(curve=0.2),
            label_opts=opts.LabelOpts(is_show=True, position="inside"),
            categories=[
                {"name": self.LEVEL_NAMES.get(kl_type, str(kl_type))}
                for kl_type in self.chan.lv_list
            ]
        )
        
        graph.set_global_opts(
            title_opts=opts.TitleOpts(
                title=f"{self.chan.code} 缠论多级别结构分析",
                subtitle="笔 -> 线段 -> 中枢 层级关系图（实线：同级关系，虚线：跨级关系）",
                pos_left="center",
                title_textstyle_opts=opts.TextStyleOpts(font_size=20, font_weight="bold")
            ),
            legend_opts=opts.LegendOpts(
                is_show=True,
                pos_top="5%",
                pos_left="center"
            ),
        )
        
        # 保存图表
        graph.render(output_path)
        return graph
    
    def plot_kline_with_bi_seg_zs(self, kl_type: KL_TYPE, output_path: Optional[str] = None):
        """
        绘制指定级别的K线图，包含笔、线段、中枢
        
        Args:
            kl_type: K线级别
            output_path: 输出路径，如果为None则使用默认路径
        """
        if kl_type not in self.plot_metas:
            raise ValueError(f"级别 {kl_type} 不在数据中")
        
        meta = self.plot_metas[kl_type]
        level_name = self.LEVEL_NAMES.get(kl_type, str(kl_type))
        
        if output_path is None:
            output_path = f"chan_{self.chan.code}_{level_name}.html"
        
        # 准备K线数据
        kline_data = []
        dates = []
        
        for klu in meta.klu_iter():
            dates.append(klu.time.to_str())
            kline_data.append([klu.open, klu.close, klu.low, klu.high])
        
        # 创建K线图
        kline_chart = (
            Kline(init_opts=opts.InitOpts(width="1400px", height="600px"))
            .add_xaxis(dates)
            .add_yaxis(
                "K线",
                kline_data,
                itemstyle_opts=opts.ItemStyleOpts(
                    color="#ec0000",
                    color0="#00da3c",
                    border_color="#8A0000",
                    border_color0="#008F28",
                ),
            )
        )
        
        # 获取当前级别的颜色配置
        level_colors = self.get_level_colors(kl_type)
        
        # 创建Line图用于叠加笔和线段
        line_chart = Line()
        line_chart.add_xaxis(dates)
        
        # 添加笔（使用级别对应的颜色）
        if meta.bi_list:
            for bi in meta.bi_list:
                if bi.begin_x < len(dates) and bi.end_x < len(dates) and bi.begin_x != bi.end_x:
                    # 创建笔的数据点，只包含起点和终点，中间填充None
                    bi_data = [None] * len(dates)
                    bi_data[bi.begin_x] = bi.begin_y
                    bi_data[bi.end_x] = bi.end_y
                    
                    line_chart.add_yaxis(
                        "",  # 空名称，不在图例中显示
                        bi_data,
                        is_connect_nones=True,  # 允许连接None值，这样能正确绘制线段
                        linestyle_opts=opts.LineStyleOpts(
                            color=level_colors['bi'],  # 使用级别对应的笔颜色
                            width=2.5,  # 笔的线宽
                            type_="solid" if bi.is_sure else "dashed"
                        ),
                        label_opts=opts.LabelOpts(is_show=False),
                        symbol="circle",
                        symbol_size=4,  # 笔的端点大小
                        is_symbol_show=True,
                        z_level=1,  # 确保笔在K线上方
                        tooltip_opts=opts.TooltipOpts(is_show=False),  # 禁用笔的tooltip
                    )
        
        # 添加线段（使用级别对应的颜色）
        if meta.seg_list:
            for seg in meta.seg_list:
                if seg.begin_x < len(dates) and seg.end_x < len(dates) and seg.begin_x != seg.end_x:
                    # 创建线段的数据点
                    seg_data = [None] * len(dates)
                    seg_data[seg.begin_x] = seg.begin_y
                    seg_data[seg.end_x] = seg.end_y
                    
                    line_chart.add_yaxis(
                        "",  # 空名称，不在图例中显示
                        seg_data,
                        is_connect_nones=True,  # 允许连接None值
                        linestyle_opts=opts.LineStyleOpts(
                            color=level_colors['seg'],  # 使用级别对应的线段颜色
                            width=4,  # 线段比笔更粗，突出显示
                            type_="solid" if seg.is_sure else "dashed"
                        ),
                        label_opts=opts.LabelOpts(is_show=False),
                        symbol="circle",
                        symbol_size=5,  # 线段端点更大
                        is_symbol_show=True,
                        z_level=2,  # 确保线段在笔的上方
                        tooltip_opts=opts.TooltipOpts(is_show=False),  # 禁用线段的tooltip
                    )
        
        # 合并图表
        kline_chart.overlap(line_chart)
        
        # 添加中枢（使用Line图绘制矩形边框，不填充）
        if meta.zs_lst:
            zs_border_chart = Line()
            zs_border_chart.add_xaxis(dates)
            
            for zs in meta.zs_lst:
                if zs.begin < len(dates) and zs.end < len(dates):
                    zs_color = level_colors['zs']
                    
                    # 绘制矩形的四条边
                    # 上边（水平线）
                    top_data = [None] * len(dates)
                    top_data[zs.begin] = zs.high
                    top_data[zs.end] = zs.high
                    zs_border_chart.add_yaxis(
                        "",
                        top_data,
                        is_connect_nones=True,
                        linestyle_opts=opts.LineStyleOpts(
                            color=zs_color,
                            width=2,
                            type_="solid"
                        ),
                        label_opts=opts.LabelOpts(is_show=False),
                        symbol="none",
                        tooltip_opts=opts.TooltipOpts(is_show=False),  # 禁用tooltip
                    )
                    
                    # 下边（水平线）
                    bottom_data = [None] * len(dates)
                    bottom_data[zs.begin] = zs.low
                    bottom_data[zs.end] = zs.low
                    zs_border_chart.add_yaxis(
                        "",
                        bottom_data,
                        is_connect_nones=True,
                        linestyle_opts=opts.LineStyleOpts(
                            color=zs_color,
                            width=2,
                            type_="solid"
                        ),
                        label_opts=opts.LabelOpts(is_show=False),
                        symbol="none",
                        tooltip_opts=opts.TooltipOpts(is_show=False),  # 禁用tooltip
                    )
                    
                    # 左边（垂直线）- 使用两个非常接近的点来绘制垂直线
                    # 由于Line图限制，我们在begin位置使用low，在begin+1位置使用high
                    left_data = [None] * len(dates)
                    if zs.begin < len(dates):
                        left_data[zs.begin] = zs.low
                        # 使用下一个点来绘制垂直线
                        next_idx = min(zs.begin + 1, len(dates) - 1)
                        if next_idx != zs.begin:
                            left_data[next_idx] = zs.high
                    
                    zs_border_chart.add_yaxis(
                        "",
                        left_data,
                        is_connect_nones=True,
                        linestyle_opts=opts.LineStyleOpts(
                            color=zs_color,
                            width=2,
                            type_="solid"
                        ),
                        label_opts=opts.LabelOpts(is_show=False),
                        symbol="none",
                        tooltip_opts=opts.TooltipOpts(is_show=False),  # 禁用tooltip
                    )
                    
                    # 右边（垂直线）
                    right_data = [None] * len(dates)
                    if zs.end < len(dates):
                        right_data[zs.end] = zs.low
                        # 使用下一个点来绘制垂直线
                        next_idx = min(zs.end + 1, len(dates) - 1)
                        if next_idx != zs.end:
                            right_data[next_idx] = zs.high
                    
                    zs_border_chart.add_yaxis(
                        "",
                        right_data,
                        is_connect_nones=True,
                        linestyle_opts=opts.LineStyleOpts(
                            color=zs_color,
                            width=2,
                            type_="solid"
                        ),
                        label_opts=opts.LabelOpts(is_show=False),
                        symbol="none",
                        tooltip_opts=opts.TooltipOpts(is_show=False),  # 禁用tooltip
                    )
            
            # 合并中枢边框图表
            kline_chart.overlap(zs_border_chart)
        
        kline_chart.set_global_opts(
            title_opts=opts.TitleOpts(
                title=f"{self.chan.code} {level_name} 缠论分析",
                subtitle="K线 + 笔 + 线段 + 中枢"
            ),
            xaxis_opts=opts.AxisOpts(is_scale=True),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=True,
                    type_="inside",
                    xaxis_index=[0, 0],
                    range_start=0,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    pos_top="97%",
                    range_start=0,
                    range_end=100,
                ),
            ],
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                # 只显示K线的tooltip，过滤掉笔、线段、中枢的tooltip
                formatter=JsCode("""
                    function(params) {
                        // 只显示K线数据的tooltip
                        var result = params[0].name + '<br/>';
                        for (var i = 0; i < params.length; i++) {
                            if (params[i].seriesName === 'K线' && params[i].value) {
                                var data = params[i].value;
                                result += '开盘: ' + data[0] + '<br/>';
                                result += '收盘: ' + data[1] + '<br/>';
                                result += '最低: ' + data[2] + '<br/>';
                                result += '最高: ' + data[3] + '<br/>';
                                break;
                            }
                        }
                        return result;
                    }
                """)
            ),
            legend_opts=opts.LegendOpts(
                is_show=False,  # 不显示图例，避免显示"笔x"标签
            ),
        )
        
        kline_chart.render(output_path)
        return kline_chart
    
    def plot_all_levels(self, output_dir: str = "./"):
        """
        绘制所有级别的K线图
        
        Args:
            output_dir: 输出目录
        """
        charts = {}
        for kl_type in self.chan.lv_list:
            level_name = self.LEVEL_NAMES.get(kl_type, str(kl_type))
            output_path = f"{output_dir}chan_{self.chan.code}_{level_name}.html"
            charts[kl_type] = self.plot_kline_with_bi_seg_zs(kl_type, output_path)
        
        # 同时生成多级别结构图
        structure_path = f"{output_dir}chan_{self.chan.code}_structure.html"
        charts['structure'] = self.plot_multi_level_structure(structure_path)
        
        return charts
