from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _save_empty(path: Path, title: str) -> None:
    _ensure_parent(path)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.set_title(title)
    ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_method_median_delta(method_agg: pd.DataFrame, out_path: str | Path) -> None:
    path = Path(out_path)
    if method_agg.empty:
        _save_empty(path, "Median Delta vs Reference")
        return

    data = method_agg.sort_values("median_of_cell_median_delta", ascending=True)
    _ensure_parent(path)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(data["method_instance"], data["median_of_cell_median_delta"], color="#2A6F97")
    ax.axhline(0.0, color="black", linewidth=1)
    ax.set_title("Method Median Delta vs Reference")
    ax.set_ylabel("Median of Cell Median Delta")
    ax.set_xlabel("Method Instance")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_method_win_rate(method_agg: pd.DataFrame, out_path: str | Path) -> None:
    path = Path(out_path)
    if method_agg.empty:
        _save_empty(path, "Mean Win Rate vs Reference")
        return

    data = method_agg.sort_values("mean_win_rate", ascending=False)
    _ensure_parent(path)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(data["method_instance"], data["mean_win_rate"], color="#5FA8D3")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Method Mean Win Rate vs Reference")
    ax.set_ylabel("Mean Win Rate")
    ax.set_xlabel("Method Instance")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_behavior_fraction_at_floor(behavior_agg: pd.DataFrame, out_path: str | Path) -> None:
    path = Path(out_path)
    if behavior_agg.empty:
        _save_empty(path, "Behavior: Fraction at Floor")
        return

    data = behavior_agg.dropna(subset=["proxy_fraction_at_floor_mean"]).sort_values(
        "proxy_fraction_at_floor_mean", ascending=False
    )
    if data.empty:
        _save_empty(path, "Behavior: Fraction at Floor")
        return

    _ensure_parent(path)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(data["method_instance"], data["proxy_fraction_at_floor_mean"], color="#8AC926")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Behavior Metric: Mean Fraction at Floor")
    ax.set_ylabel("Mean Fraction at Floor")
    ax.set_xlabel("Method Instance")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_behavior_time_to_first_floor(behavior_agg: pd.DataFrame, out_path: str | Path) -> None:
    path = Path(out_path)
    if behavior_agg.empty:
        _save_empty(path, "Behavior: Time to First Floor")
        return

    data = behavior_agg.dropna(subset=["proxy_time_to_first_floor_gen_mean"]).sort_values(
        "proxy_time_to_first_floor_gen_mean", ascending=True
    )
    if data.empty:
        _save_empty(path, "Behavior: Time to First Floor")
        return

    _ensure_parent(path)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(data["method_instance"], data["proxy_time_to_first_floor_gen_mean"], color="#F9C74F")
    ax.set_title("Behavior Metric: Mean Time to First Floor")
    ax.set_ylabel("Mean Generation Index")
    ax.set_xlabel("Method Instance")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
