from dataclasses import dataclass

import pandas as pd


@dataclass
class Event:
    """
    Representa un evento de un archivo BIDS proyectado a muestras.

    Almacena la posición y duración del evento en muestras, junto con
    su tipo y el tiempo de inicio original expresado en segundos.

    Attributes:
        onset_sample (int): Muestra correspondiente al inicio del evento.
        duration_sample (int): Duración del evento expresada en muestras.
        trial_type (str): Tipo o descripción del evento.
        onset_sec (float): Tiempo de inicio original del evento, en segundos,
            conservado sin convertir.
    """
    
    onset_sample: int
    duration_sample: int
    trial_type: str
    onset_sec: float


def load_bids_events(events_tsv_path: str, sfreq: float) -> list[Event]:
    """
    Carga eventos desde un archivo `events.tsv` en formato BIDS.

    Lee el archivo como un TSV y convierte los tiempos de inicio y duración
    expresados en segundos a muestras utilizando la frecuencia de muestreo
    proporcionada. Para cada fila genera una instancia de `Event` y
    finalmente ordena los eventos según su posición de inicio en muestras.

    Args:
        events_tsv_path (str): Ruta al archivo `events.tsv`.
        sfreq (float): Frecuencia de muestreo de la señal asociada, en Hz.

    Returns:
        list[Event]: Lista de eventos ordenados de forma ascendente según
            `onset_sample`.

    Raises:
        ValueError: Si el archivo no contiene la columna obligatoria
            `onset`.

    Notes:
        - La columna `onset` es obligatoria y se interpreta en segundos.
        - Si no existe la columna `duration`, la duración de cada evento
          se establece en cero.
        - Los valores `NaN` de `duration` también se interpretan como
          una duración de cero.
        - Si no existe la columna `trial_type`, se utiliza `"event"` como
          tipo de evento.
        - `onset_sample` y `duration_sample` se calculan redondeando la
          conversión de segundos a muestras mediante `sfreq`.
        - `onset_sec` conserva el valor original de `onset` en segundos.
    """
    df = pd.read_csv(events_tsv_path, sep="\t")

    if "onset" not in df.columns:
        raise ValueError(
            "El archivo de eventos debe tener al menos la columna 'onset' (formato BIDS)."
        )

    events = []
    for _, row in df.iterrows():
        onset_sec = float(row["onset"])

        duration_sec = 0.0
        if "duration" in df.columns and not pd.isna(row.get("duration")):
            duration_sec = float(row["duration"])

        trial_type = str(row["trial_type"]) if "trial_type" in df.columns else "event"

        events.append(Event(
            onset_sample=int(round(onset_sec * sfreq)),
            duration_sample=int(round(duration_sec * sfreq)),
            trial_type=trial_type,
            onset_sec=onset_sec,
        ))

    return sorted(events, key=lambda e: e.onset_sample)
