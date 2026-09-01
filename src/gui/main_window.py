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
    controles de reproducción. Recibe una señal en memoria y genera
    ventanas sucesivas de muestras para su representación. Puede mostrar
    simultáneamente una señal cruda y una señal filtrada, además de
    superponer eventos procedentes de un archivo `events.tsv` en formato
    BIDS.

    La reproducción se realiza mediante un `QTimer` que ejecuta
    periódicamente `PlaybackEngine.tick()`. La frecuencia de muestreo y
    el período del temporizador determinan la cantidad de muestras
    avanzadas en cada actualización.

    Args:
        signal (np.ndarray): Señal cruda con forma
            `(n_canales, n_muestras)`.
        signal_filt (np.ndarray, optional): Señal filtrada con la misma
            forma que `signal`. Si no se proporciona, se utiliza `signal`
            también como señal filtrada.
        events_path (str, optional): Ruta a un archivo `events.tsv` en
            formato BIDS. Si no se proporciona, no se cargan eventos.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        window_size (int): Tamaño de la ventana visible, en muestras.
        scale_factor (float): Factor de escala utilizado para representar
            las señales.
        refresh_ms (int): Período del temporizador de reproducción, en
            milisegundos.

    Raises:
        ValueError: Si `signal` no tiene dos dimensiones.

    Attributes:
        signal (np.ndarray): Señal cruda almacenada en memoria.
        signal_filt (np.ndarray): Señal filtrada utilizada para la
            visualización.
        n_channels (int): Número de canales de la señal.
        n_samples (int): Número total de muestras de la señal.
        sfreq (float): Frecuencia de muestreo de la señal.
        events (list): Eventos cargados desde el archivo BIDS, o lista
            vacía si no se proporciona un archivo.
        engine (PlaybackEngine): Motor encargado de controlar la posición
            de reproducción.
        display (SignalDisplayWidget): Widget encargado de representar
            las señales y los eventos.
        controls (PlaybackControls): Widget con los controles de
            reproducción.
    """

    def __init__(self, signal: np.ndarray, signal_filt: None|np.ndarray = None,
                 events_path: None|str = None, sfreq: float = 250.0,
                 window_size: int = 1500, scale_factor: float = 50,
                 refresh_ms: int = 20):
        """
        Inicializa la ventana principal y sus componentes de reproducción.

        Valida la dimensionalidad de la señal, configura los datos de
        reproducción y, opcionalmente, carga los eventos BIDS. Luego crea
        el motor de reproducción, el widget de visualización y los
        controles, conecta sus señales y pone en marcha el temporizador.

        La cantidad de muestras avanzadas en cada actualización se calcula
        a partir de `sfreq` y `refresh_ms`.

        Args:
            signal (np.ndarray): Señal cruda con forma
                `(n_canales, n_muestras)`.
            signal_filt (np.ndarray, optional): Señal filtrada utilizada
                para la visualización. Si es `None`, se utiliza `signal`.
            events_path (str, optional): Ruta al archivo `events.tsv`
                desde el que se cargarán los eventos.
            sfreq (float): Frecuencia de muestreo, en Hz.
            window_size (int): Tamaño de la ventana visible, en muestras.
            scale_factor (float): Factor de escala aplicado durante la
                visualización.
            refresh_ms (int): Intervalo del temporizador, en milisegundos.

        Returns:
            None

        Notes:
            - `signal` debe tener exactamente dos dimensiones.
            - El número de canales y muestras se obtiene directamente de
              `signal.shape`.
            - Si no se proporciona `signal_filt`, se utiliza la señal cruda
              para ambos tipos de visualización.
            - Si no se proporciona `events_path`, `events` se inicializa
              como una lista vacía.
            - El avance por actualización se calcula como
              `max(1, round(sfreq * refresh_ms / 1000))`.
            - El temporizador se inicia inmediatamente después de conectar
              sus señales.
            - La vista se actualiza inicialmente utilizando la posición
              inicial del motor de reproducción.
        """
        super().__init__()

        if signal.ndim != 2:
            raise ValueError("`signal` debe tener forma (n_canales, n_muestras).")

        self.signal = signal
        self.signal_filt = signal_filt if signal_filt is not None else signal
        self.n_channels, self.n_samples = signal.shape
        self.sfreq = sfreq

        self.events = load_bids_events(events_path, sfreq) if events_path else []

        self.setWindowTitle("NeuroIA GUI — Reproductor de señales")
        self.setGeometry(45, 80, 1600, 900)

        # Muestras por tick, calculadas a partir de sfreq para que la
        # reproducción avance a velocidad real (no a una velocidad arbitraria).
        step = max(1, round(sfreq * refresh_ms / 1000))
        self.engine = PlaybackEngine(self.n_samples, window_size, step=step)

        self.display = SignalDisplayWidget(
            channel_names=self.n_channels,
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

        Conecta los cambios de posición del motor con la actualización de
        la vista, y conecta los botones de retroceso y avance directamente
        con sus operaciones correspondientes del motor. El botón de
        reproducción/pausa se conecta al método que alterna su estado.

        Returns:
            None

        Notes:
            - `position_changed` se conecta a `_refresh_view`.
            - `prev_clicked` se conecta a `step_backward`.
            - `next_clicked` se conecta a `step_forward`.
            - `play_pause_clicked` se conecta a `_toggle_play_pause`.
        """
        self.engine.position_changed.connect(self._refresh_view)
        self.controls.prev_clicked.connect(self.engine.step_backward)
        self.controls.next_clicked.connect(self.engine.step_forward)
        self.controls.play_pause_clicked.connect(self._toggle_play_pause)

    def _toggle_play_pause(self):
        """
        Alterna el estado de reproducción y actualiza el control asociado.

        Cambia el estado de pausa del motor mediante `play_pause()` y
        actualiza el texto del botón de reproducción/pausa según el nuevo
        estado.

        Returns:
            None
        """
        is_paused = self.engine.play_pause()
        self.controls.set_paused_label(is_paused)

    def _refresh_view(self, pos: int):
        """
        Actualiza la ventana visible de señales, eventos y posición.

        Calcula los límites de la ventana a partir de la posición actual
        y el tamaño de ventana del motor. Extrae de la señal cruda y de la
        señal filtrada las muestras correspondientes y las envía al widget
        de visualización.

        También actualiza los eventos visibles para la misma ventana y
        modifica la etiqueta de posición de los controles.

        Args:
            pos (int): Posición actual de reproducción, utilizada como
                límite superior de la ventana visible.

        Returns:
            None

        Notes:
            - El inicio de la ventana se calcula como
              `pos - window_size`.
            - El final de la ventana coincide con `pos`.
            - `x_data` contiene las muestras desde `start` hasta `end - 1`.
            - Se extraen todos los canales mediante `signal[:, start:end]`.
            - La señal filtrada se extrae mediante el mismo intervalo.
            - La actualización de señales y eventos se delega a
              `SignalDisplayWidget`.
            - La posición mostrada en los controles incluye la posición
              actual y el total de muestras.
        """
        start = pos - self.engine.window_size
        end = pos

        x_data = np.arange(start, end)
        y_raw_window = self.signal[:, start:end]
        y_filt_window = self.signal_filt[:, start:end]

        self.display.update_data(x_data, y_raw_window, y_filt_window)
        self.display.update_events(self.events, start, end)
        self.controls.set_position_label(pos, self.n_samples)

    def closeEvent(self, event):
        """
        Detiene el temporizador de reproducción al cerrar la ventana.

        Comprueba si existe el temporizador y si se encuentra activo.
        En ese caso, lo detiene antes de aceptar el evento de cierre.

        Args:
            event (QCloseEvent): Evento generado al solicitar el cierre
                de la ventana.

        Returns:
            None

        Notes:
            - El temporizador solo se detiene si existe y está activo.
            - El evento de cierre se acepta mediante `event.accept()`.
        """
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        event.accept()


