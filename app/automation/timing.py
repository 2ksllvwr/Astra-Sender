"""Prepare ahead of time; wait against the local wall clock without sending early."""
import time
from datetime import datetime

PREPARE_SECONDS = 12
MAX_LATENESS = 1.0


def wait_for_dispatch(target, check, clock=time.time, sleep=time.sleep):
    while True:
        check()
        remaining = target - clock()
        if remaining <= 0:
            if -remaining > MAX_LATENESS:
                raise RuntimeError('Horário perdido por mais de 1 segundo. Envio cancelado; confira o rascunho no destino.')
            return
        sleep(min(0.05, remaining / 2) if remaining > .004 else .001)


def dispatch_enter(press, check, target=None, clock=time.time, sleep=time.sleep):
    if target is not None:
        wait_for_dispatch(target, check, clock, sleep)
    check()
    stamp = clock()
    if target is not None and stamp - target > MAX_LATENESS:
        raise RuntimeError('A validação ultrapassou o horário. Enter não foi enviado.')
    press('enter', _pause=False)
    when = datetime.fromtimestamp(stamp).strftime('%H:%M:%S.%f')[:-3]
    detail = f'Enter solicitado às {when}'
    if target is not None:
        detail += f'; atraso local: {max(0, (stamp - target) * 1000):.0f} ms'
    return detail + '. Recebimento da mensagem não confirmado.'
