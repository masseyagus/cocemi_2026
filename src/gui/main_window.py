import sys
from pathlib import Path

import numpy as np  #type: ignore
from PyQt5 import QtGui  #type: ignore
from PyQt5.QtCore import QTimer  #type: ignore
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget  #type: ignore

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
    filtrado mínimo para visualización mediante filtros pasa-altos, pasa-bajos
    y notch. La señal resultante se centra por canal y se normaliza mediante
    z-score utilizando la desviación estándar calculada sobre la señal
    excluyendo el 1 % de cada extremo para reducir la influencia de artefactos
    de borde.

    Los canales seleccionados se colorean según el tipo de señal al que
    pertenecen. La asignación de tipos y colores se define mediante
    `SIGNAL_TYPES`, que establece rangos de índices para EEG, EMG y EOG.
    Los colores correspondientes se proporcionan al widget de visualización
    junto con los elementos utilizados para construir la leyenda.

    La señal completa se carga una única vez en el widget de visualización,
    utilizando un eje temporal expresado en segundos. Durante la reproducción,
    únicamente se actualiza el rango temporal visible.

    La reproducción se controla mediante un `QTimer`, que ejecuta
    periódicamente `PlaybackEngine.tick()`. La velocidad de avance se
    determina mediante `playback_rate` y el intervalo de actualización
    mediante `refresh_ms`.

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
        notch (float or None): Frecuencia base utilizada para generar las
            frecuencias del filtro notch. Se generan múltiplos de esta
            frecuencia inferiores a la frecuencia de Nyquist. Si es `None`,
            no se generan frecuencias notch.
        playback_rate (float): Factor utilizado para determinar la cantidad
            de muestras que avanza la reproducción en cada actualización.
        lowpass (float or None): Frecuencia de corte del filtro pasa-bajos
            utilizado para la preparación de la señal. Si es `None`, no se
            aplica este filtro.

    Raises:
        ValueError: Si `signal` no es un array bidimensional, si
            `channels_idx` está vacío o si la cantidad de `channel_names`
            no coincide con el número de canales de la señal.
        IndexError: Si algún índice de `channels_idx` está fuera del rango
            de canales de la señal.
    """

    def __init__(self, signal: np.ndarray, channel_names: None | list = None,
                 channels_idx: None | list = None, events_path: None | str = None,
                 sfreq: float = 500.0,
                 window_size: int = 1500, scale_factor: float = 50,
                 refresh_ms: int = 20,
                 highpass: float | None = 0.5, notch: float | None = 50.0,
                 playback_rate: float = 0.25, lowpass: float | None = 100):
        """
        Inicializa la ventana principal y sus componentes de reproducción.

        Valida la dimensión de la señal, determina los canales que serán
        utilizados para la visualización y resuelve sus nombres. Posteriormente
        aplica opcionalmente filtros pasa-altos, pasa-bajos y notch a la señal
        seleccionada.

        La señal filtrada se centra por canal y se normaliza mediante z-score.
        Para calcular la desviación estándar se excluye el 1 % de cada extremo
        de la señal, con el objetivo de reducir la influencia de artefactos
        de borde.

        Luego carga opcionalmente los eventos BIDS, configura el título y el
        ícono de la ventana, crea el motor de reproducción y determina el color
        de cada canal según su índice. La clasificación de los canales se realiza
        mediante `SIGNAL_TYPES`, que define los rangos correspondientes a EEG,
        EMG y EOG. Los colores resultantes se proporcionan al widget de
        visualización junto con la información necesaria para construir la
        leyenda por tipo de señal.

        Finalmente, crea el widget de visualización con la señal completa y sus
        eventos, configura los controles de reproducción y establece el
        temporizador encargado de actualizar el rango temporal visible durante
        la reproducción.

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
                aplicado durante la preparación para visualización. Si es
                `None`, se omite.
            notch (float or None): Frecuencia base utilizada para generar las
                frecuencias del filtro notch. Sus múltiplos inferiores a la
                frecuencia de Nyquist se utilizan durante la preparación de la
                señal. Si es `None` o no es positiva, no se generan frecuencias
                notch.
            playback_rate (float): Factor utilizado para calcular el número de
                muestras que avanza el reproductor en cada actualización.
            lowpass (float or None): Frecuencia de corte del filtro pasa-bajos
                aplicado durante la preparación para visualización. Si es
                `None`, se omite.

        Returns:
            None

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
        if highpass or notch or lowpass:
            notch_freqs = None
            if notch and notch > 0:
                nyq = sfreq / 2
                notch_freqs = list(np.arange(notch, nyq, notch))

            self.signal = prepare_for_display(
                self.signal, sfreq, 
                highpass=highpass, 
                lowpass=lowpass, 
                notch=notch_freqs  # type: ignore
            )

        # Normalización por canal (z-score), sobre la señal ya filtrada
        means = np.mean(self.signal, axis=1, keepdims=True)
        self.signal = self.signal - means

        # Calcular std ignorando el 1% de cada extremo para evitar que artefactos de borde arruinen la escala
        trim = max(1, int(self.n_samples * 0.01))
        stds = np.std(self.signal[:, trim:-trim], axis=1, keepdims=True)
        stds[stds == 0] = 1.0  # Prevenir división por cero en canales muertos
        self.signal = self.signal / stds

        self.events = load_bids_events(events_path, sfreq) if events_path else []

        self.setWindowTitle("Reproductor de señales - NeuroIA GUI")

        icon_parent = Path(__file__).resolve().parent
        path_icon = icon_parent.parent / "assets" / "icons" / "neuro_ia_logo.png"
        icon = QtGui.QIcon(str(path_icon))
        self.setWindowIcon(icon)

        self.setGeometry(45, 80, 1600, 900)

        step = max(1, round(sfreq * refresh_ms / 1000 * playback_rate))
        self.engine = PlaybackEngine(self.n_samples, window_size, step=step)

        SIGNAL_TYPES = [                            # noqa: N806
            ("EEG", range(0, 64), "#004CFF"),
            ("EMG", range(64, 65), "#FF6F00"),
            ("EOG", range(65, 67), "#4BD212"),
        ]

        def _color_for_channel(idx: int) -> str:
            for _, idx_range, color in SIGNAL_TYPES:
                if idx in idx_range:
                    return color
            return SIGNAL_TYPES[-1][2]

        self.channel_colors = [_color_for_channel(idx) for idx in self.channels_idx]
        legend_items = [(label, color) for label, _, color in SIGNAL_TYPES]

        self.display = SignalDisplayWidget(
            channel_names=self.channel_names,
            channel_colors=self.channel_colors,
            legend_items=legend_items,   # nuevo
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

        time_axis = np.arange(self.n_samples) / self.sfreq
        self.display.load_full_signal(time_axis, self.signal)
        self.display.set_events(self.events, self.sfreq)


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

        Convierte los límites de la ventana, expresados en muestras, a segundos
        utilizando la frecuencia de muestreo de la señal y actualiza el rango
        visible del widget de visualización. También actualiza la etiqueta de
        posición de los controles.

        Args:
            pos (int): Posición final de la ventana en muestras.

        Returns:
            None
        """
        start_sec = (pos - self.engine.window_size) / self.sfreq
        end_sec = pos / self.sfreq

        self.display.set_view_range(start_sec, end_sec) # type: ignore
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
                   sfreq: float = 500.0, refresh_ms: int = 20,
                   window_size: int = 1500, scale_factor: float = 50,
                   highpass: float | None = 0.5, notch: float | None = 50.0,
                   playback_rate: float = 0.25, lowpass: float | None = 100):
    """
    Inicia la aplicación gráfica para visualizar y reproducir una señal.

    Configura la ventana principal con la señal proporcionada, permitiendo
    seleccionar canales, cargar eventos BIDS y configurar los parámetros de
    visualización, filtrado y reproducción. La señal puede ser preparada
    mediante filtros pasa-altos, pasa-bajos y notch antes de su visualización,
    seguida de una normalización por canal.

    Args:
        signal (np.ndarray):
            Señal multicanal con forma `(n_canales, n_muestras)`.
        channel_names (list[str] | None, optional):
            Nombres de los canales disponibles. Si no se proporcionan, se
            generan nombres automáticamente.
        channels_idx (list[int] | None, optional):
            Índices de los canales que se desean visualizar. Si no se
            proporciona, se utilizan todos los canales.
        events_path (str | None, optional):
            Ruta al archivo TSV de eventos en formato BIDS. Si es `None`,
            no se cargan eventos.
        sfreq (float, optional):
            Frecuencia de muestreo de la señal en Hz. Por defecto, `500.0`.
        window_size (int, optional):
            Cantidad de muestras correspondientes a la ventana visible.
            Por defecto, `1500`.
        scale_factor (float, optional):
            Factor de escala vertical aplicado a las señales para su
            visualización. Por defecto, `50`.
        refresh_ms (int, optional):
            Intervalo de actualización de la reproducción en milisegundos.
            Por defecto, `20`.
        highpass (float | None, optional):
            Frecuencia de corte del filtro pasa-altos en Hz. Si es `None` o
            no se especifica, no se aplica este filtro. Por defecto, `0.5`.
        lowpass (float | None, optional):
            Frecuencia de corte del filtro pasa-bajos en Hz. Si es `None` o
            no se especifica, no se aplica este filtro. Por defecto, `100.0`.
        notch (float | None, optional):
            Frecuencia base del filtro notch en Hz. A partir de esta
            frecuencia se generan sus múltiplos por debajo de la frecuencia
            de Nyquist. Si es `None` o no es positiva, no se aplica el filtro.
            Por defecto, `50.0`.
        playback_rate (float, optional):
            Factor utilizado para controlar la velocidad de avance de la
            reproducción. Por defecto, `0.25`.

    Notes:
        Los parámetros de filtrado se utilizan para preparar la señal antes
        de su visualización. El intervalo `refresh_ms` y `playback_rate`
        determinan conjuntamente el avance de la reproducción entre
        actualizaciones.
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
        playback_rate=playback_rate,
        lowpass=lowpass,
        refresh_ms=refresh_ms
    )
    window.show()
    sys.exit(app.exec_())
