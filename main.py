#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Isaac Lab 训练工具 - 主程序入口"""

import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Isaac Lab Train Tool")
    app.setApplicationVersion("1.1.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()