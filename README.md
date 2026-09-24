# NeuroIA GUI: Visor y Reproductor de Señales Biomédicas Multicanal
<div style="text-align: justify">

<img align="right" src="/src/assets/icons/neuro_ia_logo.png" alt="Neuro-IA Lab" width="150" style="margin-left: 25px">


Visor y reproductor interactivo de señales biomédicas multicanal desarrollado en Python para la asistencia del NueroIA Lab a la [Ronda COCEMI 2026](https://rondacocemi.uy/).

La aplicación permite cargar una señal almacenada en formato `.npy` junto con un archivo de eventos `.tsv`, procesar y preparar la señal para su correcta visualización, representar los canales seleccionados junto a sus respectivos marcadores temporales y recorrerlos de forma interactiva mediante controles de reproducción.

---

## Objetivo

El objetivo principal del proyecto es proporcionar una herramienta sencilla para **visualizar y reproducir señales biomédicas multicanal junto con sus eventos temporales**.

La aplicación busca facilitar la inspección de señales previamente adquiridas, permitiendo seleccionar los canales de interés, aplicar un procesamiento mínimo orientado a la visualización, recorrer temporalmente la señal y relacionar visualmente los cambios observados en los canales con los eventos registrados durante la adquisición.

---

## Características

| Área | Funcionalidades |
|:---:|:---:|
| **Señal** | Carga de archivos `.npy`, soporte multicanal y selección de canales. |
| **Visualización** | Representación simultánea de canales, nombres de canales y eje temporal en segundos. |
| **Procesamiento** | Detrending, eliminación de offset DC y filtros pasa-altos, pasa-bajos y notch opcionales. |
| **Normalización** | Normalización independiente de cada canal mediante z-score. |
| **Eventos** | Carga de eventos BIDS desde `.tsv` y representación mediante marcadores temporales. |
| **Reproducción** | Reproducción, pausa, avance, retroceso y reproducción en bucle. |
| **Interfaz** | Controles de reproducción, indicador de posición e interfaz gráfica basada en Qt y PyQtGraph. |

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

Antes de la visualización, la aplicación puede realizar una preparación de la señal. Este procesamiento incluye la extensión temporal mediante muestras reflejadas, eliminación de tendencia lineal y offset DC, y la aplicación opcional de filtros pasa-altos, pasa-bajos y notch.

Posteriormente, los canales seleccionados se normalizan de forma independiente mediante z-score para facilitar su representación conjunta.

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
onset   duration    trial_type

2.50    0.50        stimulus

5.00    1.00        response

8.25    0.25        stimulus
```

Los valores de `onset` y `duration` se expresan en segundos. Durante la carga, estos valores se convierten a muestras utilizando la frecuencia de muestreo de la señal.

Para la visualización, la posición de los eventos se convierte nuevamente a segundos, de modo que los marcadores y la señal utilizan la misma escala temporal.

---

## Interfaz

La aplicación está compuesta por tres elementos principales:

### Visualización de la señal

`SignalDisplayWidget` se encarga de representar los canales de la señal y los eventos correspondientes.

La señal completa se carga una única vez en las curvas de PyQtGraph. Durante la reproducción, la visualización se desplaza modificando únicamente el rango temporal visible, sin volver a extraer ni cargar ventanas de datos.

Cada canal se representa de manera independiente y se desplaza verticalmente para facilitar la visualización simultánea de múltiples señales.

El eje temporal se representa en segundos y los eventos se muestran mediante marcadores verticales en sus posiciones temporales correspondientes.

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
        Posición de      Visualización
        reproducción      de la señal
             │               │
             │               │
             └───────┬───────┘
                     │
                     ▼
                Eventos BIDS
```

`MainWindow` funciona como componente de integración. Se encarga de conectar el motor de reproducción con la visualización y los controles, además de preparar los canales seleccionados, configurar la señal completa y cargar los eventos en el widget de visualización.

Durante la reproducción, `MainWindow` actualiza el rango temporal visible y la posición mostrada en los controles, mientras que `SignalDisplayWidget` mantiene los datos de la señal y los eventos cargados.

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

También pueden configurarse los canales, el tamaño de la ventana, la escala
vertical y los parámetros de reproducción y filtrado:

```bash
python main.py señal.npy \
    --channels 0 2 4 \
    --events eventos.tsv \
    --sfreq 500 \
    --window 1500 \
    --scale 50 \
    --highpass 0.5 \
    --lowpass 100 \
    --notch 50 \
    --speed 0.25 \
    --refresh 20
```

### Argumentos disponibles

| Argumento | Descripción | Por defecto |
|:---:|:---:|:---:|
| `signal` | Archivo `.npy` con forma `(n_canales, n_muestras)`. | Obligatorio |
| `--channels` | Índices de los canales a visualizar, separados por espacios. | `None` |
| `--events` | Archivo `events.tsv` con los eventos en formato BIDS. | `None` |
| `--sfreq` | Frecuencia de muestreo de la señal, en Hz. | `500.0` |
| `--window` | Tamaño de la ventana visible, en muestras. | `1500` |
| `--scale` | Factor de escala vertical entre canales. | `50.0` |
| `--highpass` | Frecuencia de corte del filtro pasa-altos, en Hz. `0` lo desactiva. | `0.5` |
| `--lowpass` | Frecuencia de corte del filtro pasa-bajos, en Hz. `0` lo desactiva. | `100.0` |
| `--notch` | Frecuencia base para eliminar ruido de línea y sus múltiplos inferiores a Nyquist. `0` lo desactiva. | `50.0` |
| `--speed` | Velocidad de reproducción. `1.0` corresponde a tiempo real; valores menores reproducen más lentamente. | `0.25` |
| `--refresh` | Intervalo de actualización del temporizador, en milisegundos. | `20` |

La interfaz de línea de comandos no requiere un archivo independiente para una señal filtrada. La preparación de la señal para visualización se realiza internamente cuando corresponde.

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
    sfreq=500.0,
)
```

También es posible indicar qué canales serán visualizados mediante `channels_idx`:

```python
channels_idx = [0, 2, 4]

