import cirq
import pytest

import qciscirq


def test_qcis_to_cirq():
    qcis = ('X2P Q01\n'
            'X2M Q02\n'
            'B Q01 Q02 R01\n'
            'CZ G0201\n'
            'B Q01 Q02 R01\n'
            'M Q01 Q02\n'
            'B Q01 Q02 R01\n')
    q1, q2 = cirq.GridQubit(0, 1), cirq.GridQubit(0, 2)
    map_func = {'Q01': q1, 'Q02': q2}.get
    couplers = {'G0201': ('Q01', 'Q02')}
    cirq_circuit = qciscirq.qcis_to_cirq(qcis, map_func, couplers)
    ideal_cirq_circuit = cirq.FrozenCircuit(
        cirq.Moment(
            (cirq.X**0.5)(q1),
            (cirq.X**-0.5)(q2)
        ),
        cirq.Moment(cirq.CZ(q1, q2)),
        cirq.Moment(cirq.measure(q1, q2, key='Q01,Q02')),
    )
    assert cirq_circuit == ideal_cirq_circuit


def test_parse_context():
    qcis = ('Y2P Q01\n'
            'Y2M Q02\n'
            'B Q01 Q02 R01\n'
            '# This is a test comment1\n'
            'M Q01\n'
            '# CIRQ_CONTEXT_START\n'
            '# Gate: qciscirq.CPMG(num_pi_pair=2, total_duration_ns=1000)\n'
            "# Targets: ['Q02']\n"
            'I Q02 100\n'
            'X Q02\n'
            'I Q02 200\n'
            'X Q02\n'
            'I Q02 200\n'
            '# This is a test comment2\n'
            'X Q02\n'
            'I Q02 200\n'
            'X Q02\n'
            'I Q02 100\n'
            '# CIRQ_CONTEXT_END\n'
            'B Q01 Q02 R01\n'
            )
    q1, q2 = cirq.GridQubit(0, 1), cirq.GridQubit(0, 2)
    expected_cirq = cirq.FrozenCircuit(
        cirq.Moment(
            (cirq.Y**0.5)(q1),
            (cirq.Y**-0.5)(q2)
        ),
        cirq.Moment(
            cirq.measure(q1, key='Q01'),
            qciscirq.CPMG(num_pi_pair=2, total_duration_ns=1000)(q2)
        ),
    )
    actual_cirq = qciscirq.qcis_to_cirq(qcis, {'Q01': q1, 'Q02': q2}.get)
    assert actual_cirq == expected_cirq


@pytest.mark.parametrize('qcis', ['Z Q00\n', 'CNOT G0100\n'])
def test_raise_exceptions(qcis):
    with pytest.raises(ValueError):
        map_func = {'Q00': cirq.GridQubit(0, 0), 'Q01': cirq.GridQubit(0, 1)}.get
        qciscirq.qcis_to_cirq(qcis, map_func, couplers={'G0100': ('Q00', 'Q01')})


def test_not_implemented_error():
    with pytest.raises(NotImplementedError):
        qciscirq.qcis_to_cirq('I Q00 100\n', {'Q00': cirq.GridQubit(0, 0)}.get)


def test_ignore_instructions():
    qcis = ('X2P Q01\n'
            'Z Q02\n'
            'B Q01 Q02\n'
            'I Q01 1000\n'
            'I Q02 1000\n'
            'M Q01\n'
            'M Q02\n')
    actual_cirq = qciscirq.qcis_to_cirq(
        qcis, {'Q01': cirq.GridQubit(0, 1), 'Q02': cirq.GridQubit(0, 2)}.get, ignored_instructions=['I', 'Z'])
    expected_cirq = cirq.FrozenCircuit(
        cirq.Moment((cirq.X**0.5)(cirq.GridQubit(0, 1))),
        cirq.Moment(
            cirq.measure(cirq.GridQubit(0, 1), key='Q01'), cirq.measure(cirq.GridQubit(0, 2), key='Q02')
        ),
    )
    assert actual_cirq == expected_cirq
