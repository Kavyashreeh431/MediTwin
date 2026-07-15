from django.urls import path
from .views import remedy_view


urlpatterns = [

path(
"",
remedy_view,
name="remedy"
)

]