import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from pyqtgraph.Qt import QtCore


class SignalDisplayWidget(QWidget):
    """
    Widget para visualizar una o varias señales en un gráfico común.

    Contiene una curva por canal y utiliza los nombres proporcionados para
    identificar cada canal en el eje Y. Las señales se representan
    verticalmente en posiciones independientes para facilitar su visualización
    simultánea.

    La señal completa puede cargarse una única vez mediante
    `load_full_signal()`. Durante la reproducción, la ventana visible se
    desplaza mediante `set_view_range()` sin modificar los datos almacenados
    en las curvas.

    También permite mostrar eventos como líneas verticales en posiciones
    absolutas de la señal. Los eventos se cargan una única vez mediante
    `set_events()` y permanecen fijos mientras se modifica el rango visible.

    Args:
        channel_names (list): Lista con los nombres de los canales. Es
            obligatoria y no puede ser `None` ni estar vacía.
        window_size (int): Tamaño de la ventana temporal en muestras.
        scale_factor (float): Factor aplicado a las señales antes de
            representarlas.

    Attributes:
        channel_names (list): Nombres de los canales configurados.
        n_channels (int): Número de canales configurados.
        window_size (int): Tamaño de la ventana de visualización en muestras.
        scale_factor (float): Factor de escala utilizado para visualizar
            las señales.
        curves (list): Curvas utilizadas para representar cada canal.
        plot (pyqtgraph.PlotWidget): Gráfico principal de la señal.
    """

    def __init__(self, channel_names: list|None = None, window_size: int = 500, scale_factor: float = 50):
        """
        Inicializa el widget y configura el gráfico de señales.

        Requiere una lista no vacía de nombres de canales. A partir de los
        nombres recibidos se determina el número de canales y se crean las
        curvas correspondientes.

        También configura el gráfico, establece las etiquetas de los canales
        en el eje Y y prepara la lista utilizada para almacenar los marcadores
        de eventos.

        Args:
            channel_names (list): Nombres de los canales que serán representados.
                Debe ser una lista no vacía.
            window_size (int): Tamaño de la ventana temporal en muestras.
            scale_factor (float): Factor de escala utilizado al representar
                las señales.

        Returns:
            None

        Raises:
            ValueError: Si `channel_names` es `None` o está vacío.

        Notes:
            - El número de canales se obtiene mediante `len(channel_names)`.
            - Cada canal recibe una separación vertical fija de 200 unidades.
            - El gráfico utiliza un `QVBoxLayout`, ya que se muestra un único
            gráfico.
            - Las líneas de eventos se almacenan en `_event_lines`.
        """
        super().__init__()

        if not channel_names:
            raise ValueError("El widget requiere una lista válida en 'channel_names'.")
            
        self.channel_names = channel_names
        self.n_channels = len(channel_names)
        self.window_size = window_size
        self.scale_factor = scale_factor
        self._channel_spacing = 200

        self.layout = QVBoxLayout() # type: ignore
        self.setLayout(self.layout) # type: ignore

        label_style = {'color': '#000000', 'font-size': '14pt',
                       "font-family": "Times New Roman", "font-style": "italic"}

        # Gráfico de la Señal (Único)
        self.plot = pg.PlotWidget()
        self.plot.setTitle("Visualización de Señal", color="#000000", size="15pt", italic=True, bold=True)
        self.config_plot(self.plot, label_style)

        self.layout.addWidget(self.plot) # type: ignore

        self.init_curves()
        self.channel_ticks(self._channel_spacing)

        # ----- Líneas de eventos -----
        self._event_lines = []

    def config_plot(self, plot_widget, styles):
        """
        Configura las propiedades visuales y de representación del gráfico.

        Establece el fondo, la grilla, las etiquetas de los ejes, el
        autoajuste vertical y la configuración de reducción de datos.

        Args:
            plot_widget (pyqtgraph.PlotWidget): Gráfico que se desea configurar.
            styles (dict): Estilos utilizados para las etiquetas de los ejes.

        Returns:
            None

        Notes:
            - El fondo del gráfico se establece en blanco.
            - Se habilita la grilla en ambos ejes.
            - El eje Y se etiqueta como `"Canales"`.
            - El eje X se etiqueta como `"Muestras"`.
            - Se habilita el autoajuste del eje Y.
            - Se utiliza downsampling mediante el modo `"peak"`.
            - Se activa el recorte de los datos a la región visible.
        """
        plot_widget.setBackground('w')
        plot_widget.showGrid(x=True, y=True)
        plot_widget.setLabel("left", "Canales", **styles)
        plot_widget.setLabel("bottom", "Muestras", **styles)
        plot_widget.enableAutoRange(axis='y')
        plot_widget.setDownsampling(mode='peak', auto=True)
        plot_widget.setClipToView(True)

    def init_curves(self):
        """
        Inicializa una curva para cada canal configurado.

        Crea una curva vacía en el gráfico por cada elemento de
        `channel_names` y almacena las curvas en `curves`.

        Returns:
            None

        Notes:
            - El número de curvas creadas coincide con `n_channels`.
            - Las curvas se crean inicialmente sin datos.
        """
        self.curves = []
        for _ in range(self.n_channels):
            curve = self.plot.plot(pen="#000000")
            self.curves.append(curve)

    def channel_ticks(self, spacing):
        """
        Configura las etiquetas de los canales en el eje Y.

        Genera un marcador para cada nombre de canal y lo posiciona en el
        centro del espacio vertical asignado al canal.

        Args:
            spacing (float): Separación vertical asignada a cada canal.

        Returns:
            None

        Notes:
            - La primera etiqueta se posiciona en `spacing / 2`.
            - Cada canal posterior se desplaza verticalmente según `spacing`.
            - Se utilizan los nombres originales almacenados en
              `channel_names`.
        """
        ticks = []
        for i, name in enumerate(self.channel_names):
            channel_floor = i * spacing
            y_center = channel_floor + (spacing / 2)
            ticks.append((y_center, name))

        # Configuramos los ticks en el eje Y
        self.plot.getAxis('left').setTicks([ticks, []])

    def load_full_signal(self, x_data, y_data):
        """
        Carga la señal completa en las curvas del gráfico.

        Los datos se incorporan una única vez a las curvas de `pyqtgraph`.
        Posteriormente, el desplazamiento temporal de la visualización se realiza
        mediante `set_view_range()`, sin volver a extraer ni cargar ventanas de
        datos.

        Args:
            x_data (array-like): Vector de muestras compartido por todos los
                canales, típicamente generado mediante `np.arange(n_muestras)`.
            y_data (array-like): Señal completa con forma
                `(n_canales, n_muestras)`.

        Returns:
            None
        """
        if not isinstance(x_data, np.ndarray):
            x_data = np.array(x_data)

        for i, curve in enumerate(self.curves):
            offset = i * self._channel_spacing
            center_y = offset + (self._channel_spacing / 2)

            if i < len(y_data):
                curve.setData(x_data, (y_data[i] * self.scale_factor) + center_y)

    def set_view_range(self, start: int, end: int):
        """
        Actualiza el rango temporal visible del gráfico sin modificar los datos.

        Args:
            start (int): Primera muestra del rango temporal visible.
            end (int): Última muestra del rango temporal visible.

        Returns:
            None
        """
        self.plot.setXRange(start, end, padding=0)  # type: ignore

    def set_events(self, events):
        """
        Carga y representa todos los eventos en sus posiciones absolutas.

        Las líneas de eventos se agregan al gráfico utilizando `onset_sample` como
        posición sobre el eje X. Una vez cargadas, permanecen fijas mientras se
        modifica el rango temporal visible mediante `set_view_range()`.

        Args:
            events (list): Lista de eventos que contienen `onset_sample` y
                `trial_type` (ver `utils.bids_events.load_bids_events`).

        Returns:
            None

        Notes:
            Los eventos se representan en la misma escala absoluta de muestras
            utilizada por `load_full_signal()`, por lo que no es necesario
            recalcularlos al desplazar la ventana visible.
        """
        self._clear_event_lines()

        for ev in events:
            line = pg.InfiniteLine(
                pos=ev.onset_sample, angle=90,
                pen=pg.mkPen("#D62728", width=1.5, style=QtCore.Qt.DashLine),  # type: ignore
                label=ev.trial_type,
                labelOpts={"position": 0.95, "color": "#D62728"},
            )
            self.plot.addItem(line)
            self._event_lines.append(line)

    def _clear_event_lines(self):
        """
        Elimina las líneas de eventos actualmente representadas.

        Recorre los marcadores almacenados en `_event_lines`, los elimina
        del gráfico y posteriormente vacía la lista.

        Returns:
            None
        """
        for line in self._event_lines:
            self.plot.removeItem(line)
        self._event_lines = []
