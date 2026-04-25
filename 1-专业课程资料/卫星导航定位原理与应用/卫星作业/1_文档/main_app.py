"""
GNSS OrbitMaster - main_app.py
Required libraries: georinex, numpy, astropy, scipy, PyQt6

PyQt6 图形界面：提供文件管理、参数配置与结果展示。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from astropy.time import Time
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QDateTime
from PyQt6.QtGui import QAction, QFont, QLinearGradient, QPainter, QPixmap, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QDateTimeEdit,
)

from engine import PositioningEngine
from models import CalculationResult


class CalculationThread(QThread):
    """在后台线程运行解算任务，避免冻结GUI。"""

    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, engine: PositioningEngine, sv_id: str, epoch: Time, ephemeris_mode: str) -> None:
        super().__init__()
        self.engine = engine
        self.sv_id = sv_id
        self.epoch = epoch
        self.ephemeris_mode = ephemeris_mode

    def run(self) -> None:
        try:
            if self.ephemeris_mode == "Compare":
                results: List[CalculationResult] = []
                if not self.engine.has_broadcast():
                    raise RuntimeError("尚未加载广播星历，无法进行对比")
                if not self.engine.has_precise():
                    raise RuntimeError("尚未加载精密星历，无法进行对比")
                results.append(self.engine.get_position(self.sv_id, self.epoch, "Broadcast"))
                results.append(self.engine.get_position(self.sv_id, self.epoch, "Precise"))
            else:
                results = [self.engine.get_position(self.sv_id, self.epoch, self.ephemeris_mode)]
            self.results_ready.emit(results)
        except Exception as exc:  # noqa: BLE001 - 统一反馈
            self.error_occurred.emit(str(exc))


class MainWindow(QMainWindow):
    """GNSS OrbitMaster 主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GNSS OrbitMaster")
        self.resize(1400, 900)

        self.engine = PositioningEngine()
        self.calculation_thread: CalculationThread | None = None
        self.sample_dir = Path(__file__).parent / "sample_data"

        self._init_ui()
        self._init_menu()
        self._apply_theme()

    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(16, 12, 16, 12)
        central_layout.setSpacing(12)
        central_layout.addWidget(self._build_header())
        central_layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.statusBar().showMessage("欢迎使用 GNSS OrbitMaster")

    def _init_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        load_action = QAction("加载星历", self)
        load_action.triggered.connect(self._on_load_file)
        file_menu.addAction(load_action)

    # ------------------------------------------------------------------
    def _build_left_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        # 文件管理
        file_group = QGroupBox("星历文件管理")
        file_layout = QVBoxLayout(file_group)
        self.file_list = QListWidget()
        button_row = QHBoxLayout()
        self.load_button = QPushButton("加载文件")
        self.load_button.clicked.connect(self._on_load_file)
        self.remove_button = QPushButton("移除选中")
        self.remove_button.clicked.connect(self._on_remove_file)
        self.generate_button = QPushButton("生成示例数据")
        self.generate_button.clicked.connect(self._on_generate_samples)
        button_row.addWidget(self.load_button)
        button_row.addWidget(self.remove_button)
        button_row.addWidget(self.generate_button)
        file_layout.addWidget(self.file_list)
        file_layout.addLayout(button_row)
        layout.addWidget(file_group)

        # 计算参数
        param_group = QGroupBox("计算参数")
        param_layout = QVBoxLayout(param_group)
        self.sv_combo = QComboBox()
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setTimeSpec(Qt.TimeSpec.UTC)
        self.datetime_edit.setDateTime(QDateTime.currentDateTimeUtc())
        self.ephemeris_combo = QComboBox()
        self.ephemeris_combo.addItems(["Broadcast", "Precise", "Compare"])

        param_layout.addWidget(QLabel("卫星编号"))
        param_layout.addWidget(self.sv_combo)
        param_layout.addWidget(QLabel("计算时间 (UTC)"))
        param_layout.addWidget(self.datetime_edit)
        param_layout.addWidget(QLabel("星历类型"))
        param_layout.addWidget(self.ephemeris_combo)

        self.calculate_button = QPushButton("执行计算")
        self.calculate_button.setStyleSheet(
            "QPushButton { font-size: 17px; padding: 14px;"
            " background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #00d0ff, stop:1 #0078ff);"
            " color: #ffffff; font-weight: 700; letter-spacing: 1px; }"
            "QPushButton:disabled { background-color: #20334d; color: #6d7b8f; }"
        )
        self.calculate_button.clicked.connect(self._on_calculate)

        param_layout.addWidget(self.calculate_button)
        layout.addWidget(param_group)
        layout.addStretch(1)
        return container

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        logo = QLabel()
        logo.setPixmap(self._create_logo_pixmap())
        logo.setFixedSize(240, 80)
        logo.setScaledContents(True)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title_label = QLabel("GNSS OrbitMaster")
        title_font = QFont("Microsoft YaHei", 24, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #6ef0ff; letter-spacing: 1px;")

        tagline = QLabel("科研级GNSS广播/精密星历解算实验台")
        tagline.setFont(QFont("Microsoft YaHei", 14))
        tagline.setStyleSheet("color: #a8d8ff;")

        title_block.addWidget(title_label)
        title_block.addWidget(tagline)

        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(title_block)
        layout.addStretch(1)
        return header

    def _create_logo_pixmap(self) -> QPixmap:
        width, height = 240, 80
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        frame_gradient = QLinearGradient(0, 0, width, height)
        frame_gradient.setColorAt(0.0, QColor(0, 255, 214))
        frame_gradient.setColorAt(1.0, QColor(0, 136, 255))
        painter.setBrush(frame_gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, width - 1, height - 1, 22, 22)

        inner_color = QColor(8, 22, 40)
        painter.setBrush(inner_color)
        painter.drawRoundedRect(6, 6, width - 12, height - 12, 18, 18)

        orbit_pen = QColor(111, 240, 255)
        painter.setPen(orbit_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(width / 2 - 60), int(height / 2 - 25), 120, 50)
        painter.drawEllipse(int(width / 2 - 40), int(height / 2 - 12), 80, 24)

        painter.setPen(QColor(0, 194, 255))
        painter.setBrush(QColor(0, 194, 255))
        painter.drawEllipse(int(width / 2 + 30), int(height / 2 - 3), 10, 10)

        text_font = QFont("Orbitron", 26, QFont.Weight.Bold)
        painter.setFont(text_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "OM")

        painter.end()
        return pixmap

    def _build_right_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(["参数", "值", "单位", "星历类型"])
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.result_table)
        return container

    def _apply_theme(self) -> None:
        """应用科技风界面主题，统一配色与控件样式。"""
        self.setStyleSheet(
            """
            QMainWindow { background-color: #050f1d; }
            QWidget { font-family: 'Segoe UI', 'Microsoft YaHei'; color: #e5f0ff; font-size: 15px; }
            QGroupBox { border: 1px solid #133955; border-radius: 10px; margin-top: 12px; background-color: #0a1d33; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #6edcff; }
            QListWidget, QTableWidget, QComboBox, QDateTimeEdit { background-color: #061224; border: 1px solid #133955; border-radius: 6px; selection-background-color: #1f4c88; font-size: 15px; }
            QPushButton { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1b8ef2, stop:1 #00c2ff); color: #ffffff; border: none; border-radius: 8px; padding: 12px; font-weight: 600; letter-spacing: 0.5px; font-size: 15px; }
            QPushButton:hover { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3ea4ff, stop:1 #15e0ff); }
            QPushButton:disabled { background-color: #253348; color: #98a9c6; }
            QSplitter::handle { background-color: #0f2742; width: 3px; }
            QHeaderView::section { background-color: #0f2742; color: #8fd6ff; border: none; padding: 6px; }
            QTableWidget { gridline-color: #132641; alternate-background-color: #0d1b2f; font-size: 15px; }
            QStatusBar { background-color: #040b15; color: #7dd9ff; }
            QLabel { color: #8fd6ff; font-weight: 500; font-size: 15px; }
            QComboBox QAbstractItemView { selection-background-color: #1f4c88; }
            """
        )
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setShowGrid(False)
        self.result_table.setStyleSheet(
            self.result_table.styleSheet()
            + "QTableWidget::item { padding: 4px; }"
        )
        self.statusBar().setStyleSheet("border-top: 1px solid #133955;")

    # ------------------------------------------------------------------
    def _on_load_file(self) -> None:
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilters(["NAV 文件 (*.nav *.rnx *.??n)", "SP3 文件 (*.sp3)", "所有文件 (*.*)"])
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_path = dialog.selectedFiles()[0]
            try:
                result = self.engine.load_ephemeris(file_path)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "加载失败", str(exc))
                return
            self._add_loaded_file_entry(file_path, result)

    def _on_remove_file(self) -> None:
        current_row = self.file_list.currentRow()
        if current_row >= 0:
            self.file_list.takeItem(current_row)
            self.statusBar().showMessage("已移除文件记录（不会卸载缓存）", 5000)

    def _add_loaded_file_entry(self, file_path: str, result: dict, announce: bool = True) -> None:
        QListWidgetItem(f"{result['type']}: {file_path}", self.file_list)
        self._refresh_satellites()
        if announce:
            self.statusBar().showMessage(
                f"已加载 {len(result['satellites'])} 颗卫星 ({result['type']})", 5000
            )

    def _on_generate_samples(self) -> None:
        try:
            self.sample_dir.mkdir(parents=True, exist_ok=True)
            nav_path = self.sample_dir / "orbitmaster_sample.nav"
            sp3_path = self.sample_dir / "orbitmaster_sample.sp3"

            nav_path.write_text(self._sample_nav_content(), encoding="ascii")
            sp3_path.write_text(self._sample_sp3_content(), encoding="ascii")

            summaries = []
            for path in (nav_path, sp3_path):
                result = self.engine.load_ephemeris(str(path))
                self._add_loaded_file_entry(str(path), result, announce=False)
                summaries.append(f"{result['type']} -> {path.name}")

            self.statusBar().showMessage("示例星历已生成并加载", 5000)
            QMessageBox.information(
                self,
                "示例数据已就绪",
                "\n".join(["已生成以下数据：", *summaries]),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "生成失败", str(exc))

    def _sample_nav_content(self) -> str:
        epoch = datetime.now(timezone.utc).replace(microsecond=0)
        year, month, day = epoch.year, epoch.month, epoch.day
        hour, minute, second = epoch.hour, epoch.minute, epoch.second

        header = [
            "     3.05           N: GPS NAV DATA     RINEX VERSION / TYPE",
            "GNSS OrbitMaster   Built-in Generator  {:>02d}-{:>02d}-{:>02d} 00:00     PGM / RUN BY / DATE".format(
                year % 100, month, day
            ),
            "                                                            END OF HEADER",
        ]

        def record(sv: str, af0: float, af1: float, af2: float, m0: float, delta_n: float, ecc: float) -> str:
            template = (
                "{sv} {year:4d} {month:2d} {day:2d} {hour:2d} {minute:2d} {second:2d}"
                "{af0:19.12E}{af1:19.12E}{af2:19.12E}\n"
                "    1.0000000000E+02  1.8000000000E+02 {delta_n: .10E}{m0: .10E}\n"
                "    1.2000000000E-05  3.5000000000E-03  1.7000000000E-05  5.1537000000E+03\n"
                "    1.4400000000E+04  2.5000000000E-07  2.0000000000E-01  3.0000000000E-07\n"
                "    {ecc: .10E}  2.3000000000E+02  3.0000000000E-01 -8.0000000000E-09\n"
                "    1.0000000000E-09  0.0000000000E+00  2.3000000000E+03  0.0000000000E+00\n"
                "    2.0000000000E+00  0.0000000000E+00 -5.0000000000E-09  5.0000000000E+01\n"
                "    2.1600000000E+05  4.0000000000E+00  0.0000000000E+00  0.0000000000E+00\n"
            )
            return template.format(
                sv=sv,
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=second,
                af0=af0,
                af1=af1,
                af2=af2,
                delta_n=delta_n,
                m0=m0,
                ecc=ecc,
            )

        body = [
            record("G01", -1.2732925820e-04, 5.4569682106e-12, 0.0, 1.2, 4.0e-09, 0.01),
            record("G02", 2.1234567890e-04, -1.4551915228e-11, 0.0, 2.3, 4.2e-09, 0.015),
        ]
        return "\n".join(header + body)

    def _sample_sp3_content(self) -> str:
        epoch = datetime.now(timezone.utc)
        next_epoch = epoch + timedelta(minutes=15)
        epoch_line = epoch.strftime("* %Y %m %d %H %M %S.%f")[:-3]
        next_line = next_epoch.strftime("* %Y %m %d %H %M %S.%f")[:-3]

        lines = [
            "#cP{:4d} {:02d} {:02d} {:02d} {:02d} {:02d}.00000000".format(
                epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute, epoch.second
            ),
            "## 2300 86400.00000000 900.000000000000 0 0 0 0 0 0 0",
            "+   2 G01 G02",
            "%c cc cc cc cc cc cc cc cc cc cc",
            "%f  0.0  0.0  0.0  0.0  0.0",
            "%i       0",
            epoch_line,
            "PG01   15600.123456   20150.654321   21300.789123   0.000000",
            "PG02   17800.654321   19050.321654   20200.123987   0.000000",
            next_line,
            "PG01   15605.223456   20155.754321   21305.889123   0.000000",
            "PG02   17805.754321   19055.421654   20205.223987   0.000000",
            "EOF",
        ]
        return "\n".join(lines)

    def _on_calculate(self) -> None:
        sv_id = self.sv_combo.currentText()
        if not sv_id:
            QMessageBox.warning(self, "缺少参数", "请先加载星历并选择卫星")
            return

        dt = self.datetime_edit.dateTime().toPyDateTime()
        epoch = Time(dt, scale="utc")
        mode = self.ephemeris_combo.currentText()

        if mode == "Broadcast" and not self.engine.has_broadcast():
            QMessageBox.warning(self, "未加载", "请先加载广播星历文件")
            return
        if mode == "Precise" and not self.engine.has_precise():
            QMessageBox.warning(self, "未加载", "请先加载精密星历文件")
            return
        if mode == "Compare" and (not self.engine.has_broadcast() or not self.engine.has_precise()):
            QMessageBox.warning(self, "未加载", "需同时加载广播与精密星历")
            return

        self.calculate_button.setEnabled(False)
        self.statusBar().showMessage("正在计算，请稍候...")
        self.calculation_thread = CalculationThread(self.engine, sv_id, epoch, mode)
        self.calculation_thread.results_ready.connect(self._on_results_ready)
        self.calculation_thread.error_occurred.connect(self._on_calculation_error)
        self.calculation_thread.finished.connect(lambda: self.calculate_button.setEnabled(True))
        self.calculation_thread.start()

    def _on_results_ready(self, results: List[CalculationResult]) -> None:
        self._populate_results(results)
        self.statusBar().showMessage("计算完成", 5000)

    def _on_calculation_error(self, message: str) -> None:
        QMessageBox.critical(self, "计算失败", message)
        self.statusBar().showMessage("计算失败", 5000)

    def _populate_results(self, results: List[CalculationResult]) -> None:
        total_rows = sum(5 if res.success else 1 for res in results)
        self.result_table.setRowCount(total_rows)
        row = 0
        for result in results:
            dataset = (
                [
                    ("卫星ID", result.sv, ""),
                    ("计算时间", result.epoch.utc.iso, "UTC"),
                    ("X坐标", f"{result.x:.3f}", "m"),
                    ("Y坐标", f"{result.y:.3f}", "m"),
                    ("Z坐标", f"{result.z:.3f}", "m"),
                ]
                if result.success
                else [("错误", result.error_message or "未知错误", "")]
            )
            for label, value, unit in dataset:
                self.result_table.setItem(row, 0, QTableWidgetItem(label))
                self.result_table.setItem(row, 1, QTableWidgetItem(value))
                self.result_table.setItem(row, 2, QTableWidgetItem(unit))
                self.result_table.setItem(row, 3, QTableWidgetItem(result.ephemeris_type))
                row += 1
        self.result_table.resizeRowsToContents()

    def _refresh_satellites(self) -> None:
        satellites = self.engine.list_satellites()
        self.sv_combo.clear()
        self.sv_combo.addItems(satellites)


def main() -> None:
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        # Qt5 提供的旧属性在 Qt6 中可能不存在，需兼容处理
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
