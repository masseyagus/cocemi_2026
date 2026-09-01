# NeuroIA GUI

Visor y reproductor interactivo de señales biomédicas multicanal desarrollado en Python.

La aplicación permite cargar una señal almacenada en formato `.npy` junto con un archivo de eventos `.tsv`, visualizar simultáneamente todos los canales de la señal y sus respectivos marcadores, y recorrer la señal mediante controles de reproducción.

---


## Objetivo

El objetivo principal del proyecto es proporcionar una herramienta sencilla para **visualizar y reproducir señales biomédicas multicanal junto con sus eventos temporales**.

La aplicación busca facilitar la inspección de señales previamente adquiridas, permitiendo recorrerlas temporalmente y relacionar visualmente los cambios observados en los canales con los eventos registrados durante la adquisición.

---

## Características

* Carga de señales desde archivos `.npy`.
* Soporte para señales multicanal.
* Visualización simultánea de todos los canales.
* Visualización de nombres de canales.
* Carga de eventos desde archivos `.tsv` en formato BIDS.
* Representación de eventos como marcadores sobre la señal.
* Reproducción continua de la señal.
* Pausa y reanudación de la reproducción.
* Avance y retroceso por ventanas.
* Reproducción en bucle.
* Indicador de posición actual dentro de la señal.
* Interfaz gráfica basada en Qt y PyQtGraph.

---

## Funcionamiento

La aplicación recibe dos archivos principales:

### Señal

La señal debe almacenarse en un archivo NumPy (`.npy`) como un array bidimensional:

```text
(n_canales, n_muestras)
```

Por ejemplo, una señal con 8 canales y 100.000 muestras tendrá:

```python
signal.shape
# (8, 100000)
```

Cada fila representa un canal y cada columna una muestra temporal.

### Eventos

Los eventos se proporcionan mediante un archivo `events.tsv` siguiendo la estructura utilizada por BIDS.

Como mínimo, el archivo debe contener la columna:

```text
onset
```

También puede incluir:

```text
duration
trial_type
```

Un ejemplo:

```text
onset	duration	trial_type
2.50	0.50	stimulus
5.00	1.00	response
8.25	0.25	stimulus
```

Los valores de `onset` y `duration` se expresan en segundos y son convertidos a muestras utilizando la frecuencia de muestreo de la señal.

---

## Interfaz

La aplicación está compuesta por tres elementos principales:

### Visualización de la señal

`SignalDisplayWidget` se encarga de representar los canales de la señal y los eventos correspondientes a la ventana temporal actualmente visible.

Cada canal se representa de manera independiente y se desplaza verticalmente para facilitar la visualización simultánea de múltiples señales.

Los eventos que se encuentran dentro de la ventana visible se muestran mediante marcadores verticales.

### Motor de reproducción

`PlaybackEngine` controla la posición actual dentro de la señal.

Es responsable de:

* avanzar la reproducción;
* retroceder;
* pausar y reanudar;
* desplazarse entre ventanas;
* reiniciar la reproducción al alcanzar el final de la señal.

El motor es independiente de la interfaz gráfica y comunica los cambios de posición mediante señales de Qt.

### Controles de reproducción

`PlaybackControls` proporciona los controles necesarios para interactuar con la reproducción y visualizar la posición actual.

---

## Arquitectura

La aplicación mantiene separadas las responsabilidades principales:

```text
                         MainWindow
                             │
             ┌───────────────┼───────────────┐
             │               │               │
             ▼               ▼               ▼
      PlaybackEngine   SignalDisplayWidget  PlaybackControls
             │               │
             │               │
             ▼               ▼
       Posición de       Visualización
       reproducción       de la señal
             │               │
             └───────┬───────┘
                     │
                     ▼
                 Eventos BIDS
```

`MainWindow` funciona como componente de integración. Se encarga de conectar el motor de reproducción con la visualización y los controles, evitando que estos componentes tengan que conocerse directamente entre sí.

---

## Uso

### Línea de comandos

El visor puede iniciarse mediante:

