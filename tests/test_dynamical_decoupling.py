import cirq
import pytest

import qciscirq

DD_gates = [
    qciscirq.CPMG(num_pi_pair=2, total_duration_ns=1000, pi_gate='X'),
    qciscirq.CPMG(num_pi_pair=2, total_duration_ns=1000, pi_gate='Y'),
    qciscirq.XY(num_xy_pair=2, total_duration_ns=1000),
    qciscirq.XYYX(num_xyyx_pair=2, total_duration_ns=1000),
]

cirq_diagrams = [
    """
0: ---DD([X]*4)---
    """,
    """
0: ---DD([Y]*4)---
    """,
    """
0: ---DD([X--Y]*2)---
    """,
    """
0: ---DD([X--Y...Y--X]*2)---
    """,
]

expected_qcis = [
    ('# CIRQ_CONTEXT_START\n'
     "# Gate: qciscirq.CPMG(num_pi_pair=2, total_duration_ns=1000, single_pi_gate_duration_ns=50.0, pi_gate='X')\n"
     "# Targets: ['Q00']\n"
     'I Q00 100\n'
     'X Q00\n'
     'I Q00 200\n'
     'X Q00\n'
     'I Q00 200\n'
     'X Q00\n'
     'I Q00 200\n'
     'X Q00\n'
     'I Q00 100\n'
     '# CIRQ_CONTEXT_END\n'
     'B Q00\n'),
    ('# CIRQ_CONTEXT_START\n'
     "# Gate: qciscirq.CPMG(num_pi_pair=2, total_duration_ns=1000, single_pi_gate_duration_ns=50.0, pi_gate='Y')\n"
     "# Targets: ['Q00']\n"
     'I Q00 100\n'
     'Y Q00\n'
     'I Q00 200\n'
     'Y Q00\n'
     'I Q00 200\n'
     'Y Q00\n'
     'I Q00 200\n'
     'Y Q00\n'
     'I Q00 100\n'
     '# CIRQ_CONTEXT_END\n'
     'B Q00\n'),
    ('# CIRQ_CONTEXT_START\n'
     "# Gate: qciscirq.XY(num_xy_pair=2, total_duration_ns=1000, single_pi_gate_duration_ns=50.0)\n"
     "# Targets: ['Q00']\n"
     'I Q00 100\n'
     'X Q00\n'
     'I Q00 200\n'
     'Y Q00\n'
     'I Q00 200\n'
     'X Q00\n'
     'I Q00 200\n'
     'Y Q00\n'
     'I Q00 100\n'
     '# CIRQ_CONTEXT_END\n'
     'B Q00\n'),
    ('# CIRQ_CONTEXT_START\n'
     "# Gate: qciscirq.XYYX(num_xyyx_pair=2, total_duration_ns=1000, single_pi_gate_duration_ns=50.0)\n"
     "# Targets: ['Q00']\n"
     'I Q00 37\n'
     'X Q00\n'
     'I Q00 75\n'
     'Y Q00\n'
     'I Q00 75\n'
     'X Q00\n'
     'I Q00 75\n'
     'Y Q00\n'
     'I Q00 75\n'
     'Y Q00\n'
     'I Q00 75\n'
     'X Q00\n'
     'I Q00 75\n'
     'Y Q00\n'
     'I Q00 75\n'
     'X Q00\n'
     'I Q00 37\n'
     '# CIRQ_CONTEXT_END\n'
     'B Q00\n'),
]


@pytest.mark.parametrize('dd', DD_gates)
def test_dd_repr(dd):
    assert eval(repr(dd), {'qciscirq': qciscirq}) == dd


@pytest.mark.parametrize('dd, diagram', zip(DD_gates, cirq_diagrams))
def test_dd_circuit_diagram(dd, diagram):
    cirq.testing.assert_has_diagram(
        cirq.Circuit(dd.on(cirq.LineQubit(0))),
        diagram,
        use_unicode_characters=False,
    )


@pytest.mark.parametrize('dd', DD_gates)
def test_json_serialization(dd):
    c = cirq.Circuit(dd.on(cirq.LineQubit(0)))
    json = cirq.to_json(c)
    c2 = cirq.read_json(json_text=json, resolvers=[*cirq.DEFAULT_RESOLVERS, qciscirq.JSON_RESOLVERS])
    assert c == c2


def test_gates_validate():
    with pytest.raises(ValueError):
        qciscirq.CPMG(num_pi_pair=2, total_duration_ns=1000, pi_gate='Z')
    with pytest.raises(ValueError):
        qciscirq.CPMG(num_pi_pair=0, total_duration_ns=1000)
    with pytest.raises(ValueError):
        qciscirq.CPMG(num_pi_pair=20, total_duration_ns=1000)


@pytest.mark.parametrize('dd, qcis', zip(DD_gates, expected_qcis))
def test_to_qcis(dd, qcis):
    dd = dd.on(cirq.GridQubit(0, 0))
    map_func = {cirq.GridQubit(0, 0): 'Q00'}.get
    actual_qcis = qciscirq.cirq_to_qcis(cirq.Circuit(dd), map_func, ['Q00'])
    assert actual_qcis == qcis
