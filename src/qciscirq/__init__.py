"""Interop between QCIS and Cirq."""

from qciscirq.gate_table import GateTable

from qciscirq.context import CONTEXT_START, CONTEXT_END, context_wrapper

from qciscirq.dynamical_decoupling import DynamicalDecoupling, CPMG, XY, XYYX

from qciscirq.convert_cirq_to_qcis import cirq_to_qcis
from qciscirq.convert_qcis_to_cirq import qcis_to_cirq


JSON_RESOLVERS_DICT = {
    "CPMG": CPMG,
    "XY": XY,
    "XYYX": XYYX,
}

JSON_RESOLVERS = JSON_RESOLVERS_DICT.get
