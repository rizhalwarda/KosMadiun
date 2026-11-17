import json
import os
import urllib.error
import urllib.request

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import PrediksiForm
from .services import find_similar_kos, load_data_and_model, predict, price_chart


def beranda(request):
    form = PrediksiForm(request.POST or None)
    result = None
    result_display = None
    chart = ''
    explanation = None
    references = []
    count = 0
    error = None
    try:
        rows, _ = load_data_and_model()
        count = len(rows)
        chart = price_chart(rows)
    except (OSError, ValueError, ImportError) as exc:
        error = str(exc)
    if request.method == 'POST' and form.is_valid():
        try:
            result, rows = predict(
                form.cleaned_data['jarak_km'], form.cleaned_data['ac'],
                form.cleaned_data['rating'],
            )
            result_display = f"{round(result * 1000):,}".replace(',', '.')
            count = len(rows)
            chart = price_chart(rows, prediction=(
                form.cleaned_data['jarak_km'], result,
            ))
            references = _reference_items(
                rows, form.cleaned_data['jarak_km'], form.cleaned_data['ac'],
                form.cleaned_data['rating'], result,
            )
            explanation = _prediction_explanation(
                rows, result, form.cleaned_data['jarak_km'],
                form.cleaned_data['ac'], form.cleaned_data['rating'], references,
            )
        except (OSError, ValueError, ImportError) as exc:
            error = str(exc)
    return render(request, 'prediksi/beranda.html', {
        'form': form, 'result': result, 'result_display': result_display, 'chart': chart,
        'jumlah_data': count, 'error': error, 'explanation': explanation,
        'references': references,
    })


