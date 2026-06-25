from django.urls import path

from apps.groups.api.views import (
    AcceptDirectInvitationView,
    AcceptInviteView,
    CreateDirectInviteView,
    CreateInviteView,
    DirectInvitationDetailView,
    GroupArchiveView,
    GroupDetailView,
    GroupListCreateView,
    GroupRestoreView,
    InvitePreviewView,
    LeaveGroupView,
    MembersListView,
    MyDirectInvitationsView,
    RejectDirectInvitationView,
    RemoveMemberView,
    RevokeInviteView,
)

group_urlpatterns = [
    path("", GroupListCreateView.as_view(), name="list_create_groups"),
    path("mine/", GroupListCreateView.as_view(), name="list_my_groups"),
    path("<uuid:group_id>/invites/", CreateInviteView.as_view(), name="create_invite"),
    path("<uuid:group_id>/invites/direct/", CreateDirectInviteView.as_view(), name="create_direct_invite"),
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

recipient_invitation_urlpatterns = [
    path("users/me/group-invitations/", MyDirectInvitationsView.as_view(), name="my_group_invitations"),
    path("group-invitations/<uuid:invite_id>/", DirectInvitationDetailView.as_view(), name="group_invitation_detail"),
    path("group-invitations/<uuid:invite_id>/accept/", AcceptDirectInvitationView.as_view(), name="group_invitation_accept"),
    path("group-invitations/<uuid:invite_id>/reject/", RejectDirectInvitationView.as_view(), name="group_invitation_reject"),
]

urlpatterns = group_urlpatterns
