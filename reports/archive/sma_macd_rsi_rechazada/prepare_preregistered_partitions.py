"""Partición estricta 60/20/20 y aislamiento físico del Holdout."""
import hashlib
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/processed")
TRAIN_VAL_DIR = DATA_DIR / "train_val"
HOLDOUT_DIR = Path("data/locked_holdout")


def main():
    TRAIN_VAL_DIR.mkdir(parents=True, exist_ok=True)
    HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)

    assets = ["ES", "NQ", "BTC_USDT", "ETH_USDT"]
    for sym in assets:
        p = DATA_DIR / f"{sym}_4h.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        n = len(df)
        n_train = int(n * 0.60)
        n_val = int(n * 0.20)

        df_train = df.iloc[:n_train].copy().reset_index(drop=True)
        df_val = df.iloc[n_train:n_train + n_val].copy().reset_index(drop=True)
        df_holdout = df.iloc[n_train + n_val:].copy().reset_index(drop=True)

        # Guardar Train y Val para la investigación
        train_p = TRAIN_VAL_DIR / f"{sym}_4h_train.parquet"
        val_p = TRAIN_VAL_DIR / f"{sym}_4h_val.parquet"
        df_train.to_parquet(train_p, index=False)
        df_val.to_parquet(val_p, index=False)

        # Guardar Holdout bloqueado en directorio aislado
        holdout_p = HOLDOUT_DIR / f"{sym}_4h_holdout_LOCKED.parquet"
        df_holdout.to_parquet(holdout_p, index=False)

        # Calcular hash de bloqueo
        h = hashlib.sha256(open(holdout_p, "rb").read()).hexdigest()
        with open(HOLDOUT_DIR / f"{sym}_holdout.sha256", "w") as f:
            f.write(h)

        print(
            f"Partición {sym}: Train={len(df_train)} ({df_train['ts_event'].iloc[0].date()} a {df_train['ts_event'].iloc[-1].date()}) | "
            f"Val={len(df_val)} ({df_val['ts_event'].iloc[0].date()} a {df_val['ts_event'].iloc[-1].date()}) | "
            f"Holdout={len(df_holdout)} ({df_holdout['ts_event'].iloc[0].date()} a {df_holdout['ts_event'].iloc[-1].date()})"
        )


if __name__ == "__main__":
    main()
