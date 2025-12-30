#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OKX Grid Trading Bot - 启动入口

使用方法:
    python run.py                    # 启动智能版（默认，带市场分析和风控）
    python run.py --basic            # 启动基础版网格机器人
    python run.py --analyze          # 仅运行市场分析
    python run.py --non-interactive  # 非交互模式，遇到异常直接退出
    python run.py --yes              # 非交互模式下自动确认所有提示
    python run.py --help             # 显示帮助
"""
import sys
import os
import io
import argparse

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    """打印启动横幅（基础版使用）"""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║           OKX 网格量化交易机器人  v2.0 (基础版)               ║
    ║                                                               ║
    ║  注意: 量化交易有风险，请用可承受损失的资金进行测试          ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='OKX Grid Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # 运行模式
    parser.add_argument('--basic', action='store_true',
                        help='启动基础版网格机器人')
    parser.add_argument('--analyze', action='store_true',
                        help='仅运行市场分析，不进行交易')

    # 非交互模式参数
    parser.add_argument('--non-interactive', action='store_true',
                        help='非交互模式，遇到异常情况直接退出')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='非交互模式下自动确认所有提示')

    # P0-5: 实盘交易互锁保护
    parser.add_argument('--live', action='store_true',
                        help='⚠️ 启用实盘交易（必须显式指定，否则仅分析模式）')

    args = parser.parse_args()

    # 设置全局非交互模式标志
    os.environ['NON_INTERACTIVE'] = '1' if args.non_interactive else '0'
    os.environ['AUTO_YES'] = '1' if args.yes else '0'

    # P0-5: 实盘保护 - 未指定 --live 且非模拟盘时，强制启用仅分析模式
    use_simulated = os.getenv("USE_SIMULATED", "False").lower() == "true"
    if not args.live and not use_simulated and not args.analyze:
        print("\n" + "=" * 70)
        print("  ⚠️  实盘交易保护")
        print("=" * 70)
        print("  检测到实盘模式但未指定 --live 标志")
        print("  为防止误操作，已自动启用【仅分析模式】")
        print("  ")
        print("  如需实盘交易，请使用: python run.py --live")
        print("=" * 70 + "\n")
        os.environ['ANALYZE_ONLY'] = '1'

    # analyze模式自动启用ANALYZE_ONLY硬锁
    if args.analyze:
        # 在import config前设置环境变量
        os.environ['ANALYZE_ONLY'] = '1'
        # 仅运行分析
        from okx_grid_bot.analysis.macro_analysis import macro_analyzer
        print("\n" + "=" * 60)
        print("         市 场 分 析 模 式")
        print("=" * 60 + "\n")
        result = macro_analyzer.analyze_market()
        macro_analyzer.print_analysis_report(result)

    elif args.basic:
        # 启动基础版
        print_banner()
        from okx_grid_bot.bot import GridBot
        bot = GridBot()
        bot.start()

    else:
        # 默认启动智能版（带市场分析和风控）
        from okx_grid_bot.smart_bot import SmartGridBot
        bot = SmartGridBot()
        bot.start()


if __name__ == '__main__':
    main()
