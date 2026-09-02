"""
Filtrado mínimo para visualización de EEG crudo.

Este módulo NO es un pipeline de análisis: aplica únicamente lo necesario
para poder distinguir la morfología de la señal a simple vista (remueve
deriva de baja frecuencia y ruido de línea eléctrica), sin recortar bandas
fisiológicas ni hacer ningún procesamiento adicional.
"""
import numpy as np
from scipy.signal import butter, filtfilt, iirnotch


def highpass_filter(signal: np.ndarray, sfreq: float, cutoff: float = 0.5, order: int = 4) -> np.ndarray:
    """
    Elimina la deriva de baja frecuencia de una señal EEG.

    Aplica un filtro Butterworth pasa-altos para reducir componentes de muy
    baja frecuencia, como el offset de los electrodos y el drift de línea
    base, facilitando la visualización de la morfología de la señal.

    Args:
        signal (np.ndarray): Señal de entrada con forma
            `(n_canales, n_muestras)`.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        cutoff (float): Frecuencia de corte del filtro pasa-altos, en Hz.
            Por defecto, `0.5` Hz.
        order (int): Orden del filtro Butterworth. Por defecto, `4`.

    Returns:
        np.ndarray:
            Señal filtrada con la misma forma que `signal`.

    Notes:
        El filtrado se realiza mediante `filtfilt`, por lo que se aplica
        hacia adelante y hacia atrás para evitar introducir desfase temporal.
    """
    nyq = sfreq / 2
    b, a = butter(order, cutoff / nyq, btype="highpass") # type: ignore
    return filtfilt(b, a, signal, axis=-1)


def notch_filter(signal: np.ndarray, sfreq: float, freq: float = 50.0, quality: float = 30.0) -> np.ndarray:
    """
    Elimina el ruido asociado a una frecuencia de línea eléctrica.

    Aplica un filtro IIR notch centrado en la frecuencia especificada para
    reducir la interferencia de la red eléctrica en la señal EEG.

    Args:
        signal (np.ndarray): Señal de entrada con forma
            `(n_canales, n_muestras)`.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        freq (float): Frecuencia central que se desea eliminar, en Hz.
            Por defecto, `50.0` Hz.
        quality (float): Factor de calidad Q del filtro. Valores mayores
            producen una banda de rechazo más estrecha. Por defecto, `30.0`.

    Returns:
        np.ndarray:
            Señal filtrada con la misma forma que `signal`.

    Notes:
        El filtrado se realiza mediante `filtfilt`, evitando introducir
        desfase temporal en la señal.
    """
    b, a = iirnotch(freq, quality, sfreq)
    return filtfilt(b, a, signal, axis=-1)


def prepare_for_display(signal: np.ndarray, sfreq: float,
                         highpass: float | None = 0.5,
                         notch: float | None = 50.0) -> np.ndarray:
    """
    Prepara una señal EEG para su visualización.

    Aplica de forma opcional un filtro pasa-altos y un filtro notch para
    reducir la deriva de baja frecuencia y el ruido de línea eléctrica.
    Los filtros se aplican en el orden pasa-altos seguido de notch.

    Args:
        signal (np.ndarray): Señal de entrada con forma
            `(n_canales, n_muestras)`.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        highpass (float or None): Frecuencia de corte del filtro pasa-altos,
            en Hz. Si es `None`, se omite este filtro. Por defecto, `0.5` Hz.
        notch (float or None): Frecuencia central del filtro notch, en Hz.
            Si es `None`, se omite este filtro. Por defecto, `50.0` Hz.

    Returns:
        np.ndarray:
            Señal preparada para visualización, con la misma forma que
            `signal`.

    Notes:
        Esta función realiza únicamente el filtrado necesario para mejorar
        la visualización de la señal y no pretende sustituir un pipeline de
        procesamiento o análisis de EEG.
    """
    out = signal
    if highpass:
        out = highpass_filter(out, sfreq, cutoff=highpass)
    if notch:
        out = notch_filter(out, sfreq, freq=notch)
    return out
