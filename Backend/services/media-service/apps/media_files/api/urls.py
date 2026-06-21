from django.urls import path

from apps.media_files.api.views import HealthView, ListGroupMediaView, MediaDetailView, MediaDownloadView, UploadReceiptView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("receipts/", UploadReceiptView.as_view(), name="upload_receipt"),
    path("files/<uuid:file_id>/", MediaDetailView.as_view(), name="media_detail"),
    path("files/<uuid:file_id>/download/", MediaDownloadView.as_view(), name="media_download"),
    path("groups/<uuid:group_id>/media/", ListGroupMediaView.as_view(), name="group_media_list"),
]
