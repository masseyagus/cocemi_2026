"""
Punto de entrada de línea de comandos para NeuroIA GUI.

Uso
----
    python main.py señal.npy --events eventos.tsv --sfreq 250

`señal.npy` debe contener un array de forma (n_canales, n_muestras).
"""
import argparse

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
    parser.add_argument("--notch", type=float, default=50.0,
                         help="Frecuencia de línea a remover, en Hz (50 o 60). 0 para desactivarlo.")
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

    launch_viewer(
        signal,
        channels_idx=args.channels,
        events_path=args.events,
        sfreq=args.sfreq,
        window_size=args.window,
        scale_factor=args.scale,
        highpass=args.highpass or None,
        notch=args.notch or None,
    )

if __name__ == "__main__":
    main()
