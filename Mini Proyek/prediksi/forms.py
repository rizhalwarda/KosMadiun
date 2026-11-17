from django import forms


class PrediksiForm(forms.Form):
    jarak_km = forms.FloatField(
        label='Jarak ke pusat kota (km)', min_value=0, max_value=30,
        initial=2.0, widget=forms.NumberInput(attrs={'step': '0.1'}),
    )
    ac = forms.ChoiceField(
        label='Fasilitas AC', choices=[('ya', 'Tersedia'), ('tidak', 'Tidak tersedia')],
    )
    rating = forms.FloatField(
        label='Rating (1–5)', min_value=1, max_value=5, initial=4.0,
        widget=forms.NumberInput(attrs={'step': '0.1'}),
    )
