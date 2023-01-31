# Qciscirq

> Current version: v0.1-beta

Adaptors for translating quantum circuits between `QCIS` and `cirq.Circuit`.

## What is `qciscirq`

`QCIS` is a quantum circuit instruction set used in
Xiaobo Zhu group at USTC. `QCIS` is designed deliberately to work on 
hardware. They are low-level instructions and can be hard to write from
scratch, which requires heavy string manipulation.

`cirq` is an open-source quantum computing framework proposed by Google. It provides
a high-level quantum circuit API and a simulator for simulating quantum circuits. Writing
quantum circuits in `cirq` is much easier than `QCIS`.

This package(`qciscirq`) provides an adaptor for translating quantum circuits between `QCIS` and
`cirq.Circuit`. The supported translation units are limited by the relatively small number of
`QCIS` instructions. Additionally, `qciscirq` defines some cirq extension gates for some operation
abstractions such as dynamical decoupling sequence.

## Installation

`qciscirq` can be installed with `pip`:
```shell
pip install qciscirq
```

## API Reference

### `qciscirq.cirq_to_qcis`

```
Convert cirq circuit to QCIS circuit.

Args:
    circuit: The cirq circuit to be converted.
    map_func: A function that maps cirq.GridQubit to a string.
    all_blockable_qagents: All qagents that can be blocked, used in 'B' operation.
    couplers: A dictionary mapping coupler names to qubit pairs, used in CZ operation conversion.
        Defaults to None. When the circuit contains CZ gates, this argument must be provided.
    ignored_gates_or_ops: Specify the gates or operations to ignore when converting from cirq to qcis.
        Defaults to None. When None, the default set of gates or operations to ignore will be used, including
        stimcirq extension operations and cirq noise channel gates. When not None, the ignored set used will be
        the union of the default set and the set specified by this argument.

Returns:
    The QCIS circuit.

Examples:
    >>> import cirq
    >>> import qciscirq
    >>> q1, q2 = cirq.GridQubit.rect(1, 2)
    >>> print(qciscirq.cirq_to_qcis(
    ...     cirq.Circuit(
    ...         cirq.Moment((cirq.Y ** 0.5)(q1), (cirq.Y ** -0.5)(q2)),
    ...         cirq.Moment(cirq.CZ(q1, q2)),
    ...         cirq.Moment((cirq.Y ** 0.5)(q2)),
    ...         cirq.Moment(cirq.measure(q1, q2)),
    ...     ),
    ...     map_func={q1: 'Q01', q2: 'Q02'}.get,
    ...     all_blockable_qagents = ['Q01', 'Q02', 'R01'],
    ...     couplers = {'G0201': ('Q01', 'Q02')}))
    Y2P Q01
    Y2M Q02
    B Q01 Q02 R01
    CZ G0201
    B Q01 Q02 R01
    Y2P Q02
    B Q01 Q02 R01
    M Q01 Q02
    B Q01 Q02 R01
```

### `qciscirq.qcis_to_cirq`

```
Convert QCIS circuit to cirq circuit.

Args:
    qcis: The QCIS circuit to be converted.
    map_func: A function that maps a string to cirq.GridQubit.
    couplers: A dictionary mapping coupler names to qubit pairs, used in CZ operation conversion.
        Defaults to None. When qcis contains CZ operations, couplers must be provided.
    ignored_instructions: Instructions to be ignored. Defaults to None. When not None, the instructions
        start with the strings in this set will be ignored.

Returns:
    The cirq circuit.

Examples:
    >>> import cirq
    >>> import qciscirq
    >>> q1, q2 = cirq.GridQubit(0, 1), cirq.GridQubit(0, 2)
    >>> qcis_circuit = '''X2P Q01
    ... X2M Q02
    ... B Q01 Q02 R01
    ... CZ G0201
    ... B Q01 Q02 R01
    ... M Q01 Q02
    ... B Q01 Q02 R01
    ... '''
    >>> print(qciscirq.qcis_to_cirq(
    ...    qcis_circuit,
    ...    map_func={'Q01': q1, 'Q02': q2}.get,
    ...    couplers={'G0201': ('Q01', 'Q02')}))
    (0, 1): ───X^0.5────@───M('Q01,Q02')───
                        │   │
    (0, 2): ───X^-0.5───@───M──────────────
```
