import json
import time

import numpy as np  #type: ignore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg  #type: ignore
from matplotlib.figure import Figure  #type: ignore
from mne.defaults import HEAD_SIZE_DEFAULT  #type: ignore
from mne.viz import plot_topomap  #type: ignore
from PyQt5.QtCore import QEvent, Qt  #type: ignore
from PyQt5.QtWidgets import QVBoxLayout, QWidget  #type: ignore


def _parse_xy(value) -> tuple:
    """
    Convierte una entrada del JSON de posiciones en una tupla `(x, y)`.

    Acepta el formato `{"X": x, "Y": y}` (también en minúsculas) y el
    formato `[x, y]`.

    Args:
        value (dict | list): Entrada del JSON para un electrodo.

    Returns:
        tuple: `(x, y)` como floats.
    """
    if isinstance(value, dict):
        x = value["X"] if "X" in value else value["x"]
        y = value["Y"] if "Y" in value else value["y"]
        return float(x), float(y)
    return float(value[0]), float(value[1])


def load_channel_positions(montage_path, channels_idx: list, channel_names: list | None = None,
                           n_eeg_channels: int | None = None):
    """
    Asocia cada canal visualizado con su posición 2D en el montage.

    Para cada fila de la señal visualizada (cuyo índice original en el
    registro está en `channels_idx`) busca el nombre del electrodo y su
    posición en el JSON:

    - Si se proporciona `channel_names` (indexado por índice ORIGINAL de
      canal), se empareja por nombre, sin distinguir mayúsculas.
    - Si no, se asume que el canal original `k` corresponde al k-ésimo
      electrodo del JSON (el orden de las claves del archivo).

    Los canales sin posición (EMG, EOG, o índices fuera de
    `n_eeg_channels`) quedan excluidos del mapa.

    Args:
        montage_path (str | Path): Ruta al JSON de posiciones
            (`{"Fp1": {"X": ..., "Y": ...}, ...}`).
        channels_idx (list): Índices originales de los canales que
            componen las filas de la señal visualizada, en ese orden.
        channel_names (list, optional): Nombres de todos los canales del
            registro, indexados por índice original.
        n_eeg_channels (int, optional): Solo los canales originales con
            índice menor a este valor pueden tener posición.

    Returns:
        tuple: `(rows, names, positions)` con las filas de la señal que sí
        tienen posición, sus nombres de electrodo y un array `(n, 2)`.

    Raises:
        ValueError: Si ningún canal obtiene posición (típicamente por un
            desajuste de nombres entre `channel_names` y el JSON).
    """
    with open(montage_path, "r", encoding="utf-8") as f:
        montage = json.load(f)

    montage_names = list(montage.keys())
    lookup = {name.lower(): _parse_xy(v) for name, v in montage.items()}

    rows, names, xy = [], [], []
    for row, k in enumerate(channels_idx):
        if n_eeg_channels is not None and k >= n_eeg_channels:
            continue

        if channel_names is not None:
            if k >= len(channel_names):
                continue
            name = channel_names[k]
        elif k < len(montage_names):
            name = montage_names[k]
        else:
            continue

        pos = lookup.get(str(name).lower())
        if pos is None:
            continue

        rows.append(row)
        names.append(name)
        xy.append(pos)

    if not rows:
        raise ValueError(
            f"Ningún canal obtuvo posición desde '{montage_path}'. Si pasaste "
            "'channel_names', verificá que coincidan con las claves del JSON."
        )

    return rows, names, np.array(xy, dtype=float)


