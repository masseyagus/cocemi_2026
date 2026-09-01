from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class PlaybackControls(QWidget):
    """
    Representa la barra de controles de reproducción de una señal.

    Proporciona botones para retroceder, reproducir o pausar y avanzar,
    además de una etiqueta que muestra la posición actual dentro de la
    señal.

    La clase no interactúa directamente con el motor de reproducción.
    En su lugar, emite señales cuando el usuario pulsa cada uno de los
    botones, permitiendo que otro componente gestione las acciones
    correspondientes.

    Attributes:
        prev_clicked (pyqtSignal): Señal emitida al pulsar el botón
            de retroceso.
        next_clicked (pyqtSignal): Señal emitida al pulsar el botón
            de avance.
        play_pause_clicked (pyqtSignal): Señal emitida al pulsar el
            botón de reproducción o pausa.
        btn_prev (QPushButton): Botón utilizado para retroceder.
        btn_play_pause (QPushButton): Botón utilizado para alternar
            entre reproducción y pausa.
        btn_next (QPushButton): Botón utilizado para avanzar.
        label_position (QLabel): Etiqueta que muestra la posición
            actual y el total de muestras.
    """

    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    play_pause_clicked = pyqtSignal()

    def __init__(self):
        """
        Inicializa los controles de reproducción y configura su disposición.

        Crea los botones de retroceso, reproducción/pausa y avance, junto
        con la etiqueta de posición. Los elementos se organizan
        horizontalmente y se conectan sus eventos `clicked` a las señales
        correspondientes de la clase.

        Returns:
            None

        Notes:
            - El botón de reproducción/pausa comienza mostrando
              `"⏸ Pausar"`.
            - La etiqueta de posición comienza mostrando `"Muestra: 0"`.
            - Se añade un espacio flexible entre los controles y la
              etiqueta de posición.
        """
        super().__init__()

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.btn_prev = QPushButton("⏮ Retroceder")
        self.btn_play_pause = QPushButton("⏸ Pausar")
        self.btn_next = QPushButton("Avanzar ⏭")
        self.label_position = QLabel("Muestra: 0")

        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_play_pause)
        layout.addWidget(self.btn_next)
        layout.addStretch(1)
        layout.addWidget(self.label_position)

        self.btn_prev.clicked.connect(self.prev_clicked.emit)
        self.btn_next.clicked.connect(self.next_clicked.emit)
        self.btn_play_pause.clicked.connect(self.play_pause_clicked.emit)

    def set_paused_label(self, is_paused: bool):
        """
        Actualiza el texto del botón de reproducción/pausa.

        Args:
            is_paused (bool): Indica si el estado actual es pausado.
                Cuando es `True`, el botón muestra `"▶ Reanudar"`;
                cuando es `False`, muestra `"⏸ Pausar"`.

        Returns:
            None
        """
        self.btn_play_pause.setText("▶ Reanudar" if is_paused else "⏸ Pausar")

    def set_position_label(self, pos: int, n_samples: int):
        """
        Actualiza la etiqueta con la posición actual y el total de muestras.

        Args:
            pos (int): Posición actual de reproducción, expresada en
                muestras.
            n_samples (int): Cantidad total de muestras de la señal.

        Returns:
            None

        Notes:
            - La etiqueta se establece con el formato
              `"Muestra: {pos} / {n_samples}"`.
        """
        self.label_position.setText(f"Muestra: {pos} / {n_samples}")