@require_POST
def jelaskan_grafik(request):
    try:
        rows, _ = load_data_and_model()
        jarak = [row['jarak_km'] for row in rows]
        harga = [row['harga'] for row in rows]
        trend = 'cenderung turun' if (max(jarak) > min(jarak) and
                 sum((x - sum(jarak)/len(jarak)) * (y - sum(harga)/len(harga))
                     for x, y in zip(jarak, harga)) < 0) else 'cenderung naik atau relatif stabil'
        prompt = (
            'Jelaskan grafik rata-rata harga sewa kos Madiun vs jarak ke pusat kota '
            f'menggunakan bahasa Indonesia sederhana dalam 2-3 kalimat. Data {len(rows)} kos, '
            f'harga dalam ribuan rupiah per bulan, jarak {min(jarak):g}-{max(jarak):g} km, '
            f'harga {min(harga):g}-{max(harga):g}, hubungan linear sederhana {trend}. '
            'Sampaikan bahwa ini ringkasan deskriptif dan bukan kepastian harga.'
        )
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            return JsonResponse({'explanation': (
                f'Grafik merangkum {len(rows)} kos. Jarak data berkisar {min(jarak):g}–'
                f'{max(jarak):g} km dan harga {min(harga):g}–{max(harga):g} ribu rupiah '
                f'per bulan. Hubungan linear sederhana terlihat {trend}; grafik ini '
                'merangkum data sampel dan bukan kepastian harga.'
            ), 'source': 'local'})
        payload = json.dumps({
            'model': os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile'),
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3, 'max_tokens': 180,
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions', data=payload,
            headers={'Authorization': f'Bearer {api_key}',
                     'Content-Type': 'application/json'}, method='POST',
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            answer = json.loads(response.read().decode('utf-8'))
        explanation = answer['choices'][0]['message']['content'].strip()
        return JsonResponse({'explanation': explanation, 'source': 'groq'})
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            message = 'API key Groq tidak valid. Periksa kembali GROQ_API_KEY.'
        else:
            message = f'Groq sedang tidak dapat menjawab (HTTP {exc.code}). Coba lagi nanti.'
        return JsonResponse({'error': message}, status=502)
    except (urllib.error.URLError, TimeoutError):
        return JsonResponse({'error': 'Tidak dapat terhubung ke Groq. Coba lagi nanti.'}, status=502)
    except (OSError, ValueError, KeyError, ImportError) as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@csrf_exempt
@require_POST
def api_prediksi(request):
    try:
        payload = json.loads(request.body or '{}')
        jarak = float(payload['jarak_km'])
        rating = float(payload['rating'])
        ac = str(payload['ac']).strip().lower()
        if not 0 <= jarak <= 30:
            raise ValueError('Jarak harus berada di antara 0 dan 30 km.')
        if not 1 <= rating <= 5:
            raise ValueError('Rating harus berada di antara 1 dan 5.')
        if ac not in {'ya', 'tidak'}:
            raise ValueError('Pilihan AC harus ya atau tidak.')
        price, rows = predict(jarak, ac, rating)
        chart_data = _chart_points(rows, (jarak, price))
        references = _reference_items(rows, jarak, ac, rating, price)
        explanation = _prediction_explanation(rows, price, jarak, ac, rating, references)
        return JsonResponse({
            'harga_ribu': round(price, 2),
            'harga_rupiah': round(price * 1000),
            'jumlah_data': len(rows),
            'chart_data': chart_data,
            'explanation': explanation,
            'references': references,
        })
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return JsonResponse({'error': str(exc) or 'Input tidak valid.'}, status=400)
    except (OSError, ImportError) as exc:
        return JsonResponse({'error': str(exc)}, status=500)


def api_grafik(request):
    try:
        rows, _ = load_data_and_model()
        chart_data = _chart_points(rows)
        return JsonResponse({'data': chart_data, 'jumlah_data': len(rows)})
    except (OSError, ValueError, ImportError) as exc:
        return JsonResponse({'error': str(exc)}, status=500)


def _chart_points(rows, prediction=None):
    groups = {}
    for row in rows:
        band = round(row['jarak_km'])
        groups.setdefault(band, []).append(row['harga'])
    points = [
        {'jarak_km': distance, 'harga_ribu': round(sum(prices) / len(prices), 2),
         'label': f'{distance} km'}
        for distance, prices in sorted(groups.items())
    ]
    if prediction is not None:
        distance, price = prediction
        points.append({
            'jarak_km': distance, 'harga_ribu': round(price, 2),
            'label': 'Input Anda', 'is_prediction': True,
        })
    return points


def _reference_items(rows, jarak, ac, rating, estimate=None):
    items = []
    for row in find_similar_kos(rows, jarak, ac, rating):
        item = {
            'nama': row['nama'],
            'harga_ribu': row['harga'],
            'harga_display': f"Rp {round(row['harga'] * 1000):,}".replace(',', '.'),
            'jarak_km': row['jarak_km'],
            'ac': 'Tersedia' if row['ac'] == 'ya' else 'Tidak tersedia',
            'rating': row['rating'],
        }
        if estimate is not None:
            delta = round(row['harga'] * 1000 - estimate * 1000)
            item['comparison_display'] = (
                'Hampir sama dengan estimasi' if abs(delta) < 500 else
                f"Rp {abs(delta):,}".replace(',', '.') +
                (' lebih mahal dari estimasi' if delta > 0 else ' lebih murah dari estimasi')
            )
        items.append(item)
    return items


def _prediction_explanation(rows, price, distance, ac, rating, references):
    average = sum(row['harga'] for row in rows) / len(rows)
    grouped = {}
    for row in rows:
        band = round(row['jarak_km'])
        grouped.setdefault(band, []).append(row['harga'])
    nearest = min(grouped, key=lambda band: abs(band - distance))
    nearest_average = sum(grouped[nearest]) / len(grouped[nearest])
    difference = price - average
    percent_difference = abs(difference) / average * 100 if average else 0
    if difference > 0:
        comparison = f'{percent_difference:.1f}% di atas rata-rata dataset'
    elif difference < 0:
        comparison = f'{percent_difference:.1f}% di bawah rata-rata dataset'
    else:
        comparison = 'sama dengan rata-rata dataset'

    rupiah = lambda value: f"Rp {round(value * 1000):,}".replace(',', '.')
    fasilitas = 'dengan AC' if ac == 'ya' else 'tanpa AC'
    group_averages = [sum(values) / len(values) for values in grouped.values()]
    reference_comparisons = ', '.join(
        f"{reference['nama']} {reference['harga_display']} "
        f"({reference['comparison_display']})"
        for reference in references
    )
    local_explanation = (
        f'Estimasi untuk jarak {distance:g} km, {fasilitas}, dan rating {rating:g} adalah '
        f'{rupiah(price)} per bulan, {comparison} ({rupiah(average)}). '
        f'Grafik menunjukkan rata-rata harga per kelompok jarak dari {rupiah(min(group_averages))} '
        f'sampai {rupiah(max(group_averages))}; kelompok terdekat ({nearest} km) rata-ratanya '
        f'{rupiah(nearest_average)}. Referensi aktual: {reference_comparisons}; harga utama '
        'nilai utama merupakan estimasi model.'
    )
    return _generate_ai_explanation(
        local_explanation, rows, price, distance, ac, rating, references,
    )


def _generate_ai_explanation(fallback, rows, price, distance, ac, rating, references):
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return fallback
    details = {
        'jumlah_data': len(rows),
        'input': {'jarak_km': distance, 'ac': ac, 'rating': rating},
        'estimasi_ribu_rupiah_per_bulan': round(price, 2),
        'harga_rata_rata_dataset_ribu': round(sum(row['harga'] for row in rows) / len(rows), 2),
        'data_grafik_per_jarak': [
            {'jarak_km': distance_bin,
             'rata_rata_harga_ribu': round(sum(values) / len(values), 2)}
            for distance_bin, values in sorted(_group_prices(rows).items())
        ],
        'kos_referensi_aktual': [
            {'nama': item['nama'], 'harga_rupiah': item['harga_display'],
             'jarak_km': item['jarak_km'], 'ac': item['ac'], 'rating': item['rating'],
             'selisih_terhadap_estimasi': item['comparison_display']}
            for item in references
        ],
    }
    prompt = (
        'Jelaskan hasil ini dalam bahasa Indonesia yang jelas, maksimal 3 kalimat dan 65 kata. '
        'Kalimat pertama membandingkan estimasi dengan rata-rata dataset. Kalimat kedua merangkum '
        'rentang harga pada grafik dan kelompok jarak terdekat. Kalimat ketiga menyebut nama, '
        'harga aktual, dan selisih terhadap estimasi untuk ketiga kos referensi. Tegaskan bahwa '
        'harga referensi adalah data aktual dan estimasi adalah keluaran model. Jangan mengarang fakta. '
        f'Gunakan hanya data ini: {json.dumps(details, ensure_ascii=False)}'
    )
    payload = json.dumps({
        'model': os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile'),
        'messages': [
            {'role': 'system', 'content': 'Anda menjelaskan hasil analisis data kos secara akurat dan mudah dipahami.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.2, 'max_tokens': 190,
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.groq.com/openai/v1/chat/completions', data=payload,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            answer = json.loads(response.read().decode('utf-8'))
        return answer['choices'][0]['message']['content'].strip() or fallback
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
            ValueError, KeyError, IndexError):
        return fallback


def _group_prices(rows):
    grouped = {}
    for row in rows:
        band = round(row['jarak_km'])
        grouped.setdefault(band, []).append(row['harga'])
    return grouped


@csrf_exempt
@require_POST
def api_jelaskan_grafik(request):
    return jelaskan_grafik(request)