class TopomapWidget(QWidget):
    """
    Mapa topográfico de energía por canal, con la estética de MNE.

    El dibujo lo hace `mne.viz.plot_topomap` (contorno de cabeza, nariz,
    orejas, interpolación, curvas de nivel y sensores), embebido en un
    canvas de matplotlib. El widget calcula la energía (RMS) de la ventana
    visible para cada canal con posición y redibuja el mapa.

    Está pensado para flotar sobre otro widget (ver `attach_to`): queda
    anclado abajo a la derecha del widget anfitrión, superpuesto a su
    contenido, y sigue sus cambios de tamaño.

    Args:
        rows (list): Filas de la señal visualizada que tienen posición.
        positions (np.ndarray): Posiciones `(n, 2)` de esas filas, en las
            unidades del JSON (no hace falta que estén en metros).
        names (list, optional): Nombres de electrodo de esas filas. Si
            incluye `"Cz"`, se usa como centro de la cabeza.
        cmap (str): Colormap de matplotlib. `"RdBu_r"` replica el aspecto
            habitual de MNE; `"Reds"` es el que MNE elige por defecto
            cuando todos los valores son no negativos.
        vlim (tuple): Límites `(vmin, vmax)` de color. `(None, None)`
            autoescala en cada cuadro, como hace MNE.
        contours (int): Cantidad de curvas de nivel.
        res (int): Resolución de la grilla de interpolación.
        max_fps (float): Máximo de redibujados por segundo. Redibujar
            cuesta unos ~15-20 ms, así que se limita para no restar
            fluidez a la señal.
        size (int): Lado del widget, en píxeles.
        title (str): Título del mapa.
        head_center (tuple, optional): Centro `(x, y)` de la cabeza. Por
            defecto, la posición de `"Cz"` o el centroide de los sensores.
        head_radius (float, optional): Radio de la cabeza. Por defecto,
            1.08 veces la distancia máxima entre el centro y un sensor.

    Raises:
        ValueError: Si `rows` está vacío.

    Notes:
        - Requiere `mne>=1.2` (parámetro `vlim`).
        - Si los sensores no cubren toda la cabeza (por ejemplo, sin
          electrodos occipitales), MNE extrapola esa zona: no representa
          energía medida.
    """

    def __init__(self, rows: list, positions: np.ndarray, names: list | None = None,
                 cmap: str = "RdBu_r", vlim: tuple = (None, None), contours: int = 6,
                 res: int = 64, max_fps: float = 8.0, size: int = 750,
                 title: str = "Energía (RMS)", head_center: tuple | None = None,
                 head_radius: float | None = None):
        """
        Inicializa el widget de mapa topográfico.

        El widget utiliza las posiciones espaciales de los electrodos para
        representar la magnitud RMS de las señales mediante un mapa topográfico.
        La actualización del mapa se limita a la frecuencia indicada mediante
        `fps`.

        Args:
            parent (QWidget | None): Widget padre de Qt.
            positions (dict | None): Diccionario con las posiciones espaciales de
                los canales EEG.
            size (int): Tamaño inicial del área utilizada para representar el
                mapa topográfico, en píxeles.
            vlim (tuple): Límites inferior y superior utilizados para la escala
                de valores del mapa. Los valores `None` permiten determinar
                automáticamente los límites.
            cmap (str): Nombre del mapa de colores utilizado para representar los
                valores de la señal.
            fps (float): Frecuencia máxima de actualización del mapa topográfico,
                expresada en cuadros por segundo.
            head_size (float): Factor de escala aplicado a las coordenadas
                espaciales de los electrodos para ajustar el tamaño de la cabeza
                representada.
        """
        super().__init__()

        if not rows:
            raise ValueError("TopomapWidget requiere al menos un canal con posición.")

        self._rows = list(rows)
        self._pos = np.asarray(positions, dtype=float)
        self._cmap = cmap
        self._vlim = vlim
        self._contours = contours
        self._res = res
        self._title = title
        self._min_interval = 1.0 / max_fps if max_fps > 0 else 0.0
        self._last_draw = 0.0
        self._host = None
        self._margin = (16, 60)

        # Geometría de la cabeza: centro en Cz (o centroide) y radio según
        # la extensión de los sensores
        if head_center is None:
            lowered = [str(n).lower() for n in (names or [])]
            head_center = (
                tuple(self._pos[lowered.index("cz")]) if "cz" in lowered
                else tuple(self._pos.mean(axis=0))
            )
        if head_radius is None:
            distances = np.linalg.norm(self._pos - np.array(head_center), axis=1)
            head_radius = float(distances.max()) * 1.08

        center = np.array(head_center, dtype=float)
        self._pos_mne = (self._pos - center) / float(head_radius) * HEAD_SIZE_DEFAULT
        self._sphere = (0.0, 0.0, 0.0, HEAD_SIZE_DEFAULT)

        self._build_ui(size)

    @classmethod
    def from_montage(cls, montage_path, channels_idx: list, channel_names: list | None = None,
                     n_eeg_channels: int | None = None, **kwargs) -> "TopomapWidget":
        """
        Crea el widget leyendo las posiciones desde un JSON de montage.

        Args:
            montage_path (str | Path): Ruta al JSON de posiciones.
            channels_idx (list): Índices originales de los canales de la
                señal visualizada (`MainWindow.channels_idx`).
            channel_names (list, optional): Nombres de todos los canales
                del registro. Si es `None`, el canal `k` se asocia al
                k-ésimo electrodo del JSON.
            n_eeg_channels (int, optional): Cantidad de canales EEG al
                inicio del registro; el resto no lleva posición.
            **kwargs: Parámetros de `TopomapWidget.__init__`.

        Returns:
            TopomapWidget: Widget listo para recibir datos.
        """
        rows, names, positions = load_channel_positions(
            montage_path, channels_idx, channel_names, n_eeg_channels
        )
        return cls(rows, positions, names=names, **kwargs)

    def _build_ui(self, size: int):
        """
        Construye el panel: figura de matplotlib con un único eje y estilo
        de tarjeta blanca con borde.

        Args:
            size (int): Lado del widget, en píxeles.

        Returns:
            None
        """
        self.setObjectName("topomap")
        self.setAttribute(Qt.WA_StyledBackground, True)  # type: ignore
        self.setStyleSheet(
            "#topomap { background-color: white; border: 1px solid #9a9a9a; border-radius: 8px; }"
        )
        self.setFixedSize(size, size)

        self._fig = Figure(figsize=(5, 5), dpi=100, facecolor="white")
        self._fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.90)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self._fig)

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._canvas)
        self.setLayout(layout)

    def attach_to(self, host: QWidget, margin: tuple = (16, 60)):
        """
        Superpone el widget al anfitrión, anclado abajo a la derecha.

        El widget pasa a ser hijo de `host` (fuera de cualquier layout) y
        se reposiciona automáticamente cuando `host` cambia de tamaño.

        Args:
            host (QWidget): Widget sobre el que se superpone el mapa.
            margin (tuple): Distancia `(derecha, abajo)` al borde del
                anfitrión, en píxeles. El margen inferior por defecto deja
                libre el eje X del gráfico.

        Returns:
            None
        """
        self._host = host
        self._margin = margin
        self.setParent(host)
        host.installEventFilter(self)
        self._reposition()
        self.show()
        self.raise_()

    def eventFilter(self, obj, event):  # type: ignore
        """
        Reposiciona el mapa cuando el anfitrión cambia de tamaño.

        Args:
            obj (QObject): Objeto que recibe el evento.
            event (QEvent): Evento recibido.

        Returns:
            bool: Siempre delega el evento al comportamiento por defecto.
        """
        if obj is self._host and event.type() == QEvent.Resize: # type: ignore
            self._reposition()
        return super().eventFilter(obj, event)

    def _reposition(self):
        """
        Ancla el widget abajo a la derecha del anfitrión.

        Returns:
            None
        """
        if self._host is None:
            return
        x = self._host.width() - self.width() - self._margin[0]
        y = self._host.height() - self.height() - self._margin[1]
        self.move(max(x, 0), max(y, 0))
        self.raise_()

    def update_from_window(self, window: np.ndarray):
        """
        Calcula la energía (RMS) de la ventana visible y redibuja el mapa.

        Si el último dibujo fue hace menos de `1 / max_fps` segundos, no
        hace nada (ni siquiera calcula la energía).

        Args:
            window (np.ndarray): Ventana visible con forma
                `(n_canales_visualizados, n_muestras)`, con las filas en el
                mismo orden que `channels_idx` al crear el widget.

        Returns:
            None
        """
        now = time.perf_counter()
        if now - self._last_draw < self._min_interval:
            return

        window = np.asarray(window)
        if window.ndim != 2 or window.shape[1] == 0:
            return

        self._last_draw = now
        rms_all = np.sqrt(np.einsum("ij,ij->i", window, window) / window.shape[1])
        self._draw(rms_all[self._rows])

    def _draw(self, values: np.ndarray):
        """
        Dibuja el mapa con `mne.viz.plot_topomap` para los valores dados.

        Args:
            values (np.ndarray): Energía de cada canal con posición, en el
                orden de `rows`.

        Returns:
            None
        """
        self._ax.clear()
        plot_topomap(
            values, self._pos_mne,
            sphere=self._sphere, axes=self._ax, show=False,
            cmap=self._cmap, vlim=self._vlim,
            contours=self._contours, res=self._res,
        )
        self._ax.set_title(self._title, fontsize=10, fontweight="bold")
        self._canvas.draw_idle()
