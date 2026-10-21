"""
Стресс-тестирование транзакционной надежности баланса при параллельных запросах (Race Conditions).
Учебный проект МИЭМ НИУ ВШЭ.
"""

import threading
import pytest
from database import init_db, deduct_balance, get_player, refill_player

def test_concurrent_deductions_prevent_negative_balance():
    """
    Проверка гонки данных: 20 параллельных потоков пытаются списать по 100 фишек
    при балансе 500 фишек. Ровно 5 потоков должны преуспеть, остальные 15 - получить отказ.
    Баланс ни при каких условиях не должен стать отрицательным.
    """
    init_db(force=True)
    # Пополняем и сбрасываем баланс до 500
    from database import get_connection
    with get_connection() as conn:
        conn.execute("UPDATE player SET balance = 500 WHERE id = 1")
        conn.commit()

    success_count = 0
    failure_count = 0
    lock = threading.Lock()

    def try_deduct():
        nonlocal success_count, failure_count
        try:
            deduct_balance(100)
            with lock:
                success_count += 1
        except ValueError:
            with lock:
                failure_count += 1

    threads = [threading.Thread(target=try_deduct) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    player = get_player()
    assert success_count == 5
    assert failure_count == 15
    assert player["balance"] == 0