launch_viewer(
    signal=signal,
    channel_names=channel_names,
    channels_idx=channels_idx,
    events_path="events.tsv",
    sfreq=250.0,
)
```

La preparación de la señal para visualización puede configurarse mediante los parámetros `highpass`, `lowpass` y `notch`.

La reproducción puede ajustarse mediante `refresh_ms`, que determina el intervalo de actualización del temporizador, y `playback_rate`, que controla el avance de la reproducción.

---

## Estructura del proyecto

Una organización general del proyecto es:

```text
cocemi_2026/
├── data
│   └── obtain_data.ipynb
├── src
│   ├── assets
│   │   └── icons
│   │       └── neuro_ia_logo.png
│   ├── gui
│   │   ├── widgets
│   │   │   ├── __init__.py
│   │   │   ├── playback_controls.py
│   │   │   └── signal_display_widget.py
│   │   ├── __init__.py
│   │   └── main_window.py
│   └── utils
│       ├── __init__.py
│       ├── bids_events.py
│       ├── filters.py
│       └── playback_engine.py
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

La señal completa se carga en memoria una única vez y la interfaz muestra una ventana temporal de tamaño configurable.

Durante la reproducción:

```text
Señal completa

───────────────────────────────────────────────────────

                  ┌──────────────┐
                  │    Ventana   │
                  │    visible   │
                  └──────────────┘
                         │
                         ▼

───────────────────────────────────────────────────────
                         →
                       tiempo
```

El `PlaybackEngine` modifica progresivamente la posición de la ventana.

Cada cambio de posición actualiza únicamente el rango temporal visible del gráfico. La señal y los eventos permanecen cargados en `SignalDisplayWidget`, evitando volver a extraer y transferir los datos correspondientes a cada ventana.

Cuando se alcanza el final de la señal, la reproducción vuelve al inicio de la ventana y continúa en bucle.

---

## Tecnologías

El proyecto utiliza:

* **Python 3.12**

* **NumPy** para la representación y manipulación de las señales.

* **SciPy** para el procesamiento mínimo de las señales mediante filtros y detrending.

* **PyQt5** para la interfaz gráfica y el sistema de eventos.

* **PyQtGraph** para la visualización interactiva de las señales.

* **Pandas** para la lectura de los archivos de eventos `.tsv`.

---

## Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/masseyagus/cocemi_2026.git
   ```

2. **Crear y activar el entorno de Conda:**
   ```bash
   conda env create -f environment.yml
   ```

3. **Instalar la librería en modo editable:**  
   Instala este mismo paquete (`cocemi`) en modo editable para que cualquier modificación en el código fuente de la interfaz se aplique de inmediato sin necesidad de reinstalar:
   ```bash
   pip install -e .
   ```

4. **Soporte para archivos HDF5 o XDF (Opcional):**  
   Si necesitas soporte para leer formatos HDF5 o XDF, puedes utilizar la Jupyter Notebook `obtain_data.ipynb`. Sin embargo, para su uso debes añadir al entorno la librería [pyhwr](https://github.com/lucasbaldezzari/pyhwr.git) de [Lucas Baldezzari](https://github.com/lucasbaldezzari). Para ello, clona su repositorio y, desde la raíz del paquete con tu entorno activo, ejecútalo en modo de compatibilidad:
   ```bash
   pip install -e . --config-settings editable_mode=compat
   ```

---

## Ejemplo completo

Suponiendo la siguiente estructura:

```text
cocemi_2026/

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

La aplicación cargará la señal, preparará los canales para su visualización según la configuración establecida, mostrará los canales seleccionados, superpondrá los eventos correspondientes y permitirá reproducir la señal mediante los controles de la interfaz.

---

## Licencia

Este proyecto se distribuye bajo la licencia indicada en el archivo [LICENSE.md](./LICENSE.md).
