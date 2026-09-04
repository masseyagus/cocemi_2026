"""
Punto de entrada de línea de comandos para NeuroIA GUI.

Uso
----
    python main.py señal.npy --events eventos.tsv --sfreq 250

`señal.npy` debe contener un array de forma (n_canales, n_muestras).
"""
import argparse
import ctypes
import sys

import numpy as np

from gui.main_window import launch_viewer


def parse_args():
    """
    Define y procesa los argumentos de línea de comandos.

    Configura los parámetros necesarios para cargar la señal y, de forma
    opcional, un archivo de eventos BIDS. También permite configurar la
    frecuencia de muestreo, el tamaño de la ventana visible y el factor de
    escala vertical utilizado por el visor.

    Returns:
        argparse.Namespace:
            Objeto con los argumentos de línea de comandos procesados:
            `signal`, `events`, `sfreq`, `window` y `scale`.
    """
    parser = argparse.ArgumentParser(
        description="Reproductor de señales biomédicas con overlay de eventos BIDS."
    )
    parser.add_argument("signal", help="Archivo .npy con forma (n_canales, n_muestras).")
    parser.add_argument("--channels", type=int, nargs='+', default=None,
                         help="Índices de canales a visualizar separados por espacio (ej. 10 24 51 60).")
    parser.add_argument("--events", default=None,
                         help="Archivo events.tsv en formato BIDS. Opcional.")
    parser.add_argument("--sfreq", type=float, default=500.0,
                         help="Frecuencia de muestreo, en Hz.")
    parser.add_argument("--window", type=int, default=1500,
                         help="Tamaño de la ventana visible, en muestras.")
    parser.add_argument("--scale", type=float, default=50.0,
                         help="Factor de escala/ganancia vertical entre canales.")
    parser.add_argument("--highpass", type=float, default=0.5,
                         help="Corte del pasa-altos de visualización, en Hz. 0 para desactivarlo.")
    parser.add_argument("--lowpass", type=float, default=100.0,
                         help="Corte del pasa-bajos de visualización, en Hz. 0 para desactivarlo.")
    parser.add_argument("--notch", type=float, default=50.0,
                         help="Frecuencia de línea a remover, en Hz (50 o 60). 0 para desactivarlo.")
    parser.add_argument("--speed", type=float, default=0.25,
                     help="Velocidad de reproducción (1.0 = tiempo real, <1 = más lento).")
    parser.add_argument("--refresh", type=int, default=20,
                     help="Intervalo de actualización del temporizador, en milisegundos.")
    return parser.parse_args()


def main():
    """
    Carga la señal especificada por línea de comandos y lanza el visor.

    La señal se carga desde un archivo `.npy`. Los parámetros restantes se
    utilizan para configurar la reproducción y visualización mediante
    `launch_viewer()`.

    Returns:
        None:
            Esta función no devuelve ningún valor. La ejecución queda a cargo
            de la aplicación gráfica.
    """
    args = parse_args()

    signal = np.load(args.signal)

    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            print(f"No se pudo aplicar el awareness de DPI: {e}")

    launch_viewer(
        signal,
        channels_idx=args.channels,
        events_path=args.events,
        sfreq=args.sfreq,
        window_size=args.window,
        scale_factor=args.scale,
        highpass=args.highpass or None,
        notch=args.notch or None,
        playback_rate=args.speed,
        lowpass=args.lowpass,
        refresh_ms=args.refresh
    )

if __name__ == "__main__":
    main()
