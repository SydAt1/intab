import base64
import io
import matplotlib
matplotlib.use('Agg') # Safe for server environments without display
import matplotlib.pyplot as plt

def generate_ascii_tab(notes, total_length_sec=None):
    if not notes:
        return "No notes detected — try lowering threshold (e.g., 0.3–0.4)"

    if total_length_sec is None:
        total_length_sec = max(n['onset'] + n['duration'] for n in notes) + 1

    # ASCII Tab
    tab_lines = {i: ['-'] * int(total_length_sec * 10) for i in range(1, 7)}
    for note in notes:
        start_idx = int(note['onset'] * 10)
        fret_str = str(note['fret'])
        for i, d in enumerate(fret_str):
            pos = start_idx + i
            if pos < len(tab_lines[note['string']]) and tab_lines[note['string']][pos] == '-':
                tab_lines[note['string']][pos] = d

    lines = ["=== ASCII Guitar Tablature ===", ""]
    labels = ['e', 'B', 'G', 'D', 'A', 'E']
    for s in range(1, 7):
        lines.append(f"{labels[s-1]}|---" + ''.join(tab_lines[s]) + "---|")
    lines.append("      0         1         2         3         4         5     seconds")
    
    return "\n".join(lines)


def generate_fretboard_plot_base64(notes, total_length_sec=None):
    if not notes:
        return None

    if total_length_sec is None:
        total_length_sec = max(n['onset'] + n['duration'] for n in notes) + 1

    plt.figure(figsize=(14, 6))
    plt.xlim(0, total_length_sec)
    plt.ylim(-0.5, 5.5)
    plt.yticks(range(6), ['e (1)', 'B (2)', 'G (3)', 'D (4)', 'A (5)', 'E (6)'])
    plt.xlabel('Time (seconds)')
    plt.title('Detected Notes (red circles = played fret)')
    plt.grid(True, axis='x', alpha=0.5)

    for y in range(6):
        plt.hlines(y, 0, total_length_sec, color='gray', linewidth=2)

    for note in notes:
        y_pos = note['string'] - 1
        x_center = note['onset'] + note['duration'] / 2
        circle = plt.Circle((x_center, y_pos), 0.15, color='red', alpha=0.8)
        plt.gca().add_patch(circle)
        plt.text(x_center, y_pos, str(note['fret']),
                 color='white', fontsize=11, fontweight='bold',
                 ha='center', va='center')

    plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return img_base64
