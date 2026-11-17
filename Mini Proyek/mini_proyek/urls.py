"""
URL configuration for mini_proyek project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from prediksi import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.beranda, name='beranda'),
    path('jelaskan/', views.jelaskan_grafik, name='jelaskan_grafik'),
    path('api/predict/', views.api_prediksi, name='api_prediksi'),
    path('api/chart/', views.api_grafik, name='api_grafik'),
    path('api/explain/', views.api_jelaskan_grafik, name='api_jelaskan_grafik'),
]