```bash
python main.py señal.npy
```

Para cargar también los eventos:

```bash
python main.py señal.npy --events eventos.tsv
```

Es posible especificar la frecuencia de muestreo:

```bash
python main.py señal.npy --events eventos.tsv --sfreq 250
```

También pueden configurarse el tamaño de la ventana y la escala vertical:

```bash
python main.py señal.npy \
    --events eventos.tsv \
    --sfreq 250 \
    --window 1500 \
    --scale 50
```

### Argumentos disponibles

| Argumento  | Descripción                              | Por defecto |
| ---------- | ---------------------------------------- | ----------: |
| `signal`   | Archivo `.npy` con la señal              | Obligatorio |
| `--events` | Archivo `events.tsv` con los eventos     |      `None` |
| `--sfreq`  | Frecuencia de muestreo en Hz             |       `250` |
| `--window` | Tamaño de la ventana visible en muestras |      `1500` |
| `--scale`  | Escala vertical entre canales            |        `50` |

---

## Uso desde Python

También es posible iniciar el visor directamente desde Python:

```python
import numpy as np

from gui.main_window import launch_viewer

signal = np.load("signal.npy")

launch_viewer(
    signal=signal,
    events_path="events.tsv",
    sfreq=250.0,
)
```

Los nombres de los canales pueden proporcionarse mediante `channel_names`:

```python
channel_names = [
    "Fp1",
    "Fp2",
    "C3",
    "C4",
    "O1",
    "O2",
]

launch_viewer(
    signal=signal,
    channel_names=channel_names,
    events_path="events.tsv",
    sfreq=250.0,
)
```

---

## Estructura del proyecto

Una organización general del proyecto es:

```text
signalprocessing/
│
├── gui/
│   ├── main_window.py
│   │
│   └── widgets/
│       ├── playback_controls.py
│       └── signal_display_widget.py
│
├── utils/
│   ├── bids_events.py
│   └── playback_engine.py
│
├── data/
│   ├── signal.npy
│   └── events.tsv
│
├── .gitignore
├── LICENSE.md
├── README.md
├── environment.yml
├── main.py
└── pyproject.toml
```

Los archivos de datos (señal y eventos) pueden almacenarse en una carpeta `data/` para mantenerlos separados del código fuente.

---

## Flujo de reproducción

La señal completa permanece cargada en memoria y la interfaz muestra una ventana temporal de tamaño configurable.

Durante la reproducción:

```text
Señal completa
───────────────────────────────────────────────────────
                  ┌──────────────┐
                  │    Ventana   │
                  │   visible    │
                  └──────────────┘
                         │
                         ▼
───────────────────────────────────────────────────────
                         →
                      tiempo
```

El `PlaybackEngine` modifica progresivamente la posición de la ventana. Cada cambio de posición genera una actualización de la visualización.

Cuando se alcanza el final de la señal, la reproducción vuelve al inicio de la ventana y continúa en bucle.

---

## Tecnologías

El proyecto utiliza:

* **Python 3.12**
* **NumPy** para la representación y manipulación de las señales.
* **PyQt5** para la interfaz gráfica y el sistema de eventos.
* **PyQtGraph** para la visualización interactiva de las señales.
* **Pandas** para la lectura de los archivos de eventos `.tsv`.

---

## Instalación

Clonar el repositorio:

```bash
git clone https://github.com/masseyagus/cocemi_2026.git
```

Creación de entorno Conda:

```bash
conda env create -f environment.yml
```

---

## Ejemplo completo

Suponiendo la siguiente estructura:

```text
signalprocessing/
├── data/
│   ├── signal.npy
│   └── events.tsv
└── main.py
```

el visor puede iniciarse ejecutando:

```bash
python main.py data/signal.npy \
    --events data/events.tsv \
    --sfreq 250
```

La aplicación cargará la señal, mostrará sus canales, superpondrá los eventos correspondientes y permitirá reproducirla mediante los controles de la interfaz.

---

## Licencia

Este proyecto se distribuye bajo la licencia indicada en el archivo `LICENSE`.
