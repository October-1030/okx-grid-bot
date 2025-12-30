#!/usr/bin/env python
"""
OKX Grid Trading Bot - 启动入口

使用方法:
    python run.py           # 启动基础版网格机器人
    python run.py --smart   # 启动智能版（带市场分析）
    python run.py --analyze # 仅运行市场分析
    python run.py --help    # 显示帮助
"""
import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    """打印启动横幅"""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║           OKX 网格量化交易机器人  v2.0                        ║
    ║                                                               ║
    ║  使用方法:                                                    ║
    ║    python run.py           启动基础版网格机器人               ║
    ║    python run.py --smart   启动智能版（带市场分析）           ║
    ║    python run.py --analyze 仅运行市场分析                     ║
    ║                                                               ║
    ║  注意: 量化交易有风险，请用可承受损失的资金进行测试          ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)


def main():
    """主函数"""
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == '--help' or arg == '-h':
            print(__doc__)
            return

        elif arg == '--smart':
            # 启动智能版
            from okx_grid_bot.smart_bot import SmartGridBot
            bot = SmartGridBot()
            bot.start()

        elif arg == '--analyze':
            # 仅运行分析
            from okx_grid_bot.analysis.macro_analysis import macro_analyzer
            print("\n" + "=" * 60)
            print("         市 场 分 析 模 式")
            print("=" * 60 + "\n")
            result = macro_analyzer.analyze_market()
            macro_analyzer.print_analysis_report(result)

        else:
            print(f"未知参数: {arg}")
            print("使用 python run.py --help 查看帮助")
    else:
        # 默认启动基础版
        print_banner()
        from okx_grid_bot.bot import GridBot
        bot = GridBot()
        bot.start()


if __name__ == '__main__':
    main()
