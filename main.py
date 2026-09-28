"""
Uso.
----
    python main.py

Al ejecutarse, abrirá una ventana de configuración para cargar los 
archivos y parámetros necesarios antes de lanzar el visor.
"""

import ctypes
import os
import sys
import tkinter as tk

from gui.launcher import LauncherGUI


def main():
    """
    Inicializa la aplicación gráfica y abre la ventana de configuración.

    En Windows intenta habilitar la conciencia de DPI del proceso para mejorar
    la nitidez de la interfaz. Luego crea la ventana raíz de Tkinter, carga
    el tema visual definido en `azure.tcl` y crea la instancia de
    `LauncherGUI`.

    El bucle principal de Tkinter se ejecuta mediante `root.mainloop()` y
    mantiene activa la ventana de configuración hasta que el usuario la
    cierre o lance el visor principal.

    Returns:
        None
    """
    if sys.platform == "win32":
        try:
            # Mejora la nitidez de la interfaz gráfica en Windows (DPI Awareness)
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            print(f"No se pudo aplicar el awareness de DPI: {e}")

    root = tk.Tk()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    azure_tcl_path = os.path.join(script_dir, "azure.tcl")
    
    try:
        root.tk.call("source", azure_tcl_path)
        root.tk.call("set_theme", "dark")  # Cambiar a "light" si se prefiere tema claro
    except Exception as e:
        print(f"Error al cargar el tema Azure: {e}")

    path = "src/assets/montages/posiciones_64_canales.json"

    app = LauncherGUI(root, path_montage=path)  # noqa: F841

    root.update_idletasks()
    
    # Obtener las dimensiones exactas requeridas por el contenido
    req_width = root.winfo_reqwidth()
    req_height = root.winfo_reqheight()
    
    root.geometry(f"{req_width}x{req_height}")
    root.resizable(False, False)

    root.mainloop()

if __name__ == "__main__":
    main()
