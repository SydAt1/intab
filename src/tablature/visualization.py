import base64
import io
import matplotlib
matplotlib.use('Agg') # Safe for server environments without display
import matplotlib.pyplot as plt


def generate_ascii_tab(notes, total_length_sec=None):
    """
    Generates an ASCII guitar tablature from detected notes.
    
    Uses a resolution of 10 characters per second.
    Multi-digit fret numbers (e.g., 12) are rendered correctly.
    Sustained notes are shown with repeated fret digits or dashes.
    """
    if not notes:
        return "No notes detected — the model predicted silence for the entire clip."

    if total_length_sec is None:
        total_length_sec = max(n['onset'] + n['duration'] for n in notes) + 1

    chars_per_sec = 10
    total_chars = int(total_length_sec * chars_per_sec)

    # Initialize 6 strings with dashes
    tab_lines = {i: ['-'] * total_chars for i in range(1, 7)}

    # Sort notes by onset so earlier notes take priority on overlap
    sorted_notes = sorted(notes, key=lambda n: n['onset'])

    for note in sorted_notes:
        string = note['string']
        fret = note['fret']
        start_idx = int(note['onset'] * chars_per_sec)
        fret_str = str(fret)

        # Place fret number at the onset position
        for i, digit in enumerate(fret_str):
            pos = start_idx + i
            if 0 <= pos < total_chars:
                tab_lines[string][pos] = digit

    lines = ["=== ASCII Guitar Tablature ===", ""]
    labels = ['e', 'B', 'G', 'D', 'A', 'E']
    for s in range(1, 7):
        lines.append(f"{labels[s-1]}|---" + ''.join(tab_lines[s]) + "---|")

    # Time ruler
    ruler = "      "
    for sec in range(int(total_length_sec) + 1):
        ruler += str(sec).ljust(chars_per_sec)
    lines.append(ruler.rstrip() + "  seconds")
    
    return "\n".join(lines)


def generate_fretboard_plot_base64(notes, total_length_sec=None):
    """
    Creates a fretboard-style visualization with note events as colored blocks.
    Returns a base64-encoded PNG image.
    """
    if not notes:
        return None

    if total_length_sec is None:
        total_length_sec = max(n['onset'] + n['duration'] for n in notes) + 1

    fig, ax = plt.subplots(figsize=(max(14, total_length_sec * 1.5), 6))
    ax.set_xlim(0, total_length_sec)
    ax.set_ylim(-0.5, 5.5)

    ax.set_yticks(range(6))
    ax.set_yticklabels(['e (1)', 'B (2)', 'G (3)', 'D (4)', 'A (5)', 'E (6)'])
    ax.set_xlabel('Time (seconds)')
    ax.set_title('Detected Notes on Fretboard')
    ax.grid(True, axis='x', alpha=0.3, linestyle='--')

    # Draw string lines
    for y in range(6):
        ax.hlines(y, 0, total_length_sec, color='gray', linewidth=1.5, alpha=0.5)

    # Draw note events as rounded rectangles with fret labels
    for note in notes:
        y_pos = note['string'] - 1
        onset = note['onset']
        duration = note['duration']
        fret = note['fret']

        # Draw a colored bar for the note duration
        rect = plt.Rectangle(
            (onset, y_pos - 0.2), duration, 0.4,
            facecolor='#e74c3c', edgecolor='#c0392b',
            alpha=0.85, linewidth=1, zorder=3
        )
        ax.add_patch(rect)

        # Fret number label centered on the bar
        x_center = onset + duration / 2
        ax.text(x_center, y_pos, str(fret),
                color='white', fontsize=10, fontweight='bold',
                ha='center', va='center', zorder=4)

    ax.invert_yaxis()  # e (high) at top, E (low) at bottom
    plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return img_base64
