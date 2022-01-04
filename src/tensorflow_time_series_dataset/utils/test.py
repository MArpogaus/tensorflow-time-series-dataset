from contextlib import nullcontext as does_not_raise

import numpy as np
import pytest


def get_id_and_idx(val):
    id = val // 1e6
    idx = val % 1e4
    return id, idx


def gen_patch(df, idx, size):
    return df.values[np.int(idx) : np.int(idx + size)]


def gen_batch(df, columns, size, ids, lines):
    batch = []
    for id, line in zip(ids, lines):
        if "id" in df.columns:
            p = gen_patch(df[df.id == id[0]][columns], line, size)
        else:
            p = gen_patch(df[columns], line, size)
        batch.append(p)
    return np.float32(batch)


def validate_dataset(
    df,
    ds,
    batch_size,
    history_size,
    prediction_size,
    history_columns,
    meta_columns,
    prediction_columns,
):
    x1_shape = (batch_size, history_size, len(history_columns))
    x2_shape = (batch_size, 1, len(meta_columns))
    y_shape = (batch_size, prediction_size, len(meta_columns))
    for b, (x, y) in enumerate(ds.as_numpy_iterator()):
        print(y.shape)
        x1, x2 = None, None
        if history_size and len(history_columns) and len(meta_columns):
            x1, x2 = x
        elif history_size and len(history_columns):
            x1 = x
        elif len(meta_columns):
            x2 = x

        if x1 is not None:
            assert x1.shape == x1_shape, f"Wrong shape: history ({b})"
            first_val = x1[:, 0]
            ids, lines = get_id_and_idx(first_val)

            assert np.all(
                x1 == gen_batch(df, history_columns, history_size, ids, lines)
            ), f"Wrong data: history ({b})"
            if x2 is not None:
                assert np.all(
                    x2 == gen_batch(df, meta_columns, 1, ids, lines + history_size)
                ), f"wrong data: meta not consecutive ({b})"

            last_val = x1[:, -1]
            ids, lines = get_id_and_idx(last_val)
            y_test = gen_batch(df, prediction_columns, prediction_size, ids, lines + 1)
            assert np.all(y == y_test), f"Wrong data: prediction not consecutive ({b})"

        if x2 is not None:
            first_val = x2[:, 0]
            ids, lines = get_id_and_idx(first_val)
            assert x2.shape == x2_shape, f"Wrong shape: meta ({b})"
            assert np.all(
                x2 == gen_batch(df, meta_columns, 1, ids, lines)
            ), f"Wrong data: meta ({b})"

        assert y.shape == y_shape, f"Wrong shape: prediction ({b})"
        first_val = y[:, 0]
        ids, lines = get_id_and_idx(first_val)
        assert np.all(
            y == gen_batch(df, prediction_columns, prediction_size, ids, lines)
        ), f"Wrong data: prediction ({b})"


def get_ctxmgr(prediction_size):
    if prediction_size <= 0:
        ctxmgr = pytest.raises(
            AssertionError,
            match="prediction_size must be a positive integer greater than zero",
        )
    else:
        ctxmgr = does_not_raise()
    return ctxmgr
