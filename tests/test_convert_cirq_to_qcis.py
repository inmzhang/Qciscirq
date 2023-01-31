import cirq
import pytest

import qciscirq


@pytest.fixture
def bell():
    q1, q2 = cirq.GridQubit(0, 1), cirq.GridQubit(0, 2)
    bell_circuit = cirq.Circuit(
        cirq.Moment((cirq.Y ** 0.5)(q1), (cirq.Y ** -0.5)(q2)),
        cirq.Moment(cirq.CZ(q1, q2)),
        cirq.Moment((cirq.Y ** 0.5)(q2)),
        cirq.Moment(cirq.measure(q1, q2)),
    )
    return bell_circuit


@pytest.fixture
def needed_conversion_utils():
    q1, q2 = cirq.GridQubit(0, 1), cirq.GridQubit(0, 2)
    map_func = {q1: 'Q01', q2: 'Q02'}.get
    couplers = {'G0201': ('Q01', 'Q02')}
    all_blockable_qagents = ['Q01', 'Q02', 'R01']
    return map_func, all_blockable_qagents, couplers


@pytest.fixture
def ideal_bell_qcis():
    return ('Y2P Q01\n'
            'Y2M Q02\n'
            'B Q01 Q02 R01\n'
            'CZ G0201\n'
            'B Q01 Q02 R01\n'
            'Y2P Q02\n'
            'B Q01 Q02 R01\n'
            'M Q01 Q02\n'
            'B Q01 Q02 R01\n')


def test_bell_state_conversion(bell, needed_conversion_utils, ideal_bell_qcis):
    qcis = qciscirq.cirq_to_qcis(bell, *needed_conversion_utils)
    assert qcis == ideal_bell_qcis


def test_bell_state_conversion_with_repetition(bell, needed_conversion_utils, ideal_bell_qcis):
    bell_append_repeat = cirq.CircuitOperation(bell.freeze(), repetitions=3)
    qcis = qciscirq.cirq_to_qcis(cirq.Circuit(bell_append_repeat), *needed_conversion_utils)
    assert qcis == ideal_bell_qcis * 3


def test_unsupported_gate_conversion(needed_conversion_utils):
    q1, q2 = cirq.GridQubit(0, 1), cirq.GridQubit(0, 2)
    bell_with_cnot = cirq.Circuit(
        cirq.Moment((cirq.Y ** 0.5)(q1)),
        cirq.Moment(cirq.CNOT(q1, q2)),
        cirq.Moment(cirq.measure(q1, q2, key='m')),
    )
    with pytest.raises(TypeError, match="convert"):
        qciscirq.cirq_to_qcis(bell_with_cnot, *needed_conversion_utils)
    manually_ignore_cnot = qciscirq.cirq_to_qcis(
        bell_with_cnot, *needed_conversion_utils, ignored_gates_or_ops=[cirq.CNOT])
    assert manually_ignore_cnot == ('Y2P Q01\n'
                                    'B Q01 Q02 R01\n'
                                    'M Q01 Q02\n'
                                    'B Q01 Q02 R01\n')


def test_ignore_gate_quietly(bell, needed_conversion_utils, ideal_bell_qcis):
    q1 = cirq.GridQubit(0, 1)
    bell_with_noise = bell.copy()
    bell_with_noise.insert(
        0, cirq.Moment(cirq.DepolarizingChannel(0.1)(q1))
    )
    qcis = qciscirq.cirq_to_qcis(bell_with_noise, *needed_conversion_utils)
    assert qcis == ideal_bell_qcis
