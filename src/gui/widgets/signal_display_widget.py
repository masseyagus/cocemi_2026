import numpy as np  #type: ignore
import pyqtgraph as pg  #type: ignore
from PyQt5.QtWidgets import QVBoxLayout, QWidget  #type: ignore
from pyqtgraph.Qt import QtCore, QtGui  #type: ignore


class SignalDisplayWidget(QWidget):
    """
    Widget para visualizar una o varias señales en un gráfico común.

    Contiene una curva por canal y utiliza los nombres proporcionados para
    identificar cada canal en el eje Y. Las señales se representan
    verticalmente en posiciones independientes para facilitar su visualización
    simultánea. Cada curva puede utilizar un color específico proporcionado
    mediante `channel_colors`.

    La señal completa puede cargarse una única vez mediante
    `load_full_signal()`. El eje X utiliza tiempos expresados en segundos.
    Durante la reproducción, la ventana visible se desplaza mediante
    `set_view_range()` sin modificar los datos almacenados en las curvas.

    También permite mostrar eventos como líneas verticales en posiciones
    absolutas de tiempo. Los eventos se cargan una única vez mediante
    `set_events()` y sus posiciones se convierten de muestras a segundos
    utilizando la frecuencia de muestreo proporcionada. Una vez cargados,
    permanecen fijos mientras se modifica el rango visible.

    Puede mostrar una leyenda con los tipos de señal y sus colores mediante
    `legend_items`.

    Args:
        channel_names (list): Lista con los nombres de los canales. Es
            obligatoria y no puede ser `None` ni estar vacía.
        window_size (int): Tamaño de la ventana temporal en muestras.
        scale_factor (float): Factor aplicado a las señales antes de
            representarlas.
        channel_colors (list | None): Lista de colores utilizados para las
            curvas de los canales. Si es `None`, se utiliza el color
            `"#004CFF"` para todos los canales.
        legend_items (list | None): Elementos de la leyenda. Cada elemento
            debe contener una etiqueta de tipo de señal y su color. Si es
            `None`, no se muestra la leyenda.

    Attributes:
        channel_names (list): Nombres de los canales configurados.
        channel_colors (list): Colores utilizados para representar los
            canales.
        legend_items (list): Elementos utilizados para construir la leyenda
            por tipo de señal.
        n_channels (int): Número de canales configurados.
        window_size (int): Tamaño de la ventana de visualización en muestras.
        scale_factor (float): Factor de escala utilizado para visualizar
            las señales.
        curves (list): Curvas utilizadas para representar cada canal.
        plot (pyqtgraph.PlotWidget): Gráfico principal de la señal.
    """

    def __init__(self, channel_names: list|None = None, window_size: int = 500, 
                 scale_factor: float = 50, channel_colors:list|None=None, legend_items:list|None=None):
        """
        Inicializa el widget y configura el gráfico de señales.

        Requiere una lista no vacía de nombres de canales. A partir de los
        nombres recibidos se determina el número de canales y se crean las
        curvas correspondientes.

        También configura el gráfico, establece las etiquetas de los canales
        en el eje Y, asigna los colores de las curvas, crea la leyenda por tipo
        de señal cuando se proporciona y prepara la lista utilizada para
        almacenar los marcadores de eventos.

        Args:
            channel_names (list): Nombres de los canales que serán representados.
                Debe ser una lista no vacía.
            window_size (int): Tamaño de la ventana temporal en muestras.
            scale_factor (float): Factor de escala utilizado al representar
                las señales.
            channel_colors (list | None): Colores utilizados para representar
                las curvas de los canales. Si es `None`, se utiliza
                `"#004CFF"` para todos los canales.
            legend_items (list | None): Elementos utilizados para construir la
                leyenda por tipo de señal. Cada elemento contiene una etiqueta
                y el color correspondiente. Si es `None` o está vacío, no se
                agrega una leyenda.

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
            - El eje temporal del gráfico se expresa en segundos.
            - La leyenda se configura con una columna por elemento recibido en
            `legend_items`.
        """
        super().__init__()

        if not channel_names:
            raise ValueError("El widget requiere una lista válida en 'channel_names'.")
            
        self.channel_names = channel_names
        self.channel_colors = channel_colors or ["#004CFF"] * self.n_channels
        self.legend_items = legend_items or []

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
        self._add_signal_type_legend()

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
            - El eje X se etiqueta como `"Tiempos (s)"`.
            - Se habilita el autoajuste del eje Y.
            - Se utiliza downsampling mediante el modo `"peak"`.
            - Se activa el recorte de los datos a la región visible.
        """
        plot_widget.setBackground('w')
        plot_widget.showGrid(x=True, y=True)
        plot_widget.setLabel("left", "Canales", **styles)
        plot_widget.setLabel("bottom", "Tiempos (s)", **styles)
        plot_widget.enableAutoRange(axis='y')
        plot_widget.setDownsampling(mode='peak', auto=True)
        plot_widget.setClipToView(True)

    def init_curves(self):
        """
        Inicializa una curva para cada canal configurado.

        Crea una curva vacía en el gráfico por cada elemento de
        `channel_names`, utilizando el color correspondiente de
        `channel_colors`, y almacena las curvas en `curves`.

        Returns:
            None

        Notes:
            - El número de curvas creadas coincide con `n_channels`.
            - Las curvas se crean inicialmente sin datos.
            - Cada curva utiliza el color indicado en la posición correspondiente
            de `channel_colors`.
            - Las curvas se representan con un ancho de trazo de 2.
        """
        self.curves = []
        for i in range(self.n_channels):
            curve = self.plot.plot(pen=pg.mkPen(self.channel_colors[i], width=2))
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
        El vector del eje X representa los tiempos de la señal en segundos.
        Posteriormente, el desplazamiento temporal de la visualización se realiza
        mediante `set_view_range()`, sin volver a extraer ni cargar ventanas de
        datos.

        Args:
            x_data (array-like): Vector de tiempos en segundos compartido por
                todos los canales.
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

        Los límites del rango corresponden a tiempos expresados en segundos,
        utilizando la misma escala temporal que el eje X de las curvas.

        Args:
            start (float): Tiempo inicial del rango visible, en segundos.
            end (float): Tiempo final del rango visible, en segundos.

        Returns:
            None
        """
        self.plot.setXRange(start, end, padding=0)  # type: ignore

    def set_events(self, events, sfreq):
        """
        Carga y representa todos los eventos en sus posiciones temporales
        absolutas.

        Convierte la posición de cada evento desde muestras a segundos mediante
        la frecuencia de muestreo proporcionada y agrega una línea vertical en
        la posición temporal correspondiente. Las etiquetas de los eventos se
        muestran con un tamaño de fuente de 14 puntos. Una vez cargados, los
        eventos permanecen fijos mientras se modifica el rango temporal visible
        mediante `set_view_range()`.

        Args:
            events (list): Lista de eventos que contienen `onset_sample` y
                `trial_type` (ver `utils.bids_events.load_bids_events`).
            sfreq (float): Frecuencia de muestreo utilizada para convertir
                `onset_sample` de muestras a segundos.

        Returns:
            None

        Notes:
            Los eventos se representan en la misma escala temporal en segundos
            utilizada por el eje X de `load_full_signal()`, por lo que no es
            necesario recalcularlos al desplazar la ventana visible.

            Las etiquetas de los eventos utilizan una fuente de tamaño
            fijo de 14 puntos.
        """
        self._clear_event_lines()

        for ev in events: # hacer más grandes las letras (markers)

            pos_sec = ev.onset_sample / sfreq
            
            line = pg.InfiniteLine(
                pos=pos_sec, angle=90,
                pen=pg.mkPen("#D62728", width=1.5, style=QtCore.Qt.DashLine),  # type: ignore
                label=ev.trial_type,
                labelOpts={"position": 0.95, "color": "#D62728"},
            )

            font = QtGui.QFont()
            font.setPointSize(14)
            line.label.setFont(font)

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

    def _add_signal_type_legend(self):
        """
        Agrega una leyenda al gráfico para identificar los tipos de señal.

        Utiliza los elementos proporcionados mediante `legend_items` para crear
        una entrada por tipo de señal, asociando cada etiqueta con una muestra
        del color correspondiente.

        Returns:
            None

        Notes:
            - Si `legend_items` está vacío, no se agrega ninguna leyenda.
            - La leyenda se posiciona en la esquina superior izquierda del
            gráfico.
            - Se utiliza una columna por cada elemento de `legend_items`.
            - Las etiquetas de la leyenda se muestran en color negro.
            - Las muestras de la leyenda utilizan un trazo de ancho 2 con el
            color asociado a cada tipo de señal.
        """
        if not self.legend_items:
            return

        total_columns = len(self.legend_items)

        legend = self.plot.addLegend(
            offset=(10, 10), 
            labelTextSize='15pt', 
            colCount=total_columns
        )

        for label, color in self.legend_items:
            sample = pg.PlotDataItem(pen=pg.mkPen(color, width=2))
            label_negro = f'<span style="color: black;">{label}</span>'
            legend.addItem(sample, label_negro)
