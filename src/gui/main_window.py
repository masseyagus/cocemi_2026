import sys

import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget

from gui.widgets.playback_controls import PlaybackControls
from gui.widgets.signal_display_widget import SignalDisplayWidget
from utils.bids_events import load_bids_events
from utils.playback_engine import PlaybackEngine


class MainWindow(QWidget):
    """
    Ventana principal para la reproducción y visualización de señales.

    Integra el motor de reproducción, el widget de visualización y los
    controles de reproducción. Recibe una señal multicanal en memoria y
    actualiza periódicamente una ventana de muestras para su representación.

    La reproducción se controla mediante un `QTimer`, que ejecuta
    periódicamente `PlaybackEngine.tick()`. Los cambios de posición del motor
    actualizan la ventana visible y la posición mostrada en los controles.

    Args:
        signal (np.ndarray): Señal multicanal con forma
            `(n_canales, n_muestras)`.
        channel_names (list of str, optional): Nombres de los canales que se
            mostrarán en el widget de visualización. Si no se proporcionan,
            el comportamiento depende de `SignalDisplayWidget`.
        events_path (str, optional): Ruta a un archivo `events.tsv` en
            formato BIDS. Si no se proporciona, no se cargan eventos.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        window_size (int): Tamaño de la ventana visible, en muestras.
        scale_factor (float): Factor de escala utilizado para representar
            las señales.
        refresh_ms (int): Período del temporizador de reproducción, en
            milisegundos.

    Raises:
        ValueError: Si `signal` no es un array bidimensional.
    """

    def __init__(self, signal: np.ndarray, channel_names: None|list = None,
                 events_path: None|str = None, sfreq: float = 250.0,
                 window_size: int = 1500, scale_factor: float = 50,
                 refresh_ms: int = 20):
        """
        Inicializa la ventana principal y sus componentes de reproducción.

        Valida la dimensión de la señal, carga opcionalmente los eventos BIDS,
        crea el motor de reproducción, configura el widget de visualización y
        los controles, y establece el temporizador encargado de actualizar la
        reproducción.

        Args:
            signal (np.ndarray): Señal multicanal con forma
                `(n_canales, n_muestras)`.
            channel_names (list of str, optional): Nombres de los canales.
            events_path (str, optional): Ruta al archivo `events.tsv` con los
                eventos BIDS.
            sfreq (float): Frecuencia de muestreo en Hz.
            window_size (int): Tamaño de la ventana visible en muestras.
            scale_factor (float): Factor de escala vertical utilizado por el
                widget de visualización.
            refresh_ms (int): Intervalo de actualización del temporizador, en
                milisegundos.

        Raises:
            ValueError: Si `signal.ndim` es diferente de 2.
        """
        super().__init__()

        if signal.ndim != 2:
            raise ValueError("`signal` debe tener forma (n_canales, n_muestras).")

        self.signal = signal
        self.n_channels, self.n_samples = signal.shape
        self.sfreq = sfreq

        self.events = load_bids_events(events_path, sfreq) if events_path else []

        self.setWindowTitle("NeuroIA GUI — Reproductor de señales")
        self.setGeometry(45, 80, 1600, 900)

        step = max(1, round(sfreq * refresh_ms / 1000))
        self.engine = PlaybackEngine(self.n_samples, window_size, step=step)

        # Pasamos channel_names al widget actualizado
        self.display = SignalDisplayWidget(
            channel_names=channel_names,
            window_size=self.engine.window_size,
            scale_factor=scale_factor,
        )
        self.controls = PlaybackControls()

        layout = QVBoxLayout()
        layout.addWidget(self.display)
        layout.addWidget(self.controls)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._connect_signals()

        self._timer = QTimer()
        self._timer.timeout.connect(self.engine.tick)
        self._timer.start(refresh_ms)

        self._refresh_view(self.engine.pos)

    def _connect_signals(self):
        """
        Conecta las señales de los componentes de la interfaz.

        Conecta los cambios de posición del motor con la actualización de la
        vista, los controles de avance y retroceso con las acciones
        correspondientes del motor y el control de reproducción/pausa con el
        método encargado de actualizar su estado.

        Returns:
            None
        """
        self.engine.position_changed.connect(self._refresh_view)
        self.controls.prev_clicked.connect(self.engine.step_backward)
        self.controls.next_clicked.connect(self.engine.step_forward)
        self.controls.play_pause_clicked.connect(self._toggle_play_pause)

    def _toggle_play_pause(self):
        """
        Alterna el estado de reproducción del motor.

        Ejecuta `PlaybackEngine.play_pause()` y actualiza la etiqueta del control
        de reproducción de acuerdo con el nuevo estado.

        Returns:
            None
        """
        is_paused = self.engine.play_pause()
        self.controls.set_paused_label(is_paused)

    def _refresh_view(self, pos: int):
        """
        Actualiza la ventana visible de la señal para una posición determinada.

        Calcula los límites de la ventana a partir de la posición actual del
        reproductor, extrae las muestras correspondientes de todos los canales,
        actualiza la visualización de la señal y de los eventos, y modifica la
        etiqueta de posición de los controles.

        Args:
            pos (int): Posición final de la ventana en muestras.

        Returns:
            None
        """
        start = pos - self.engine.window_size
        end = pos

        x_data = np.arange(start, end)
        
        # Ahora solo extraemos una ventana de datos
        y_window = self.signal[:, start:end]

        # Actualizamos pasando únicamente (x, y)
        self.display.update_data(x_data, y_window)
        self.display.update_events(self.events, start, end)
        self.controls.set_position_label(pos, self.n_samples)

    def closeEvent(self, event):
        """
        Detiene el temporizador de reproducción al cerrar la ventana.

        Si el temporizador está creado y activo, se detiene antes de aceptar el
        evento de cierre.

        Args:
            event (QCloseEvent): Evento de cierre de la ventana.

        Returns:
            None
        """
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        event.accept()


def launch_viewer(signal: np.ndarray, channel_names: None|list = None,
                  events_path: None|str = None, sfreq: float = 250.0,
                  window_size: int = 1500, scale_factor: float = 50):
    """
    Crea y ejecuta el visor de señales.

    Inicializa la aplicación Qt si todavía no existe, crea una instancia de
    `MainWindow` con los parámetros proporcionados, muestra la ventana y
    ejecuta el ciclo de eventos de la aplicación.

    Args:
        signal (np.ndarray): Señal multicanal con forma
            `(n_canales, n_muestras)`.
        channel_names (list of str, optional): Nombres de los canales.
        events_path (str, optional): Ruta a un archivo `events.tsv` en
            formato BIDS.
        sfreq (float): Frecuencia de muestreo en Hz.
        window_size (int): Tamaño de la ventana visible en muestras.
        scale_factor (float): Factor de escala utilizado para visualizar
            las señales.

    Returns:
        None
    """
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(
        signal=signal, 
        channel_names=channel_names, 
        events_path=events_path,
        sfreq=sfreq, 
        window_size=window_size, 
        scale_factor=scale_factor
    )
    window.show()
    sys.exit(app.exec_())
