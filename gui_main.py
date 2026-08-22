import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QSlider, QLabel
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg


def _dominant_component_indices_for_summary(composition_profile, Rmax=None):
    if not composition_profile:
        return []

    if Rmax is not None:
        i_rmax = min(
            range(len(composition_profile)),
            key=lambda i: abs(composition_profile[i][0] - Rmax)
        )
        state = composition_profile[i_rmax][1]
    else:
        state = composition_profile[-2][1] if len(composition_profile) > 1 else composition_profile[-1][1]

    active = [idx for idx, value in enumerate(state) if value > 1e-12]
    if not active:
        return []

    max_value = max(state[idx] for idx in active)
    threshold = max_value - 0.05
    dominant = sorted(idx for idx in active if state[idx] >= threshold)
    if not dominant:
        dominant = [max(active, key=lambda idx: state[idx])]
    return dominant


def select_main_components(composition_profile, Rmax):
    """
    Determine the dominant purified component indices from the final non-pure
    summary row, so degenerate mixtures do not get assigned a single hard-coded
    index or a component that belongs on the impurity plot.
    """
    if not composition_profile:
        return [], [], None, None

    i_Rmax = min(
        range(len(composition_profile)),
        key=lambda i: abs(composition_profile[i][0] - Rmax)
    )
    i_zero = len(composition_profile) - 1

    n_components = len(composition_profile[0][1])
    main_components = _dominant_component_indices_for_summary(composition_profile, Rmax)
    if not main_components:
        main_components = [
            max(range(n_components), key=lambda idx: composition_profile[-2][1][idx])
            if len(composition_profile) > 1 else 0
        ]

    impurity_components = [
        k for k in range(n_components)
        if k not in main_components and any(row[1][k] > 1e-12 for row in composition_profile)
    ]

    # print("[GUI] i_Rmax", i_Rmax)
    # print("[GUI] i_zero", i_zero)
    # print("[GUI] main_components", main_components)
    # print("[GUI] impurity_components", impurity_components)

    return main_components, impurity_components, i_Rmax, i_zero




