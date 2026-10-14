import os
import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe for server use
import matplotlib.pyplot as plt


def generate_report(room_labels=None, booking_counts=None):
    """
    Generate a room booking frequency bar chart.

    Args:
        room_labels:    list of room codes  (from DB query)
        booking_counts: list of booking totals matching room_labels

    Falls back to placeholder data when called standalone.
    """
    if room_labels is None or booking_counts is None:
        room_labels    = ["10.5.3", "10.5.25", "80.6.5", "56.3.2", "14.12.34"]
        booking_counts = [12, 8, 15, 6, 10]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(room_labels, booking_counts, color="#58a6ff", edgecolor="#1f6feb", linewidth=0.8)

    # Value labels on top of each bar
    for bar, count in zip(bars, booking_counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.2,
            str(count),
            ha="center", va="bottom", fontsize=10, color="#e6edf3"
        )

    ax.set_title("Room Booking Frequency Report", fontsize=14, color="#e6edf3", pad=15)
    ax.set_xlabel("Room Code",        fontsize=11, color="#8b949e")
    ax.set_ylabel("Number of Bookings", fontsize=11, color="#8b949e")
    ax.tick_params(colors="#8b949e")
    ax.set_facecolor("#161b22")
    fig.patch.set_facecolor("#0d1117")

    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")

    output_path = os.path.join(os.path.dirname(__file__), "report.png")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)

    print(f"[REPORT] Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    generate_report()
