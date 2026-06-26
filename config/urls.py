from django.contrib import admin
from django.urls import path
from django.conf.urls import include

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('board.urls')),
    path('', include('member.urls')),
    path('predict_incoming/', views.predict_incoming, name='predict_incoming'),
    path('mac/', views.mac_analysis, name='mac_analysis'),
]