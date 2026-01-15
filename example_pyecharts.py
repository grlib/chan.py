"""
使用pyecharts绘制缠论分析图的示例
"""
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.PyEchartsPlotDriver import CPyEchartsPlotDriver

if __name__ == "__main__":
    code = "sh.000001"
    begin_time = "2023-12-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    
    # 设置多个级别（从高到低）
    lv_list = [
        KL_TYPE.K_DAY,      # 30分钟
    ]

    config = CChanConfig({
        "bi_strict": True,
        "trigger_step": False,
        "skip_step": 0,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": '1,2,3a,1p,2s,3b',
        "print_warning": True,
        "zs_algo": "normal",
    })

    # 创建CChan实例
    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    print(f"数据加载完成: {chan.code}")
    print(f"级别列表: {[lv.name for lv in chan.lv_list]}")
    
    # 创建pyecharts绘图驱动
    plot_driver = CPyEchartsPlotDriver(chan)
    
    # 方法1: 绘制多级别结构图（按照图片要求）
    print("正在生成多级别结构图...")
    structure_chart = plot_driver.plot_multi_level_structure("chan_structure.html")
    print("多级别结构图已保存到: chan_structure.html")
    
    # 方法2: 绘制指定级别的K线图（包含笔、线段、中枢）
    print("正在生成各级别K线图...")
    for kl_type in chan.lv_list:
        level_name = plot_driver.LEVEL_NAMES.get(kl_type, str(kl_type))
        output_path = f"chan_{code}_{level_name}.html"
        chart = plot_driver.plot_kline_with_bi_seg_zs(kl_type, output_path)
        print(f"{level_name}级别K线图已保存到: {output_path}")
    
    # 方法3: 一次性绘制所有级别
    print("正在生成所有级别的图表...")
    charts = plot_driver.plot_all_levels("./")
    print("所有图表已生成完成！")
    
    print("\n使用说明:")
    print("1. 打开 chan_structure.html 查看多级别结构关系图")
    print("2. 打开 chan_*_*.html 查看各级别的K线分析图")
    print("3. 图表支持交互：缩放、拖拽、悬停查看详情")
