from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QStackedWidget, QSlider, QSpinBox
)
from PySide6.QtCore import Qt, Signal
import numpy as np
import imageio

from modules.i_image_module import IImageModule

class BaseParamsWidget(QWidget):
    def get_params(self) -> dict:
        raise NotImplementedError


class NoParamsWidget(BaseParamsWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("No parameters for this filter."))
        layout.addStretch()

    def get_params(self):
        return {}


class BrightnessParamsWidget(BaseParamsWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Brightness Strength"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(-100)
        self.slider.setMaximum(100)
        self.slider.setValue(30)
        layout.addWidget(self.slider)

    def get_params(self):
        return {"strength": self.slider.value()}


class ThresholdParamsWidget(BaseParamsWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Threshold Value"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(255)
        self.slider.setValue(128)
        layout.addWidget(self.slider)

    def get_params(self):
        return {"threshold": self.slider.value()}


class PosterizeParamsWidget(BaseParamsWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Number of Levels"))
        self.spin = QSpinBox()
        self.spin.setMinimum(2)
        self.spin.setMaximum(16)
        self.spin.setValue(4)
        layout.addWidget(self.spin)

    def get_params(self):
        return {"levels": self.spin.value()}


class SolarizeParamsWidget(BaseParamsWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Solarization Threshold"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(255)
        self.slider.setValue(128)
        layout.addWidget(self.slider)

    def get_params(self):
        return {"threshold": self.slider.value()}

class EmanControlsWidget(QWidget):
    process_requested = Signal(dict)

    def __init__(self, module_manager, parent=None):
        super().__init__(parent)
        self.module_manager = module_manager
        self.param_widgets = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Eman Image Filters</h3>"))
        layout.addWidget(QLabel("Operation"))

        self.operation_selector = QComboBox()
        layout.addWidget(self.operation_selector)

        self.params_stack = QStackedWidget()
        layout.addWidget(self.params_stack)

        operations = {
            "Image Negative": NoParamsWidget,
            "Brightness Boost": BrightnessParamsWidget,
            "Binary Threshold": ThresholdParamsWidget,
            "Posterization": PosterizeParamsWidget,
            "Solarization": SolarizeParamsWidget,
            "Channel Swap (RGB)": NoParamsWidget,
        }

        for name, widget_class in operations.items():
            widget = widget_class()
            self.operation_selector.addItem(name)
            self.params_stack.addWidget(widget)
            self.param_widgets[name] = widget

        self.apply_button = QPushButton("Apply Filter")
        layout.addWidget(self.apply_button)

        self.apply_button.clicked.connect(self._apply)
        self.operation_selector.currentTextChanged.connect(
            lambda name: self.params_stack.setCurrentWidget(self.param_widgets[name])
        )

    def _apply(self):
        op = self.operation_selector.currentText()
        params = self.param_widgets[op].get_params()
        params["operation"] = op
        self.process_requested.emit(params)


class EmanImageModule(IImageModule):

    def __init__(self):
        super().__init__()
        self._controls_widget = None

    def get_name(self):
        return "Eman Module"

    def get_supported_formats(self):
        return ["png", "jpg", "jpeg", "bmp", "tiff"]

    def create_control_widget(self, parent=None, module_manager=None):
        if self._controls_widget is None:
            self._controls_widget = EmanControlsWidget(module_manager, parent)
            self._controls_widget.process_requested.connect(
                self._handle_processing_request
            )
        return self._controls_widget

    def _handle_processing_request(self, params):
        if self._controls_widget.module_manager:
            self._controls_widget.module_manager.apply_processing_to_current_image(params)

    def load_image(self, file_path):
        try:
            image = imageio.imread(file_path)
            return True, image, {"name": file_path.split("/")[-1]}, None
        except Exception as e:
            print("Load error:", e)
            return False, None, {}, None


    def process_image(self, image_data, metadata, params):
        img = image_data.astype(float)
        max_val = np.max(img)
        op = params["operation"]

        if op == "Image Negative":
            img = max_val - img

        elif op == "Brightness Boost":
            strength = params["strength"]
            img = np.clip(img + strength, 0, max_val)

        elif op == "Binary Threshold":
            t = params["threshold"]
            img = np.where(img > t, max_val, 0)

        elif op == "Posterization":
            levels = params["levels"]
            step = max_val / levels
            img = np.floor(img / step) * step

        elif op == "Solarization":
            t = params["threshold"]
            img = np.where(img < t, img, max_val - img)

        elif op == "Channel Swap (RGB)":
            if img.ndim == 3 and img.shape[2] >= 3:
                img = img[:, :, [2, 1, 0]]

        return img.astype(image_data.dtype)
