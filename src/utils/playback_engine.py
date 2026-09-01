from PyQt5.QtCore import QObject, pyqtSignal


class PlaybackEngine(QObject):
    """
    Motor de reproducción sobre una señal cargada en memoria.

    Mantiene la posición actual de reproducción en muestras y controla
    el avance, retroceso, pausa y reproducción en loop. No almacena los
    datos de la señal, sino únicamente su cantidad total de muestras y
    el tamaño de la ventana de visualización.

    Cada vez que la posición cambia, emite la señal `position_changed`
    para que el componente encargado de la visualización actualice los
    datos mostrados. Cuando la reproducción alcanza el final de la señal,
    reinicia la posición al final de una ventana completa y emite
    `looped`.

    Args:
        n_samples (int): Cantidad total de muestras de la señal.
        window_size (int): Cantidad de muestras de la ventana visible.
            Si es mayor que `n_samples`, se ajusta al número total de
            muestras.
        step (int): Cantidad de muestras que se avanza en cada llamada
            a `tick()`. Se establece como mínimo en 1.

    Notes:
        - La posición inicial es igual a `window_size`, por lo que se
          considera que comienza con una ventana completa visible.
        - `position_changed` emite la nueva posición cada vez que
          `_set_pos()` actualiza la posición.
        - `looped` se emite cuando la nueva posición alcanza o supera
          `n_samples`.
        - Las posiciones menores que `window_size` se ajustan a
          `window_size`.
    """

    position_changed = pyqtSignal(int)  # nueva posición (última muestra visible)
    looped = pyqtSignal()               # se emite cada vez que la señal vuelve al inicio

    def __init__(self, n_samples: int, window_size: int, step: int = 1):
        """
        Inicializa el motor de reproducción.

        Args:
            n_samples (int): Cantidad total de muestras de la señal.
            window_size (int): Tamaño de la ventana visible, en muestras.
            step (int): Cantidad de muestras de avance utilizada en cada
                llamada a `tick()`. Se establece como mínimo en 1.

        Returns:
            None

        Notes:
            - `window_size` se limita a `n_samples` cuando la señal es
              más corta que la ventana solicitada.
            - La reproducción comienza en la posición `window_size`.
            - El estado inicial es de reproducción, no de pausa.
        """
        super().__init__()
        self.n_samples = n_samples
        self.window_size = min(window_size, n_samples)
        self.step = max(1, step)
        self.is_paused = False
        self.pos = self.window_size  # arranca con una ventana completa visible

    # ---- Reproducción automática (llamado por el QTimer de MainWindow) ----
    def tick(self):
        """
        Avanza la posición de reproducción automáticamente.

        Si el motor está pausado, no realiza ninguna acción. En caso
        contrario, incrementa la posición actual en `step` muestras
        mediante `_set_pos()`.

        Returns:
            None
        """
        if self.is_paused:
            return
        self._set_pos(self.pos + self.step)

    # ---- Controles manuales ----
    def play_pause(self) -> bool:
        """
        Alterna entre el estado de pausa y reproducción.

        Invierte el estado actual de `is_paused` y devuelve el nuevo
        estado.

        Returns:
            bool: `True` si el motor queda pausado y `False` si queda
                en reproducción.
        """
        """Alterna pausa/reproducción. Devuelve el nuevo estado (True = pausado)."""
        self.is_paused = not self.is_paused
        return self.is_paused

    def step_forward(self):
        """
        Avanza una ventana completa de reproducción.

        Incrementa la posición actual en `window_size` muestras y aplica
        las restricciones de posición mediante `_set_pos()`.

        Returns:
            None
        """
        """Salta una ventana completa hacia adelante (usado por el botón 'Avanzar')."""
        self._set_pos(self.pos + self.window_size)

    def step_backward(self):
        """
        Retrocede una ventana completa de reproducción.

        Reduce la posición actual en `window_size` muestras y aplica
        las restricciones de posición mediante `_set_pos()`.

        Returns:
            None
        """
        self._set_pos(self.pos - self.window_size)

    def seek(self, sample: int):
        """
        Establece la posición de reproducción en una muestra determinada.

        La posición solicitada se procesa mediante `_set_pos()`, por lo
        que se ajusta si se encuentra fuera de los límites permitidos.

        Args:
            sample (int): Posición de muestra a la que se desea saltar.

        Returns:
            None
        """
        self._set_pos(sample)

    # ---- Interno ----
    def _set_pos(self, new_pos: int):
        """
        Actualiza la posición de reproducción y emite las señales correspondientes.

        Si la nueva posición alcanza o supera `n_samples`, reinicia la
        reproducción en `window_size` y emite `looped`. Si la posición
        es menor que `window_size`, la ajusta a `window_size`.

        Finalmente, almacena la posición resultante en `pos` y emite
        `position_changed` con dicha posición.

        Args:
            new_pos (int): Nueva posición de reproducción en muestras.

        Returns:
            None

        Notes:
            - El reinicio al alcanzar el final constituye el comportamiento
              de loop.
            - La posición nunca queda por debajo de `window_size`.
            - `position_changed` se emite incluso cuando la posición
              resultante coincide con la posición anterior.
        """
        if new_pos >= self.n_samples:
            new_pos = self.window_size  # loop: reinicia dejando una ventana llena
            self.looped.emit()
        elif new_pos < self.window_size:
            new_pos = self.window_size

        self.pos = new_pos
        self.position_changed.emit(self.pos)