class MainWindow(QMainWindow):
    """
    Main GUI window containing:
    - Component 1 plot
    - Impurity plot
    - RelSolVol plot
    - Recovery slider
    """

    _active_window = None

    @staticmethod
    def _impurity_colors(count):
        if count <= 0:
            return []

        palette = [
            "red", "green", "orange", "purple", "cyan", "yellow",
            "magenta", "lime", "brown", "pink", "teal", "gold",
            "darkRed", "darkGreen", "darkBlue", "darkOrange",
        ]
        if count <= len(palette):
            return palette[:count]

        colors = []
        for idx in range(count):
            hue = idx / max(count, 1)
            colors.append(pg.mkColor((hue, 0.7, 0.8)).name())
        return colors

    class InfoPanel(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setWindowFlags(Qt.WindowType.Widget)
            layout = QVBoxLayout(self)
            self.label = QLabel()
            self.label.setStyleSheet("background: rgba(24, 24, 24, 80); color: white; border: 1px solid rgba(255, 255, 255, 80); padding: 6px;")
            layout.addWidget(self.label)

        def update_info(self, text):
            self.label.setText(text)

    class ProfilePlotWidget(QWidget):
        """
        Generic plot widget for:
        - Component 1 vs Recovery
        - Impurity profiles
        - RelSolVol
        """

        def __init__(self, title, x_label, y_label):
            super().__init__()
            layout = QVBoxLayout(self)

            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setTitle(title)
            self.plot_widget.setLabel("bottom", x_label)
            self.plot_widget.setLabel("left", y_label)
            self.plot_widget.invertX(True)
            self.plot_widget.setXRange(1, 0, padding=0)
            self.legend_text = pg.TextItem("", anchor=(1, 0))
            self.plot_widget.addItem(self.legend_text, ignoreBounds=True)
            self.legend_text.setColor("w")
            self.legend_text.setPos(1.0, 1.0)
            self.legend_text.setText(" ")
            self.Rmax_line = pg.InfiniteLine(
                angle=90, movable=False, pen=pg.mkPen("magenta", width=2)
            )
            self.plot_widget.addItem(self.Rmax_line)
            self.Rmax_label = pg.TextItem("Rmax", anchor=(0.0, 0.5))
            self.Rmax_label.setColor("magenta")
            self.plot_widget.addItem(self.Rmax_label)

            layout.addWidget(self.plot_widget)

            self.cursor = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("yellow", width=2))
            self.plot_widget.addItem(self.cursor)

        def set_cursor_position(self, R):
            self.cursor.setPos(R)

        def set_rmax_marker(self, Rmax):
            self.Rmax_line.setPos(Rmax)
            self.Rmax_label.setPos(Rmax - 0.006, 0.94)
            self.Rmax_label.setText("Rmax")

        def update_legend(self, text):
            self.legend_text.setText(text)

    def __init__(self, Rmax, composition_profile, solvent_profile):
        super().__init__()
        self.Rmax = Rmax
        self.composition_profile = composition_profile
        self.solvent_profile = solvent_profile
        self.info_panel = None
        self.comp1_plot = None
        self.impurity_plot = None
        self.solvent_plot = None

        self.setWindowTitle("MultXeu Purification Profile Viewer")
        MainWindow._active_window = self

        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)

        self._setup_component_selection()
        self._create_plot_widgets()

        slider_layout = QHBoxLayout()
        self.slider_label = QLabel("Recovery: 1.00")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.on_slider_changed)
        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.slider)
        self.main_layout.addLayout(slider_layout)

        self._populate_plots()

    def closeEvent(self, event):
        self.hide()
        MainWindow._active_window = None
        self.deleteLater()
        event.accept()

    def _setup_component_selection(self):
        if not self.composition_profile:
            self.main_components = []
            self.impurity_components = []
            self.purified_component_index = None
            self.purified_component_indices = []
            return

        i_Rmax = min(
            range(len(self.composition_profile)),
            key=lambda i: abs(self.composition_profile[i][0] - self.Rmax)
        )
        i_zero = len(self.composition_profile) - 1

        n_components = len(self.composition_profile[0][1])
        self.main_components = _dominant_component_indices_for_summary(self.composition_profile, self.Rmax)
        if not self.main_components:
            self.main_components = [max(range(n_components), key=lambda idx: self.composition_profile[-2][1][idx]) if len(self.composition_profile) > 1 else 0]

        self.main_components = sorted(self.main_components)
        self.purified_component_indices = list(self.main_components)
        self.purified_component_index = self.purified_component_indices[0] if self.purified_component_indices else None

        self.impurity_components = [
            k for k in range(n_components)
            if k not in self.purified_component_indices and any(row[1][k] > 1e-12 for row in self.composition_profile)
        ]
        self.impurity_components = sorted(self.impurity_components)

        # print("[GUI] i_Rmax =", i_Rmax)
        # print("[GUI] i_zero =", i_zero)
        # print("[GUI] purified_component_indices =", self.purified_component_indices)
        # print("[GUI] main_components =", self.main_components)
        # print("[GUI] impurity_components =", self.impurity_components)

    def _clear_plot_area(self):
        for plot_name in ("comp1_plot", "impurity_plot", "solvent_plot"):
            widget = getattr(self, plot_name, None)
            if widget is None:
                continue

            if widget.parent() is not None and widget.parent().layout() is not None:
                widget.parent().layout().removeWidget(widget)

            plot_widget = getattr(widget, "plot_widget", None)
            if plot_widget is not None:
                for item in list(plot_widget.listDataItems()):
                    try:
                        plot_widget.removeItem(item)
                    except Exception:
                        pass
                for item in (widget.legend_text, widget.Rmax_line, widget.cursor, widget.Rmax_label):
                    try:
                        plot_widget.removeItem(item)
                    except Exception:
                        pass
                plot_widget.clear()

            widget.setParent(None)
            widget.deleteLater()
            setattr(self, plot_name, None)

        if self.info_panel is not None:
            self.info_panel.hide()
            self.info_panel.setParent(None)
            self.info_panel.deleteLater()
            self.info_panel = None

    def _create_plot_widgets(self):
        self.comp1_plot = self.ProfilePlotWidget(
            "Purified Component vs. Recovery", "Recovery (%)", "Composition (%)"
        )
        self.impurity_plot = self.ProfilePlotWidget(
            "Impurity Profile vs. Recovery", "Recovery (%)", "Composition (%)"
        )
        self.impurity_plot.plot_widget.setLimits(yMin=0)
        self.solvent_plot = self.ProfilePlotWidget(
            "Relative Solvent Volume", "Recovery (%)", "Relative Solvent Volume"
        )
        self.solvent_plot.plot_widget.setLimits(yMin=0)

        self.main_layout.addWidget(self.comp1_plot)
        self.main_layout.addWidget(self.impurity_plot)
        self.main_layout.addWidget(self.solvent_plot)

        self.info_panel = self.InfoPanel(self.comp1_plot.plot_widget)
        self.info_panel.resize(220, 140)
        self.info_panel.raise_()
        self.info_panel.show()
        self._position_info_panel()

    def _populate_plots(self):
        if self.main_components:
            purified_parts = []
            for idx in self.main_components:
                value = self.composition_profile[0][1][idx] * 100
                purified_parts.append(f"Comp{idx + 1}:{value:.1f}%")
            self.comp1_plot.update_legend(
                ", ".join(purified_parts) if purified_parts else "Purified: none"
            )
        else:
            self.comp1_plot.update_legend("Purified: none")

        impurity_labels = []
        for idx in self.impurity_components:
            value = self.composition_profile[0][1][idx] * 100
            impurity_labels.append(f"{value:.1f}%")

        self.impurity_plot.update_legend(
            "Impurities: " + ", ".join(impurity_labels) if impurity_labels else "Impurities: none"
        )
        recovery_index = min(len(self.solvent_profile) - 1, max(0, self.slider.value()))
        self.solvent_plot.update_legend(f"RelSolVol: {self.solvent_profile[recovery_index][1]:.2f}")
        self.comp1_plot.set_cursor_position(1.0)
        self.impurity_plot.set_cursor_position(1.0)
        self.solvent_plot.set_cursor_position(1.0)

        self.plot_profiles()
        self.comp1_plot.set_rmax_marker(self.Rmax)
        self.impurity_plot.set_rmax_marker(self.Rmax)
        self.solvent_plot.set_rmax_marker(self.Rmax)

    def refresh_plot_data(self, Rmax, composition_profile, solvent_profile):
        old_pos = self.pos()
        old_size = self.size()

        self.Rmax = Rmax
        self.composition_profile = composition_profile
        self.solvent_profile = solvent_profile
        self._setup_component_selection()

        self._clear_plot_area()
        self._create_plot_widgets()
        self._populate_plots()

        self.resize(old_size)
        self.move(old_pos)
        self._position_info_panel()

    def _position_info_panel(self):
        if self.info_panel is None or self.comp1_plot is None:
            return

        plot = self.comp1_plot.plot_widget
        panel_width = self.info_panel.width()
        plot_width = max(plot.width(), 200)
        x = max(10, plot_width - panel_width - 18)
        self.info_panel.move(x, 20)
        self.info_panel.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.info_panel is not None:
            self._position_info_panel()

    def showEvent(self, event):
        super().showEvent(event)
        if self.info_panel is not None:
            self._position_info_panel()

    def plot_profiles(self):
        R = [row[0] for row in self.composition_profile]
        R_solv = [row[0] for row in self.solvent_profile]
        V_solv = [row[1] for row in self.solvent_profile]
        impurity_colors = self._impurity_colors(len(self.impurity_components))

        degenerate_main_pair = len(self.main_components) > 1
        rmax_index = None
        if degenerate_main_pair:
            rmax_index = min(
                range(len(self.composition_profile)),
                key=lambda i: abs(self.composition_profile[i][0] - self.Rmax)
            )

        def _valid_points(component_index):
            points = []
            started = False
            plateau_value = None
            if degenerate_main_pair:
                plateau_value = self.composition_profile[rmax_index][1][component_index] * 100

            for R_val, row in zip(R, [entry[1] for entry in self.composition_profile]):
                value = row[component_index] * 100
                if degenerate_main_pair and R_val <= self.Rmax:
                    value = plateau_value

                if value > 1e-9:
                    points.append((R_val, value))
                    started = True
                    continue

                if started:
                    points.append((R_val, 0.0))
                    break

            return points

        for idx, component_index in enumerate(self.main_components):
            comp_points = _valid_points(component_index)
            if not comp_points:
                continue

            color = "blue" if idx == 0 else "darkBlue"
            self.comp1_plot.plot_widget.plot(
                [r for r, _ in comp_points],
                [v for _, v in comp_points],
                pen=pg.mkPen(color, width=2),
            )

        for idx, k in enumerate(self.impurity_components):
            points = _valid_points(k)
            if not points:
                continue

            color = impurity_colors[idx] if idx < len(impurity_colors) else "white"
            self.impurity_plot.plot_widget.plot(
                [r for r, _ in points],
                [v for _, v in points],
                pen=pg.mkPen(color, width=2),
            )

        self.solvent_plot.plot_widget.clear()
        self.solvent_plot.plot_widget.enableAutoRange(axis='y')
        self.solvent_plot.plot_widget.enableAutoRange(axis='x')
        self.solvent_plot.plot_widget.setLabel('left', "Relative Solvent Volume")
        self.solvent_plot.plot_widget.addItem(self.solvent_plot.cursor)
        self.solvent_plot.plot_widget.addItem(self.solvent_plot.Rmax_line)
        self.solvent_plot.plot_widget.plot(R_solv, V_solv, pen=pg.mkPen("cyan", width=2))

    def on_slider_changed(self, value):
        R = 1.0 - value / 100.0
        self.slider_label.setText(f"Recovery: {R*100:.0f}%")

        recovery_index = min(len(self.composition_profile) - 1, max(0, int(value)))

        purified_pct = [
            self.composition_profile[recovery_index][1][idx] * 100
            for idx in self.main_components
        ]
        impurity_pct = [
            self.composition_profile[recovery_index][1][idx] * 100
            for idx in self.impurity_components
        ]

        relsol = self.solvent_profile[recovery_index][1]
        self.solvent_plot.update_legend(f"RelSolVol: {relsol:.2f}")

        text = (
            f"Recovery (%): {R * 100:.2f}\n"
            f"Purified Component (%): {', '.join(f'{v:.2f}' for v in purified_pct) if purified_pct else 'none'}\n"
            + "Impurities (%): " + (", ".join(f"{v:.2f}" for v in impurity_pct) if impurity_pct else "none") + "\n"
            + f"RelSolVol: {relsol:.2f}"
        )
        self.info_panel.update_info(text)

        self.comp1_plot.set_cursor_position(R)
        self.impurity_plot.set_cursor_position(R)
        self.solvent_plot.set_cursor_position(R)


        


def run_gui(Rmax, composition_profile, solvent_profile, parent=None):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        created_app = True
    else:
        created_app = False

    existing_window = MainWindow._active_window
    if existing_window is not None:
        try:
            existing_window.isVisible()
        except RuntimeError:
            MainWindow._active_window = None
            existing_window = None

    if existing_window is not None:
        old_pos = existing_window.pos()
        existing_window.refresh_plot_data(Rmax, composition_profile, solvent_profile)
        existing_window.move(old_pos)
        existing_window.show()
        existing_window.raise_()
        existing_window.activateWindow()
        if created_app:
            app.exec()
        return existing_window

    window = MainWindow(Rmax, composition_profile, solvent_profile)
    window.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.WindowCloseButtonHint
        | Qt.WindowType.WindowMinimizeButtonHint
        | Qt.WindowType.WindowMaximizeButtonHint
    )
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
    window.resize(960, 640)
    window.setWindowTitle("MultXeu Purification Profile Viewer")
    window.show()

    if created_app:
        app.exec()

    return window
