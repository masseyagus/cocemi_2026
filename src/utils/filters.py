"""
Filtrado mínimo para visualización de EEG crudo.

Este módulo proporciona filtros destinados a preparar señales EEG para su
visualización, incluyendo eliminación de deriva de baja frecuencia,
limitación de componentes de alta frecuencia y reducción del ruido de línea
eléctrica.

El procesamiento se realiza sobre el eje temporal de la señal.
"""

import numpy as np
from scipy.signal import butter, detrend, filtfilt, iirnotch, sosfiltfilt


def highpass_filter(signal: np.ndarray, sfreq: float, 
                    cutoff: float = 0.5, order: int = 2) -> np.ndarray:
    """
    Aplica un filtro pasa-altos Butterworth a una señal.

    El filtro atenúa las componentes de frecuencia inferiores a la frecuencia
    de corte especificada. Se implementa mediante representación SOS y
    filtrado hacia adelante y hacia atrás para evitar desfases de fase.

    Args:
        signal (np.ndarray): Señal de entrada. El filtrado se realiza sobre
            el último eje.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        cutoff (float): Frecuencia de corte del filtro pasa-altos, en Hz.
        order (int): Orden del filtro Butterworth.

    Returns:
        np.ndarray:
            Señal filtrada con la misma forma que `signal`.

    Notes:
        La frecuencia de Nyquist se calcula como `sfreq / 2`.
    """
    nyq = sfreq / 2
    sos = butter(order, cutoff / nyq, btype="highpass", output="sos")
    return sosfiltfilt(sos, signal, axis=-1)


def lowpass_filter(signal: np.ndarray, sfreq: float, 
                   cutoff: float = 100.0, order: int = 4) -> np.ndarray:
    """
    Aplica un filtro pasa-bajos Butterworth a una señal.

    Atenúa las componentes de frecuencia superiores a la frecuencia de corte
    especificada. La frecuencia de corte se limita a un valor inferior a la
    frecuencia de Nyquist para evitar una configuración inválida del filtro.

    Args:
        signal (np.ndarray): Señal de entrada. El filtrado se realiza sobre
            el último eje.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        cutoff (float): Frecuencia de corte del filtro pasa-bajos, en Hz.
        order (int): Orden del filtro Butterworth.

    Returns:
        np.ndarray:
            Señal filtrada con la misma forma que `signal`.

    Notes:
        La frecuencia de corte efectiva no puede superar `nyq - 1.0`, donde
        `nyq` corresponde a la frecuencia de Nyquist.
    """
    nyq = sfreq / 2
    cutoff = min(cutoff, nyq - 1.0)
    sos = butter(order, cutoff / nyq, btype="lowpass", output="sos")
    return sosfiltfilt(sos, signal, axis=-1)


def notch_filter(signal: np.ndarray, sfreq: float, freqs: list[float] | float = 50.0, 
                 quality: float = 30.0) -> np.ndarray:
    """
    Aplica uno o varios filtros notch para atenuar frecuencias específicas.

    Cada frecuencia especificada se procesa mediante un filtro notch IIR.
    Las frecuencias que no se encuentran dentro del rango válido entre 0 y
    la frecuencia de Nyquist se ignoran.

    Args:
        signal (np.ndarray): Señal de entrada. El filtrado se realiza sobre
            el último eje.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        freqs (list[float] | float): Frecuencia o lista de frecuencias que se
            desean atenuar, en Hz.
        quality (float): Factor de calidad utilizado para los filtros notch.

    Returns:
        np.ndarray:
            Señal filtrada con la misma forma que `signal`.

    Notes:
        Si `freqs` es un único valor numérico, se convierte internamente en
        una lista. Cada filtro se aplica de forma secuencial mediante
        `filtfilt`.
    """
    if isinstance(freqs, (int, float)):
        freqs = [float(freqs)]

    out = signal
    nyq = sfreq / 2
    for f in freqs:
        if 0 < f < nyq:
            b, a = iirnotch(f, quality, sfreq)
            out = filtfilt(b, a, out, axis=-1)
    return out


def prepare_for_display(signal: np.ndarray, sfreq: float,
                         highpass: float | None = 0.5,
                         lowpass: float | None = 100.0,
                         notch: float | None = 50.0) -> np.ndarray:
    """
    Prepara una señal EEG para su visualización.

    Extiende la señal mediante padding reflejado, elimina la tendencia lineal
    y el offset DC, aplica opcionalmente filtros pasa-altos, pasa-bajos y
    notch, y finalmente elimina el padding agregado antes de retornar la
    señal.

    Args:
        signal (np.ndarray): Señal EEG de entrada con forma
            `(n_canales, n_muestras)`.
        sfreq (float): Frecuencia de muestreo de la señal, en Hz.
        highpass (float | None): Frecuencia de corte del filtro pasa-altos,
            en Hz. Si es `None` o no es positiva, no se aplica.
        lowpass (float | None): Frecuencia de corte del filtro pasa-bajos,
            en Hz. Si es `None` o no es positiva, no se aplica.
        notch (float | None): Frecuencia, en Hz, utilizada para el filtro
            notch. Si es `None` o es evaluada como falsa, no se aplica.

    Returns:
        np.ndarray:
            Señal preparada para visualización, con la misma forma que
            `signal`.

    Notes:
        - Se agregan 5 segundos de muestras reflejadas a ambos extremos de
          la señal antes del procesamiento.
        - La señal extendida se detrende linealmente sobre el último eje.
        - Los filtros se aplican sobre la señal extendida para reducir los
          transitorios en los extremos de la señal original.
        - El padding se elimina antes de retornar la señal.
    """
    # Extender la señal 5 segundos a cada lado con muestras reflejadas
    pad_samples = int(sfreq * 5)
    out = np.pad(signal, ((0, 0), (pad_samples, pad_samples)), mode="reflect")

    # Remover tendencias lineales e offset DC en la señal extendida
    out = detrend(out, axis=-1, type="linear")

    # Aplicar filtros sobre la señal extendida
    if highpass and highpass > 0:
        out = highpass_filter(out, sfreq, cutoff=highpass, order=2)
    if lowpass and lowpass > 0:
        out = lowpass_filter(out, sfreq, cutoff=lowpass, order=4)
    if notch:
        out = notch_filter(out, sfreq, freqs=notch)

    # Descartar los 5 segundos de padding para dejar la muestra 0 completamente limpia
    return out[:, pad_samples:-pad_samples]
