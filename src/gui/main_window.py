import sys

import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget

from gui.widgets.playback_controls import PlaybackControls
from gui.widgets.signal_display_widget import SignalDisplayWidget
from utils.bids_events import load_bids_events
from utils.filters import prepare_for_display
from utils.playback_engine import PlaybackEngine


class MainWindow(QWidget):
    """
    Ventana principal para la reproducción y visualización de señales.

    Integra el motor de reproducción, el widget de visualización y los
    controles de reproducción. Recibe una señal multicanal en memoria,
    permite seleccionar los canales que serán visualizados y configura
    la señal completa y sus eventos en el widget de visualización.

    Antes de la reproducción, la señal seleccionada puede someterse a un
    filtrado mínimo para visualización y posteriormente se normaliza de forma
    independiente por canal mediante z-score.

    La reproducción se controla mediante un `QTimer`, que ejecuta
    periódicamente `PlaybackEngine.tick()`. Los cambios de posición del motor
    actualizan el rango temporal visible y la posición mostrada en los
    controles.

    Args:
        signal (np.ndarray): Señal multicanal con forma
            `(n_canales, n_muestras)`.
        channel_names (list of str, optional): Nombres de todos los canales de
            la señal. Si no se proporcionan, se generan nombres con el formato
            `"Ch {i}"`.
        channels_idx (list, optional): Índices de los canales que serán
            utilizados para la visualización. Si no se proporciona, se utilizan
            todos los canales.
        events_path (str, optional): Ruta a un archivo `events.tsv` en
            formato BIDS. Si no se proporciona, no se cargan eventos.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        window_size (int): Tamaño de la ventana visible, en muestras.
        scale_factor (float): Factor de escala utilizado para representar
            las señales.
        refresh_ms (int): Período del temporizador de reproducción, en
            milisegundos.
        highpass (float or None): Frecuencia de corte del filtro pasa-altos
            utilizado para la preparación de la señal para visualización.
            Si es `None`, no se aplica este filtro.
        notch (float or None): Frecuencia del filtro notch utilizado para
            reducir el ruido de línea eléctrica. Si es `None`, no se aplica
            este filtro.

    Raises:
        ValueError: Si `signal` no es un array bidimensional o si
            `channels_idx` está vacío.
        IndexError: Si algún índice de `channels_idx` está fuera del rango
            de canales de la señal.
    """

    def __init__(self, signal: np.ndarray, channel_names: None | list = None,
                 channels_idx: None | list = None, events_path: None | str = None,
                 sfreq: float = 500.0,
                 window_size: int = 1500, scale_factor: float = 50,
                 refresh_ms: int = 20,
                 highpass: float | None = 0.5, notch: float | None = 50.0):
        """
        Inicializa la ventana principal y sus componentes de reproducción.

        Valida la dimensión de la señal, determina los canales que serán
        utilizados para la visualización, resuelve sus nombres, aplica
        opcionalmente el filtrado de visualización y normaliza la señal por canal.
        Luego carga opcionalmente los eventos BIDS, crea el motor de reproducción,
        configura el widget de visualización con la señal completa y los eventos,
        y establece el temporizador encargado de actualizar el rango visible
        durante la reproducción.

        Args:
            signal (np.ndarray): Señal multicanal con forma
                `(n_canales, n_muestras)`.
            channel_names (list of str, optional): Nombres de todos los canales.
                Si es `None`, se generan nombres con el formato `"Ch {i}"`.
                Si se proporciona, debe contener un nombre por cada canal de
                `signal`.
            channels_idx (list, optional): Índices de los canales que serán
                utilizados para la visualización. Si es `None`, se utilizan
                todos los canales. Los índices se ordenan y se eliminan los
                duplicados.
            events_path (str, optional): Ruta al archivo `events.tsv` con los
                eventos BIDS.
            sfreq (float): Frecuencia de muestreo en Hz.
            window_size (int): Tamaño de la ventana visible en muestras.
            scale_factor (float): Factor de escala vertical utilizado por el
                widget de visualización.
            refresh_ms (int): Intervalo de actualización del temporizador, en
                milisegundos.
            highpass (float or None): Frecuencia de corte del filtro pasa-altos
                aplicado durante la preparación para visualización. Si es `None`,
                se omite.
            notch (float or None): Frecuencia del filtro notch aplicado durante
                la preparación para visualización. Si es `None`, se omite.

        Raises:
            ValueError: Si `signal.ndim` es diferente de 2, si `channels_idx`
                está vacío o si la cantidad de `channel_names` no coincide con
                el número de canales de la señal.
            IndexError: Si algún índice de `channels_idx` está fuera del rango
                de la señal.
        """
        super().__init__()

        if signal.ndim != 2:
            raise ValueError("`signal` debe tener forma (n_canales, n_muestras).")

        n_channels_orig, self.n_samples = signal.shape

        # Resolver los índices a utilizar (ordenar y quitar duplicados)
        if channels_idx is not None:
            self.channels_idx = sorted(list(set(channels_idx)))

            if not self.channels_idx:
                raise ValueError("La lista `channels_idx` no puede estar vacía.")

            if self.channels_idx[-1] >= n_channels_orig or self.channels_idx[0] < 0:
                raise IndexError("Hay índices en `channels_idx` fuera del rango de la señal.")

        else:
            self.channels_idx = list(range(n_channels_orig))

        # Resolver los nombres de todos los canales originales
        if channel_names is None:
            all_channel_names = [f"Ch {i}" for i in range(n_channels_orig)]
        else:
            if len(channel_names) != n_channels_orig:
                raise ValueError(
                    f"Se esperaban {n_channels_orig} nombres de canales, pero se recibieron {len(channel_names)}."
                )
            all_channel_names = channel_names

        # Aplicar el filtro de canales a la señal y a los nombres seleccionados
        self.signal = signal[self.channels_idx, :]
        self.channel_names = [all_channel_names[i] for i in self.channels_idx]
        self.n_channels = len(self.channels_idx)

        self.sfreq = sfreq

        # Filtrado de visualización
        # remueve deriva de baja frecuencia y ruido de línea para que la
        # morfología sea visible, sin recortar bandas fisiológicas.
        if highpass or notch:
            self.signal = prepare_for_display(self.signal, sfreq, highpass=highpass, notch=notch)

        # Normalización por canal (z-score), sobre la señal ya filtrada
        means = np.mean(self.signal, axis=1, keepdims=True)
        self.signal = self.signal - means

        stds = np.std(self.signal, axis=1, keepdims=True)
        stds[stds == 0] = 1.0  # Prevenir división por cero en canales muertos
        self.signal = self.signal / stds

        self.events = load_bids_events(events_path, sfreq) if events_path else []

        self.setWindowTitle("NeuroIA GUI — Reproductor de señales")
        self.setGeometry(45, 80, 1600, 900)

        step = max(1, round(sfreq * refresh_ms / 1000))
        self.engine = PlaybackEngine(self.n_samples, window_size, step=step)

        self.display = SignalDisplayWidget(
            channel_names=self.channel_names,
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

        self.display.load_full_signal(np.arange(self.n_samples), self.signal)
        self.display.set_events(self.events)


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
        Actualiza el rango temporal visible de la señal para una posición
        determinada.

        Calcula los límites de la ventana a partir de la posición actual del
        reproductor, actualiza el rango visible del widget de visualización y
        modifica la etiqueta de posición de los controles.

        Args:
            pos (int): Posición final de la ventana en muestras.

        Returns:
            None
        """
        start = pos - self.engine.window_size
        end = pos

        self.display.set_view_range(start, end)
        self.controls.set_position_label(pos, self.n_samples)

    def closeEvent(self, event): # type: ignore
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


def launch_viewer(signal: np.ndarray, channel_names: None | list = None,
                   channels_idx: None | list = None, events_path: None | str = None,
                   sfreq: float = 500.0,
                   window_size: int = 1500, scale_factor: float = 50,
                   highpass: float | None = 0.5, notch: float | None = 50.0):
    """
    Crea y ejecuta el visor de señales.

    Inicializa la aplicación Qt si todavía no existe, crea una instancia de
    `MainWindow` con los parámetros proporcionados, muestra la ventana y
    ejecuta el ciclo de eventos de la aplicación.

    Args:
        signal (np.ndarray): Señal multicanal con forma
            `(n_canales, n_muestras)`.
        channel_names (list of str, optional): Nombres de todos los canales.
        channels_idx (list, optional): Índices de los canales que serán
            utilizados para la visualización. Si no se proporciona, se
            utilizan todos los canales.
        events_path (str, optional): Ruta a un archivo `events.tsv` en
            formato BIDS.
        sfreq (float): Frecuencia de muestreo en Hz.
        window_size (int): Tamaño de la ventana visible en muestras.
        scale_factor (float): Factor de escala utilizado para visualizar
            las señales.
        highpass (float or None): Frecuencia de corte del filtro pasa-altos
            utilizado para la preparación de la señal. Si es `None`, se omite.
        notch (float or None): Frecuencia del filtro notch utilizado para
            reducir el ruido de línea eléctrica. Si es `None`, se omite.

    Returns:
        None
    """
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(
        signal=signal,
        channel_names=channel_names,
        channels_idx=channels_idx,  # type: ignore
        events_path=events_path,
        sfreq=sfreq,
        window_size=window_size,
        scale_factor=scale_factor,
        highpass=highpass,
        notch=notch,
    )
    window.show()
    sys.exit(app.exec_())