def launch_viewer(signal: np.ndarray, signal_filt: None|np.ndarray = None,
                   events_path: None|str = None, sfreq: float = 250.0,
                   window_size: int = 1500, scale_factor: float = 50):
    """
    Crea y ejecuta el visor de señales.

    Obtiene una instancia existente de `QApplication` o crea una nueva si
    no existe. Luego instancia `MainWindow` con los datos proporcionados,
    muestra la ventana y ejecuta el bucle de eventos de la aplicación.

    Args:
        signal (np.ndarray): Señal a visualizar con forma
            `(n_canales, n_muestras)`.
        signal_filt (np.ndarray, optional): Señal filtrada a visualizar.
            Si no se proporciona, `MainWindow` utiliza `signal`.
        events_path (str, optional): Ruta a un archivo `events.tsv` en
            formato BIDS.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        window_size (int): Tamaño de la ventana visible, en muestras.
        scale_factor (float): Factor de escala utilizado para visualizar
            las señales.

    Returns:
        None

    Notes:
        - Si ya existe una instancia de `QApplication`, se reutiliza.
        - La ventana se muestra mediante `show()`.
        - La ejecución queda a cargo del bucle de eventos de Qt.
        - La función finaliza mediante `sys.exit()` con el resultado de
          `app.exec_()`.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(signal, signal_filt=signal_filt, events_path=events_path,
                         sfreq=sfreq, window_size=window_size, scale_factor=scale_factor)
    window.show()
    sys.exit(app.exec_())
