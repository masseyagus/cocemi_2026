import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np

from gui.main_window import launch_viewer


def parse_channels(chan_str):
    """
    Convierte una cadena de índices de canales en una lista ordenada.

    La cadena puede contener índices individuales y rangos separados por
    espacios o comas. Los rangos se indican mediante un guion y se consideran
    inclusivos en ambos extremos.

    Por ejemplo, `"1 2 5-8, 10"` se convierte en
    `[1, 2, 5, 6, 7, 8, 10]`.

    Si la cadena está vacía o contiene únicamente espacios, devuelve `None`.

    Args:
        chan_str (str): Cadena con los índices o rangos de canales que se
            desean seleccionar.

    Returns:
        list[int] | None: Lista ordenada y sin índices repetidos, o `None` si
            la cadena está vacía.

    Raises:
        ValueError: Si alguno de los índices o rangos no puede convertirse
            a un entero.
    """    
    if not chan_str.strip():
        return None
    
    channels = set()
    # Reemplazamos comas por espacios y dividimos
    parts = chan_str.replace(',', ' ').split()
    for p in parts:
        if '-' in p:
            start, end = map(int, p.split('-'))
            channels.update(range(start, end + 1))
        else:
            channels.add(int(p))
    return sorted(list(channels))

class LauncherGUI:
    """
    Ventana de configuración para iniciar NeuroIA GUI.

    Permite seleccionar los archivos de señal y eventos, configurar los
    parámetros de visualización y filtrado, seleccionar canales y activar
    opciones adicionales como el mapa topográfico.

    La ventana almacena los valores introducidos por el usuario mediante
    variables de Tkinter. Al ejecutar `launch()`, valida y convierte los
    parámetros, carga la señal desde el archivo `.npy` y utiliza
    `launch_viewer()` para iniciar la ventana principal de reproducción.

    Attributes:
        root (tk.Tk): Ventana raíz de Tkinter utilizada como contenedor
            principal.
        signal_var (tk.StringVar): Ruta al archivo `.npy` de la señal.
        events_var (tk.StringVar): Ruta al archivo de eventos BIDS `.tsv`.
        channels_var (tk.StringVar): Índices de los canales introducidos por
            el usuario.
        sfreq_var (tk.DoubleVar): Frecuencia de muestreo de la señal.
        window_var (tk.IntVar): Tamaño de la ventana de visualización en
            muestras.
        scale_var (tk.DoubleVar): Factor de escala o ganancia utilizado para
            la visualización.
        highpass_var (tk.DoubleVar): Frecuencia de corte del filtro
            pasa-altos.
        lowpass_var (tk.DoubleVar): Frecuencia de corte del filtro
            pasa-bajos.
        notch_var (tk.DoubleVar): Frecuencia del filtro notch.
        speed_var (tk.DoubleVar): Velocidad de reproducción.
        refresh_var (tk.IntVar): Intervalo de actualización de la reproducción
            en milisegundos.
        topomap_var (tk.BooleanVar): Indica si se debe activar el mapa
            topográfico.
        topomap_fps_var (tk.DoubleVar): Frecuencia de actualización del
            topomap.
        n_eeg_var (tk.StringVar): Cantidad de canales EEG utilizados para el
            topomap. Una cadena vacía representa `None`.
    """

    def __init__(self, root, path_montage):
        """
        Inicializa la ventana de configuración del lanzador.

        Configura el título, tamaño y comportamiento de la ventana y crea los
        controles necesarios para seleccionar los archivos de entrada, configurar
        los canales, establecer los parámetros de señal y filtros y configurar
        la reproducción y el mapa topográfico.

        Los parámetros numéricos se inicializan con los valores predeterminados
        utilizados por el visor. La opción de topomap permite activar o desactivar
        su visualización y configurar su frecuencia de actualización y cantidad
        de canales EEG.

        Args:
            root (tk.Tk): Ventana raíz de Tkinter sobre la que se construye la
                interfaz.

        Returns:
            None
        """
        self.root = root
        self.montage = path_montage
        self.root.title("NeuroIA - Configuración de Lanzamiento")
        self.root.geometry("650x740")
        self.root.resizable(False, False)
        
        # Frame principal con padding
        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- SECCIÓN 1: ARCHIVOS ---
        file_frame = ttk.LabelFrame(main_frame, text="Archivos", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        self.signal_var = tk.StringVar()
        self.events_var = tk.StringVar()
        
        self.create_file_row(file_frame, "Señal (.npy):", self.signal_var, [("Numpy arrays", "*.npy")])
        self.create_file_row(file_frame, "Eventos BIDS (.tsv):", self.events_var, [("TSV files", "*.tsv")])
        
        # --- SECCIÓN 2: CANALES ---
        chan_frame = ttk.LabelFrame(main_frame, text="Selección de Canales", padding="10")
        chan_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(chan_frame, text="Índices (Ej: 1 5 10-15):").grid(row=0, column=0, sticky=tk.W)
        self.channels_var = tk.StringVar()
        ttk.Entry(chan_frame, textvariable=self.channels_var, width=40).grid(row=0, column=1, padx=5, sticky=tk.W)
        
        # --- SECCIÓN 3: PARÁMETROS DE SEÑAL Y FILTROS ---
        param_frame = ttk.LabelFrame(main_frame, text="Parámetros de Visualización y Filtros", padding="10")
        param_frame.pack(fill=tk.X, pady=5)
        
        # Variables con sus valores por defecto
        self.sfreq_var = tk.DoubleVar(value=500.0)
        self.window_var = tk.IntVar(value=1500)
        self.scale_var = tk.DoubleVar(value=50.0)
        self.highpass_var = tk.DoubleVar(value=0.5)
        self.lowpass_var = tk.DoubleVar(value=100.0)
        self.notch_var = tk.DoubleVar(value=50.0)
        
        self.create_param_grid(param_frame, [
            ("Frec. Muestreo (Hz):", self.sfreq_var, 0, 0),
            ("Ventana (muestras):", self.window_var, 0, 2),
            ("Escala/Ganancia:", self.scale_var, 1, 0),
            ("Highpass (Hz, 0=off):", self.highpass_var, 1, 2),
            ("Lowpass (Hz, 0=off):", self.lowpass_var, 2, 0),
            ("Notch (Hz, 0=off):", self.notch_var, 2, 2)
        ])
        
        # --- SECCIÓN 4: REPRODUCCIÓN Y TOPOMAP ---
        misc_frame = ttk.LabelFrame(main_frame, text="Reproducción y Extras", padding="10")
        misc_frame.pack(fill=tk.X, pady=5)
        
        self.speed_var = tk.DoubleVar(value=0.25)
        self.refresh_var = tk.IntVar(value=20)
        self.topomap_var = tk.BooleanVar(value=False)
        self.topomap_fps_var = tk.DoubleVar(value=8.0)
        self.n_eeg_var = tk.StringVar() # StringVar para permitir vacío (None)
        
        self.create_param_grid(misc_frame, [
            ("Velocidad (x):", self.speed_var, 0, 0),
            ("Refresco (ms):", self.refresh_var, 0, 2),
            ("FPS Topomap:", self.topomap_fps_var, 1, 0),
            ("Canales EEG (vacío=Todos):", self.n_eeg_var, 1, 2)
        ])
        
        ttk.Checkbutton(misc_frame, text="Activar Mapa Topográfico", variable=self.topomap_var).grid(row=2, column=0, columnspan=4, pady=10, sticky=tk.W)  # noqa: E501
        
        # --- BOTÓN DE LANZAMIENTO ---
        launch_btn = ttk.Button(main_frame, text="Lanzar Visor", command=self.launch)
        launch_btn.pack(fill=tk.X, pady=15)

    def create_file_row(self, parent, label_text, variable, filetypes):
        """
        Crea una fila de selección de archivo.

        La fila contiene una etiqueta descriptiva, un campo de texto asociado a
        una variable de Tkinter y un botón que abre un diálogo para seleccionar
        un archivo. La ruta seleccionada se almacena en la variable proporcionada.

        Args:
            parent (tkinter.Widget): Widget contenedor donde se agrega la fila.
            label_text (str): Texto descriptivo mostrado junto al campo.
            variable (tkinter.Variable): Variable de Tkinter vinculada al campo
                de texto y utilizada para almacenar la ruta seleccionada.
            filetypes (list[tuple[str, str]]): Tipos de archivo que se muestran
                en el diálogo de selección.

        Returns:
            None
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label_text, width=18).pack(side=tk.LEFT)
        ttk.Entry(frame, textvariable=variable).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame, text="Buscar", command=lambda: variable.set(filedialog.askopenfilename(filetypes=filetypes))).pack(side=tk.RIGHT)  # noqa: E501

    def create_param_grid(self, parent, params):
        """
        Crea una cuadrícula de parámetros con etiquetas y campos de entrada.

        Cada elemento de `params` define el texto de una etiqueta, la variable
        de Tkinter asociada y la posición que ocuparán dentro de la cuadrícula.

        Args:
            parent (tkinter.Widget): Widget contenedor donde se agregan los
                controles.
            params (list[tuple]): Lista de parámetros. Cada elemento debe tener
                la forma `(text, variable, row, col)`, donde `text` es la etiqueta
                mostrada, `variable` es la variable de Tkinter asociada, y
                `row` y `col` indican la posición inicial dentro de la cuadrícula.

        Returns:
            None
        """
        for text, var, row, col in params:
            ttk.Label(parent, text=text).grid(row=row, column=col, padx=5, pady=5, sticky=tk.W)
            ttk.Entry(parent, textvariable=var, width=10).grid(row=row, column=col+1, padx=5, pady=5, sticky=tk.W)

    def launch(self):
        """
        Valida la configuración, carga la señal y lanza el visor principal.

        Verifica que se haya seleccionado un archivo de señal, convierte los
        canales introducidos por el usuario mediante `parse_channels()` y procesa
        la cantidad de canales EEG configurada para el topomap.

        Luego carga la señal mediante `numpy.load()`, obtiene los parámetros de
        visualización, filtrado y reproducción configurados en la interfaz y
        destruye la ventana de configuración antes de iniciar el visor mediante
        `launch_viewer()`.

        Los valores de frecuencia de corte de los filtros se convierten a
        `None` cuando el usuario introduce cero, lo que permite desactivar
        dichos filtros. La configuración del topomap incluye su frecuencia de
        actualización, la cantidad de canales EEG y la ruta al archivo de
        posiciones de los 64 canales.

        Los errores de formato numérico o de selección de canales se muestran
        mediante un mensaje de error específico. Cualquier otra excepción se
        muestra como un error inesperado.

        Returns:
            None

        Raises:
            No propaga las excepciones capturadas internamente. Los errores se
                muestran mediante cuadros de diálogo de Tkinter.
        """
        # Validar archivo de señal
        sig_path = self.signal_var.get()
        if not sig_path:
            messagebox.showerror("Error", "Debe seleccionar un archivo de señal (.npy)")
            return
            
        try:
            # Parsear canales
            channels_idx = parse_channels(self.channels_var.get())
            
            # Parsear n_eeg
            n_eeg_val = self.n_eeg_var.get().strip()
            n_eeg = int(n_eeg_val) if n_eeg_val else None

            # Cargar señal
            signal = np.load(sig_path)
            
            # Recuperar resto de parámetros
            events_path = self.events_var.get() if self.events_var.get() else None
            sfreq = self.sfreq_var.get()
            window_size = self.window_var.get()
            scale_factor = self.scale_var.get()
            highpass = self.highpass_var.get()
            lowpass = self.lowpass_var.get()
            notch = self.notch_var.get()
            
            # Destruir la ventana de configuración antes de lanzar el visor
            self.root.destroy()
            
            # Lanzar visor
            launch_viewer(
                signal,
                channels_idx=channels_idx,
                events_path=events_path,
                sfreq=sfreq,
                window_size=window_size,
                scale_factor=scale_factor,
                highpass=highpass if highpass > 0 else None,
                notch=notch if notch > 0 else None,
                playback_rate=self.speed_var.get(),
                lowpass=lowpass if lowpass > 0 else None,
                refresh_ms=self.refresh_var.get(),
                topomap_fps=self.topomap_fps_var.get(),
                show_topomap=self.topomap_var.get(),
                n_eeg_channels=n_eeg,
                montage_path=self.montage
            )
            
        except ValueError as e:
            messagebox.showerror("Error de Formato", f"Por favor \
                                 verifique que los valores numéricos y canales sean correctos.\nDetalle: {e}")
        except Exception as e:
            messagebox.showerror("Error Inesperado", str(e))
