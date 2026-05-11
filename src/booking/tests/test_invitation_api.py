from django.contrib.auth.models import User
from django.urls import reverse
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.test import APITestCase

from booking.constants.invitation import PlaceInvitationStatus
from booking.models import Place, PlaceInvitation


def list_results(response):
    return response.data["results"]


class MyInvitationAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="me-owner", email="owner@example.com", password="pw"
        )
        self.invitee = User.objects.create_user(
            username="me-invitee", email="invitee@example.com", password="pw"
        )
        self.other = User.objects.create_user(
            username="me-other", email="other@example.com", password="pw"
        )
        self.place = Place.objects.create(name="P", public=False)
        assign_perm("booking.manage_place", self.owner, self.place)
        self.invitation = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
        )

    def _detail_url(self, pk):
        return reverse("my-invitation-detail", kwargs={"pk": pk})

    def test_anonymous_list_forbidden(self):
        response = self.client.get(reverse("my-invitation-list"))
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_authenticated_list_only_own_invitations(self):
        PlaceInvitation.objects.create(
            place=self.place,
            email=self.other.email,
            invited_by=self.owner,
        )
        self.client.force_authenticate(user=self.invitee)
        response = self.client.get(reverse("my-invitation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in list_results(response)}
        self.assertEqual(ids, {str(self.invitation.pk)})

    def test_list_exposes_place_name(self):
        self.client.force_authenticate(user=self.invitee)
        response = self.client.get(reverse("my-invitation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = list_results(response)[0]
        self.assertEqual(row["place_name"], self.place.name)

    def test_list_email_matching_is_case_insensitive(self):
        self.invitation.email = "Invitee@Example.COM"
        self.invitation.save()
        self.client.force_authenticate(user=self.invitee)
        response = self.client.get(reverse("my-invitation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_results(response)), 1)

    def test_list_filter_by_status(self):
        PlaceInvitation.objects.create(
            place=Place.objects.create(name="P2", public=False),
            email=self.invitee.email,
            invited_by=self.owner,
            status=PlaceInvitationStatus.DECLINED,
        )
        self.client.force_authenticate(user=self.invitee)
        response = self.client.get(
            reverse("my-invitation-list"),
            {"status": PlaceInvitationStatus.PENDING},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = {row["status"] for row in list_results(response)}
        self.assertEqual(statuses, {PlaceInvitationStatus.PENDING})

    def test_accept_sets_accepted_by_and_grants_can_see(self):
        self.client.force_authenticate(user=self.invitee)
        response = self.client.patch(
            self._detail_url(self.invitation.pk),
            {"status": PlaceInvitationStatus.ACCEPTED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, PlaceInvitationStatus.ACCEPTED)
        self.assertEqual(self.invitation.accepted_by, self.invitee)
        self.assertTrue(self.invitee.has_perm("booking.can_see", self.place))

    def test_decline_keeps_accepted_by_null_and_no_perm(self):
        self.client.force_authenticate(user=self.invitee)
        response = self.client.patch(
            self._detail_url(self.invitation.pk),
            {"status": PlaceInvitationStatus.DECLINED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, PlaceInvitationStatus.DECLINED)
        self.assertIsNone(self.invitation.accepted_by)
        self.assertFalse(self.invitee.has_perm("booking.can_see", self.place))

    def test_decline_after_accept_removes_can_see(self):
        self.client.force_authenticate(user=self.invitee)
        accept = self.client.patch(
            self._detail_url(self.invitation.pk),
            {"status": PlaceInvitationStatus.ACCEPTED},
            format="json",
        )
        self.assertEqual(accept.status_code, status.HTTP_200_OK)
        self.assertTrue(self.invitee.has_perm("booking.can_see", self.place))

        decline = self.client.patch(
            self._detail_url(self.invitation.pk),
            {"status": PlaceInvitationStatus.DECLINED},
            format="json",
        )
        self.assertEqual(decline.status_code, status.HTTP_200_OK)
        invitee = User.objects.get(pk=self.invitee.pk)
        self.assertFalse(invitee.has_perm("booking.can_see", self.place))

    def test_accept_after_decline_grants_can_see(self):
        self.invitation.status = PlaceInvitationStatus.DECLINED
        self.invitation.save()
        self.client.force_authenticate(user=self.invitee)
        response = self.client.patch(
            self._detail_url(self.invitation.pk),
            {"status": PlaceInvitationStatus.ACCEPTED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, PlaceInvitationStatus.ACCEPTED)
        self.assertEqual(self.invitation.accepted_by, self.invitee)
        self.assertTrue(self.invitee.has_perm("booking.can_see", self.place))

    def test_invalid_transition_pending_to_revoked_is_400(self):
        self.client.force_authenticate(user=self.invitee)
        response = self.client.patch(
            self._detail_url(self.invitation.pk),
            {"status": PlaceInvitationStatus.REVOKED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_transition_accepted_to_revoked_is_400(self):
        self.invitation.status = PlaceInvitationStatus.ACCEPTED
        self.invitation.accepted_by = self.invitee
        self.invitation.save()
        self.client.force_authenticate(user=self.invitee)
        response = self.client.patch(
            self._detail_url(self.invitation.pk),
            {"status": PlaceInvitationStatus.REVOKED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_patch_invitation_of_another_user(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.patch(
            self._detail_url(self.invitation.pk),
            {"status": PlaceInvitationStatus.DECLINED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_not_allowed_on_my_endpoint(self):
        self.client.force_authenticate(user=self.invitee)
        response = self.client.post(
            reverse("my-invitation-list"),
            {"place": str(self.place.pk), "email": self.invitee.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_place_is_ignored(self):
        other_place = Place.objects.create(name="Other", public=False)
        self.client.force_authenticate(user=self.invitee)
        response = self.client.patch(
            self._detail_url(self.invitation.pk),
            {
                "place": str(other_place.pk),
                "status": PlaceInvitationStatus.ACCEPTED,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.place, self.place)


class ManagerInvitationAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="mgr-owner", email="owner@example.com", password="pw"
        )
        self.other_owner = User.objects.create_user(
            username="mgr-other", email="other-owner@example.com", password="pw"
        )
        self.invitee = User.objects.create_user(
            username="mgr-invitee", email="invitee@example.com", password="pw"
        )

        self.place = Place.objects.create(name="Mine", public=False)
        assign_perm("booking.manage_place", self.owner, self.place)

        self.other_place = Place.objects.create(name="Theirs", public=False)
        assign_perm("booking.manage_place", self.other_owner, self.other_place)

    def _detail_url(self, pk):
        return reverse("manager-invitation-detail", kwargs={"pk": pk})

    def test_anonymous_list_forbidden(self):
        response = self.client.get(reverse("manager-invitation-list"))
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_non_manager_sees_no_invitations(self):
        PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
        )
        self.client.force_authenticate(user=self.invitee)
        response = self.client.get(reverse("manager-invitation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_results(response), [])

    def test_manager_only_sees_invitations_of_managed_places(self):
        mine = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
        )
        PlaceInvitation.objects.create(
            place=self.other_place,
            email=self.invitee.email,
            invited_by=self.other_owner,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse("manager-invitation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in list_results(response)}
        self.assertEqual(ids, {str(mine.pk)})

    def test_filter_by_place(self):
        another = Place.objects.create(name="Mine 2", public=False)
        assign_perm("booking.manage_place", self.owner, another)
        i1 = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
        )
        PlaceInvitation.objects.create(
            place=another,
            email=self.invitee.email,
            invited_by=self.owner,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            reverse("manager-invitation-list"),
            {"place": str(self.place.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in list_results(response)}
        self.assertEqual(ids, {str(i1.pk)})

    def test_filter_by_multiple_statuses_or_logic(self):
        pending = PlaceInvitation.objects.create(
            place=self.place,
            email="a@example.com",
            invited_by=self.owner,
        )
        another_place = Place.objects.create(name="Mine 2", public=False)
        assign_perm("booking.manage_place", self.owner, another_place)
        declined = PlaceInvitation.objects.create(
            place=another_place,
            email="b@example.com",
            invited_by=self.owner,
            status=PlaceInvitationStatus.DECLINED,
        )
        PlaceInvitation.objects.create(
            place=another_place,
            email="c@example.com",
            invited_by=self.owner,
            status=PlaceInvitationStatus.REVOKED,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            reverse("manager-invitation-list"),
            {
                "status": [
                    PlaceInvitationStatus.PENDING,
                    PlaceInvitationStatus.DECLINED,
                ]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in list_results(response)}
        self.assertEqual(ids, {str(pending.pk), str(declined.pk)})

    def test_manager_creates_invitation_sets_invited_by_and_pending(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("manager-invitation-list"),
            {"place": str(self.place.pk), "email": "new@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], PlaceInvitationStatus.PENDING)
        created = PlaceInvitation.objects.get(pk=response.data["id"])
        self.assertEqual(created.invited_by, self.owner)
        self.assertEqual(created.place, self.place)

    def test_non_manager_cannot_create_invitation_for_place(self):
        self.client.force_authenticate(user=self.invitee)
        response = self.client.post(
            reverse("manager-invitation-list"),
            {"place": str(self.place.pk), "email": "x@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_with_non_pending_status_is_400(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("manager-invitation-list"),
            {
                "place": str(self.place.pk),
                "email": "x@example.com",
                "status": PlaceInvitationStatus.ACCEPTED,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_can_revoke_pending_invitation(self):
        invitation = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self._detail_url(invitation.pk),
            {"status": PlaceInvitationStatus.REVOKED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, PlaceInvitationStatus.REVOKED)

    def test_manager_can_revoke_declined_invitation(self):
        invitation = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
            status=PlaceInvitationStatus.DECLINED,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self._detail_url(invitation.pk),
            {"status": PlaceInvitationStatus.REVOKED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, PlaceInvitationStatus.REVOKED)

    def test_manager_can_repend_revoked_invitation(self):
        invitation = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
            status=PlaceInvitationStatus.REVOKED,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self._detail_url(invitation.pk),
            {"status": PlaceInvitationStatus.PENDING},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, PlaceInvitationStatus.PENDING)
        self.assertFalse(self.invitee.has_perm("booking.can_see", self.place))

    def test_manager_revoke_accepted_invitation_removes_can_see(self):
        invitation = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
            status=PlaceInvitationStatus.ACCEPTED,
            accepted_by=self.invitee,
        )
        self.assertTrue(self.invitee.has_perm("booking.can_see", self.place))
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self._detail_url(invitation.pk),
            {"status": PlaceInvitationStatus.REVOKED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitee = User.objects.get(pk=self.invitee.pk)
        self.assertFalse(invitee.has_perm("booking.can_see", self.place))

    def test_manager_cannot_set_status_to_accepted(self):
        invitation = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self._detail_url(invitation.pk),
            {"status": PlaceInvitationStatus.ACCEPTED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_cannot_patch_invitation_of_other_place(self):
        invitation = PlaceInvitation.objects.create(
            place=self.other_place,
            email=self.invitee.email,
            invited_by=self.other_owner,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self._detail_url(invitation.pk),
            {"status": PlaceInvitationStatus.REVOKED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_cannot_change_place_or_email(self):
        invitation = PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
        )
        another = Place.objects.create(name="Mine 2", public=False)
        assign_perm("booking.manage_place", self.owner, another)
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self._detail_url(invitation.pk),
            {"place": str(another.pk), "email": "x@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
