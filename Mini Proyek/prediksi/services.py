"""Self-contained Ridge regression training and inference for kos prices."""
import csv
import json
import os
from functools import lru_cache
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parent.parent / 'kos_madiun.csv'
MODEL_PATH = Path(__file__).resolve().parent.parent / 'model_kos.json'


def _solve(matrix, vector):
    """Solve a small linear system with Gaussian elimination and pivoting."""
    size = len(vector)
    augmented = [list(map(float, matrix[i])) + [float(vector[i])] for i in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError('Data tidak cukup bervariasi untuk melatih model.')
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    return [augmented[i][-1] for i in range(size)]


def _feature_stats(rows):
    distances = [row['jarak_km'] for row in rows]
    ratings = [row['rating'] for row in rows]
    means = [sum(distances) / len(rows), sum(ratings) / len(rows)]
    scales = []
    for values, mean in zip((distances, ratings), means):
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        scales.append(variance ** 0.5 or 1.0)
    return means, scales


def _vector(jarak_km, ac, rating, means, scales):
    return [1.0, (jarak_km - means[0]) / scales[0],
            (rating - means[1]) / scales[1], 1.0 if ac == 'ya' else 0.0]


def _train(rows):
    means, scales = _feature_stats(rows)
    vectors = [_vector(row['jarak_km'], row['ac'], row['rating'], means, scales)
               for row in rows]
    targets = [row['harga'] for row in rows]
    width = len(vectors[0])
    xtx = [[sum(x[i] * x[j] for x in vectors) for j in range(width)]
           for i in range(width)]
    xty = [sum(x[i] * y for x, y in zip(vectors, targets)) for i in range(width)]
    # Ridge penalty limits unstable coefficients in the small open dataset.
    for i in range(1, width):
        xtx[i][i] += 1.0
    coefficients = _solve(xtx, xty)
    return {'algorithm': 'Ridge Regression', 'features': ['jarak_km', 'rating', 'ac'],
            'means': means, 'scales': scales, 'coefficients': coefficients,
            'ridge_alpha': 1.0, 'target_unit': 'ribu_rupiah_per_bulan'}


@lru_cache(maxsize=1)
def load_data_and_model():
    with DATA_PATH.open(encoding='utf-8-sig', newline='') as source:
        rows = list(csv.DictReader(source))
    if not rows or not {'jarak_km', 'harga', 'ac', 'rating'} <= set(rows[0]):
        raise ValueError('CSV harus memiliki kolom jarak_km, harga, ac, dan rating.')
    cleaned = []
    for row in rows:
        try:
            cleaned.append({
                'nama': (row.get('nama') or 'Kos tanpa nama').strip(),
                'jarak_km': float(row['jarak_km']),
                'ac': row['ac'].strip().lower(),
                'rating': float(row['rating']),
                'harga': float(row['harga']),
            })
        except (TypeError, ValueError):
            continue
    if len(cleaned) < 5:
        raise ValueError('Dataset perlu sedikitnya lima baris numerik yang valid.')

    model = _train(cleaned)
    # Vercel's deployed source directory is read-only; the in-memory model is
    # enough for serverless requests. Keep the JSON artifact for local runs.
    if not os.environ.get('VERCEL'):
        MODEL_PATH.write_text(json.dumps(model, indent=2), encoding='utf-8')
    return cleaned, model


def predict(jarak_km, ac, rating):
    rows, model = load_data_and_model()
    values = _vector(jarak_km, ac, rating, model['means'], model['scales'])
    price = sum(coefficient * value
                for coefficient, value in zip(model['coefficients'], values))
    return max(0, price), rows


def find_similar_kos(rows, jarak_km, ac, rating, limit=3):
    """Rank dataset examples by the same features used for prediction."""
    _, scales = _feature_stats(rows)
    distance_scale, rating_scale = scales
    ranked = []
    for row in rows:
        distance_gap = abs(row['jarak_km'] - jarak_km) / distance_scale
        rating_gap = abs(row['rating'] - rating) / rating_scale
        ac_gap = 0 if row['ac'] == ac else 1
        score = .5 * distance_gap + .3 * rating_gap + .2 * ac_gap
        ranked.append((score, row))
    ranked.sort(key=lambda item: (item[0], abs(item[1]['jarak_km'] - jarak_km)))
    return [dict(row) for _, row in ranked[:limit]]


def price_chart(rows, prediction=None):
    """Return SVG for average price by distance band."""
    groups = {}
    for row in rows:
        band = round(row['jarak_km'])
        groups.setdefault(band, []).append(row['harga'])
    points = [(x, sum(values) / len(values), False) for x, values in sorted(groups.items())]
    if prediction is not None:
        points.append((prediction[0], prediction[1], True))
    if not points:
        return ''
    width, height, left, top = 700, 320, 72, 24
    right, bottom = 18, 44
    max_y = max(y for _, y, _ in points) * 1.18 or 1
    plot_w, plot_h = width - left - right, height - top - bottom
    slot = plot_w / len(points)
    bar_width = min(58, slot * 0.58)
    bars = []
    for index, (distance, price, is_prediction) in enumerate(points):
        bar_height = price / max_y * plot_h
        x = left + index * slot + (slot - bar_width) / 2
        y = top + plot_h - bar_height
        fill = 'url(#predictionFill)' if is_prediction else 'url(#barFill)'
        label = 'Input Anda' if is_prediction else f'{distance} km'
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" '
            f'rx="8" fill="{fill}"><title>{label}: Rp {price * 1000:,.0f}</title></rect>'
            f'<text class="bar-value" x="{x + bar_width / 2:.1f}" y="{max(top + 13, y - 8):.1f}" '
            f'text-anchor="middle">{price:,.0f}</text>'
            f'<text x="{left + index * slot + slot / 2:.1f}" y="{height - 24}" text-anchor="middle">{label}</text>'
        )
    grid = ''.join(
        f'<g><line class="grid" x1="{left}" y1="{top + i * plot_h / 4:.1f}" '
        f'x2="{width-right}" y2="{top + i * plot_h / 4:.1f}"/>'
        f'<text x="{left-9}" y="{top + i * plot_h / 4 + 4:.1f}" text-anchor="end">{max_y * (1-i/4):,.0f}</text></g>'
        for i in range(5)
    )
    return f'''<svg viewBox="0 0 {width} {height}" role="img" aria-label="Grafik batang rata-rata harga kos berdasarkan jarak">
      <defs><linearGradient id="barFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#36a78b"/><stop offset="100%" stop-color="#176b5b"/></linearGradient><linearGradient id="predictionFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#e9a83b"/><stop offset="100%" stop-color="#be7620"/></linearGradient></defs>
      <style>text{{font:11px system-ui;fill:var(--muted)}} .grid{{stroke:var(--line);stroke-width:1;stroke-dasharray:3 5}} .bar-value{{font-weight:650;fill:var(--ink)}}</style>
      {grid}
      <text transform="translate(17 {top + plot_h/2}) rotate(-90)" text-anchor="middle">Harga (ribu Rp)</text>
      {''.join(bars)}
      <text x="{left+plot_w/2}" y="{height-3}" text-anchor="middle">Jarak ke pusat kota</text>
    </svg>'''
