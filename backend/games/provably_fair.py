"""
Криптографический модуль генерации случайных чисел (CSPRNG) и
детерминированного Provably Fair механизма на основе HMAC-SHA256.

Особенности:
1. CSPRNG на базе os.urandom (вместо псевдослучайного MT19937).
2. Схема обязательства (Commitment Scheme): хеш серверного сида отдается клиенту ДО ставки.
3. Детерминированное вычисление исходов через HMAC-SHA256(server_seed, f"{client_seed}:{nonce}").
"""

import hashlib
import hmac
import os
import struct
from typing import Tuple, List

class ProvablyFairEngine:
    """
    Движок доказательной честности (Provably Fair) для настольных игр казино.
    Использует криптографические примитивы HMAC-SHA256 и commitment scheme.
    """

    @staticmethod
    def generate_server_seed(bytes_count: int = 32) -> str:
        """Генерирует криптографически стойкий серверный сид из системной энтропии."""
        return os.urandom(bytes_count).hex()

    @staticmethod
    def hash_seed(seed: str) -> str:
        """Вычисляет публичный SHA-256 хеш сида для предварительного коммитмента."""
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_hmac(server_seed: str, client_seed: str, nonce: int) -> hmac.HMAC:
        """Создает HMAC-SHA256 объект на основе серверного и клиентского сидов."""
        message = f"{client_seed}:{nonce}".encode("utf-8")
        key = server_seed.encode("utf-8")
        return hmac.new(key, message, hashlib.sha256)

    @classmethod
    def get_float(cls, server_seed: str, client_seed: str, nonce: int, offset: int = 0) -> float:
        """
        Извлекает равномерно распределенное число в диапазоне [0, 1)
        из 32-битного среза HMAC-SHA256 дайджеста.
        """
        digest = cls.generate_hmac(server_seed, client_seed, nonce).digest()
        byte_slice = digest[offset : offset + 4]
        # Читаем 4 байта как unsigned int в big-endian формате
        (int_val,) = struct.unpack(">I", byte_slice)
        # 0xFFFFFFFF = 4294967295
        return int_val / 4294967296.0

    @classmethod
    def get_int(cls, server_seed: str, client_seed: str, nonce: int, min_val: int, max_val: int, offset: int = 0) -> int:
        """Возвращает целое число в диапазоне [min_val, max_val] включительно."""
        f = cls.get_float(server_seed, client_seed, nonce, offset)
        return min_val + int(f * (max_val - min_val + 1))

    @classmethod
    def shuffle_list(cls, items: list, server_seed: str, client_seed: str, nonce: int) -> list:
        """
        Алгоритм тасования Фишера-Йетса с использованием детерминированных байтов HMAC.
        Используется для генерации карточного башмака (блэкджек).
        """
        shuffled = items.copy()
        n = len(shuffled)
        
        # Получаем достаточный поток псевдослучайных байт через хеш-цепочку
        stream = b""
        chunk_idx = 0
        while len(stream) < n * 4:
            msg = f"{client_seed}:{nonce}:{chunk_idx}".encode("utf-8")
            stream += hmac.new(server_seed.encode("utf-8"), msg, hashlib.sha256).digest()
            chunk_idx += 1

        for i in range(n - 1, 0, -1):
            offset = (n - 1 - i) * 4
            (val,) = struct.unpack(">I", stream[offset : offset + 4])
            j = val % (i + 1)
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]

        return shuffled
