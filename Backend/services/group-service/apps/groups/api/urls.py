from django.urls import path

from apps.groups.api.views import (
    AcceptInviteView,
    CreateInviteView,
    GroupArchiveView,
    GroupDetailView,
    GroupListCreateView,
    GroupRestoreView,
    InvitePreviewView,
    LeaveGroupView,
    MembersListView,
    RemoveMemberView,
    RevokeInviteView,
)

urlpatterns = [
    path("", GroupListCreateView.as_view(), name="list_create_groups"),
    path("mine/", GroupListCreateView.as_view(), name="list_my_groups"),
    path("<uuid:group_id>/invites/", CreateInviteView.as_view(), name="create_invite"),
    path("invites/<str:token>/", InvitePreviewView.as_view(), name="preview_invite"),
    path("invites/<str:token>/accept/", AcceptInviteView.as_view(), name="accept_invite"),
    path("<uuid:group_id>/invites/<uuid:invite_id>/revoke/", RevokeInviteView.as_view(), name="revoke_invite"),
    path("<uuid:group_id>/members/", MembersListView.as_view(), name="list_members"),
    path("<uuid:group_id>/members/<uuid:member_id>/remove/", RemoveMemberView.as_view(), name="remove_member"),
    path("<uuid:group_id>/leave/", LeaveGroupView.as_view(), name="leave_group"),
    path("<uuid:group_id>/restore/", GroupRestoreView.as_view(), name="group_restore"),
    path("<uuid:group_id>/archive/", GroupArchiveView.as_view(), name="group_archive"),
    path("<uuid:group_id>/", GroupDetailView.as_view(), name="group_detail"),
]
