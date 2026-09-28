# NeuroIA GUI: Visor y Reproductor de Señales Biomédicas Multicanal
<div style="text-align: justify">

<img align="right" src="/src/assets/icons/neuro_ia_logo.png" alt="Neuro-IA Lab" width="150" style="margin-left: 25px">


Visor y reproductor interactivo de señales biomédicas multicanal desarrollado en Python para la asistencia del NueroIA Lab a la [Ronda COCEMI 2026](https://rondacocemi.uy/).

La aplicación permite cargar una señal almacenada en formato **.npy** junto con un archivo de eventos **.tsv**, procesar y preparar la señal para su correcta visualización, representar los canales seleccionados junto a sus respectivos marcadores temporales y recorrerlos de forma interactiva mediante controles de reproducción.

---

## Objetivo

El objetivo principal del proyecto es proporcionar una herramienta sencilla para **visualizar y reproducir señales biomédicas multicanal junto con sus eventos temporales**.

La aplicación busca facilitar la inspección de señales previamente adquiridas, permitiendo seleccionar los canales de interés, aplicar un procesamiento mínimo orientado a la visualización, recorrer temporalmente la señal y relacionar visualmente los cambios observados en los canales con los eventos registrados durante la adquisición.

---

## Características

| Área | Funcionalidades |
|:---:|:---:|
| **Señal** | Carga de archivos **.npy**, soporte multicanal y selección flexible de canales (índices individuales y rangos). |
| **Visualización** | Representación simultánea de canales, nombres de canales, eje temporal y mapa topográfico de energía (topomap) sincronizado. |
| **Procesamiento** | Detrending, eliminación de offset DC y filtros pasa-altos, pasa-bajos y notch opcionales. |
| **Normalización** | Normalización independiente de cada canal mediante z-score. |
| **Eventos** | Carga de eventos BIDS desde `.tsv` y representación mediante marcadores temporales. |
| **Reproducción** | Reproducción, pausa, avance, retroceso y reproducción en bucle con velocidad ajustable. |
| **Interfaz** | Lanzador de configuración gráfico con tema moderno (Azure), controles de reproducción e indicadores integrados. |

---

## Funcionamiento

La aplicación recibe dos archivos principales:

### Señal

La señal debe almacenarse en un archivo NumPy (**.npy**) como un array bidimensional:

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

Los eventos se proporcionan mediante un archivo **events.tsv** siguiendo la estructura utilizada por BIDS.

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

|***onset***|***duration***|***trial_type***|
|:--:|:--:|:--:|
|2.50|0.50|stimulus|
|5.00||1.00|response|
|8.25|0.25|stimulus|


Los valores de **onset** y **duration** se expresan en segundos. Durante la carga, estos valores se convierten a muestras utilizando la frecuencia de muestreo de la señal.

Para la visualización, la posición de los eventos se convierte nuevamente a segundos, de modo que los marcadores y la señal utilizan la misma escala temporal.

---

## Interfaz

La aplicación cuenta con una interfaz de configuración de lanzamiento previa y tres componentes principales en la ventana del visor:

### Lanzador de configuración

Permite seleccionar los archivos **.npy** y **.tsv** mediante explorador de archivos y configurar todos los parámetros de filtrado, canales, refresco y visualización antes de iniciar la reproducción, eliminando la necesidad de comandos complejos por consola.

### Visualización de la señal

`SignalDisplayWidget` representa los canales seleccionados y los eventos correspondientes. La señal completa se carga una única vez en las curvas de **PyQtGraph** y la visualización se desplaza modificando únicamente el rango temporal visible.

### Mapa topográfico

TopomapWidget muestra la distribución espacial de la energía de la señal en tiempo real mediante una proyección 2D basada en las posiciones del **montaje 10-20**.

### Motor y controles de reproducción

`PlaybackEngine` controla el avance temporal de forma independiente a la interfaz gráfica, mientras que PlaybackControls ofrece la interacción del usuario para reproducir, pausar y ajustar la navegación.

---

## Arquitectura

La aplicación mantiene separadas las responsabilidades principales:

```text
                                  MainWindow
                                       │
        ┌───────────────────┬──────────┴──────────┬───────────────────┐
        │                   │                     │                   │
        ▼                   ▼                     ▼                   ▼
 PlaybackEngine    SignalDisplayWidget      TopomapWidget      PlaybackControls
        │                   │                     │
        ▼                   ▼                     ▼
   Posición de        Visualización de     Mapa topográfico
  reproducción            la señal             de energía
        │                   │
        └─────────┬─────────┘
                  │
                  ▼
             Eventos BIDS
```

**MainWindow** funciona como componente de integración principal. Se encarga de conectar el motor de reproducción con la visualización de la señal, el mapa topográfico de energía y los controles, además de preparar los canales seleccionados, configurar la señal completa y cargar los eventos en los widgets correspondientes.

Durante la reproducción, **MainWindow** coordina las actualizaciones notificadas por **PlaybackEngine**: actualiza el rango temporal visible en **SignalDisplayWidget**, recalcula la distribución de energía mostrada en **TopomapWidget** y refresca el indicador de posición en **PlaybackControls**.

---

## Uso

### Inicio de la aplicación

Para abrir la interfaz de configuración gráfica, simplemente ejecuta en la terminal:

```bash
python main.py

```

Al ejecutarse, se abrirá la ventana de configuración donde podrás:

**1. Seleccionar archivos:** Buscar tu archivo de señal **.npy** y el archivo opcional de eventos BIDS .tsv.

**2. Seleccionar canales:** Definir los canales que deseas visualizar. Puedes ingresar índices individuales separados por espacio o coma, así como también rangos (ej. 0 2 5-10, 15). Si se deja en blanco, se visualizan todos los canales.

**3. Ajustar parámetros:** Configurar la frecuencia de muestreo, tamaño de ventana, ganancia, filtros (pasa-altos, pasa-bajos, notch) y velocidad de reproducción.

**4. Mapa topográfico:** Activar la casilla de mapa topográfico e indicar el número de canales EEG iniciales si la señal contiene otros tipos de sensores (EMG/EOG).

Al presionar el botón **Lanzar Visor**, la ventana de configuración se cerrará e iniciará la reproducción interactiva.

<p align="center">
  <img src="/src/assets/icons/launch_gui.png" alt="Launcher" width="350">
</p>

---

## Uso desde Python

También es posible iniciar el visor programáticamente incluyendo la configuración de topografía y canales:

```python
import numpy as np
from gui.main_window import launch_viewer

signal = np.load("data/signal.npy")

launch_viewer(
    signal=signal,
    channels_idx=[0, 1, 2, 3, 4, 5],
    events_path="data/events.tsv",
    sfreq=500.0,
    window_size=1500,
    scale_factor=50.0,
    highpass=0.5,
    lowpass=100.0,
    notch=50.0,
    playback_rate=0.25,
    show_topomap=True,
    n_eeg_channels=64,
    topomap_fps=8.0,
    montage_path="src/assets/montage/posiciones_64_canales.json"
)
```

---

## Estructura del proyecto

Una organización general del proyecto es:

```text
cocemi_2026/
├── data
├── src
│   ├── assets
│   │   ├── icons
│   │   │   └── neuro_ia_logo.png
│   │   └── montages
│   │       └── posiciones_64_canales.json
│   ├── gui
│   │   ├── widgets
│   │   │   ├── __init__.py
│   │   │   ├── playback_controls.py
│   │   │   ├── signal_display_widget.py
│   │   │   └── topomap_widget.py
│   │   ├── __init__.py
│   │   ├── launcher.py
│   │   └── main_window.py
│   └── utils
│       ├── __init__.py
│       ├── bids_events.py
│       ├── filters.py
│       └── playback_engine.py
├── theme
│   ├── dark
│   │   └── [60+ archivos .png del tema oscuro]
│   ├── light
│   │   └── [60+ archivos .png del tema claro]
│   ├── dark.tcl
│   └── light.tcl
├── .gitignore
├── LICENSE.md
├── README.md
├── THIRD_PARTY_LICENSES.md
├── azure.tcl
├── environment.yml
├── main.py
└── pyproject.toml
```

Los archivos de datos (señal y eventos) pueden almacenarse en una carpeta **data/** para mantenerlos separados del código fuente.

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

El **PlaybackEngine** modifica progresivamente la posición de la ventana.

Cada cambio de posición actualiza únicamente el rango temporal visible del gráfico. La señal y los eventos permanecen cargados en **SignalDisplayWidget**, evitando volver a extraer y transferir los datos correspondientes a cada ventana.

Cuando se alcanza el final de la señal, la reproducción vuelve al inicio de la ventana y continúa en bucle.

---

## Tecnologías

El proyecto utiliza:

* **Python 3.12**

* **NumPy** para la representación y manipulación de las señales.

* **SciPy** para el procesamiento mínimo de señales mediante filtros y detrending, e interpolación espacial para el mapa topográfico.

* **PyQt5 y Tkinter (con Azure-ttk-theme)** para la interfaz gráfica y formularios de lanzamiento.

* **PyQtGraph** para la visualización interactiva de las señales.

* **Pandas** para la lectura de los archivos de eventos **.tsv**.

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
   Instala este mismo paquete (***cocemi***) en modo editable para que cualquier modificación en el código fuente de la interfaz se aplique de inmediato sin necesidad de reinstalar:
   ```bash
   pip install -e .
   ```

4. **Soporte para archivos HDF5 o XDF (Opcional):**  
   Si necesitas soporte para leer formatos HDF5 o XDF, puedes utilizar la Jupyter Notebook `obtain_data.ipynb`. Sin embargo, para su uso debes añadir al entorno la librería [pyhwr](https://github.com/lucasbaldezzari/pyhwr.git) de [Lucas Baldezzari](https://github.com/lucasbaldezzari). Para ello, clona su repositorio y, desde la raíz del paquete con tu entorno activo, ejecútalo en modo de compatibilidad:

   ```bash
   pip install -e . --config-settings editable_mode=compat
   ```

---

## Licencia y Créditos de Terceros
Este proyecto se distribuye bajo la licencia MIT indicada en el archivo [LICENSE.md](/LICENSE.md).

Para conocer las atribuciones de derechos de autor y licencias de los componentes de terceros integrados en este repositorio (tema gráfico Azure-ttk-theme y coordenadas de montaje derivadas de MNE-Python), consulta el archivo [THIRD_PARTY_LICENSES.md](/THIRD_PARTY_LICENSES.md).