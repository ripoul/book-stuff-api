from django.contrib.auth.models import User
from django.test import TestCase
from guardian.shortcuts import assign_perm

from booking.constants.invitation import PlaceInvitationStatus
from booking.models import Place, PlaceInvitation


class InvitationSignalTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="sig-owner", email="owner@example.com", password="pw"
        )
        self.invitee = User.objects.create_user(
            username="sig-invitee", email="invitee@example.com", password="pw"
        )
        self.place = Place.objects.create(name="P", public=False)
        assign_perm("booking.manage_place", self.owner, self.place)

    def _create_invitation(
        self, status: str = PlaceInvitationStatus.PENDING, accepted_by=None
    ) -> PlaceInvitation:
        return PlaceInvitation.objects.create(
            place=self.place,
            email=self.invitee.email,
            invited_by=self.owner,
            status=status,
            accepted_by=accepted_by,
        )

    def test_pending_creation_does_not_grant_can_see(self):
        self._create_invitation()
        self.assertFalse(self.invitee.has_perm("booking.can_see", self.place))

    def test_transition_pending_to_accepted_grants_can_see(self):
        invitation = self._create_invitation()
        invitation.status = PlaceInvitationStatus.ACCEPTED
        invitation.accepted_by = self.invitee
        invitation.save()
        self.assertTrue(self.invitee.has_perm("booking.can_see", self.place))

    def test_transition_accepted_to_revoked_removes_can_see(self):
        invitation = self._create_invitation()
        invitation.status = PlaceInvitationStatus.ACCEPTED
        invitation.accepted_by = self.invitee
        invitation.save()
        self.assertTrue(self.invitee.has_perm("booking.can_see", self.place))

        invitation.status = PlaceInvitationStatus.REVOKED
        invitation.save()
        invitee = User.objects.get(pk=self.invitee.pk)
        self.assertFalse(invitee.has_perm("booking.can_see", self.place))

    def test_transition_accepted_to_declined_removes_can_see(self):
        invitation = self._create_invitation()
        invitation.status = PlaceInvitationStatus.ACCEPTED
        invitation.accepted_by = self.invitee
        invitation.save()
        invitation.status = PlaceInvitationStatus.DECLINED
        invitation.save()
        invitee = User.objects.get(pk=self.invitee.pk)
        self.assertFalse(invitee.has_perm("booking.can_see", self.place))

    def test_transition_pending_to_declined_no_perm_change(self):
        invitation = self._create_invitation()
        invitation.status = PlaceInvitationStatus.DECLINED
        invitation.save()
        self.assertFalse(self.invitee.has_perm("booking.can_see", self.place))

    def test_transition_pending_to_revoked_no_perm_change(self):
        invitation = self._create_invitation()
        invitation.status = PlaceInvitationStatus.REVOKED
        invitation.save()
        self.assertFalse(self.invitee.has_perm("booking.can_see", self.place))

    def test_create_directly_accepted_grants_can_see(self):
        self._create_invitation(
            status=PlaceInvitationStatus.ACCEPTED, accepted_by=self.invitee
        )
        self.assertTrue(self.invitee.has_perm("booking.can_see", self.place))

    def test_accepted_status_idempotent_save_keeps_can_see(self):
        invitation = self._create_invitation()
        invitation.status = PlaceInvitationStatus.ACCEPTED
        invitation.accepted_by = self.invitee
        invitation.save()
        invitation.save()
        self.assertTrue(self.invitee.has_perm("booking.can_see", self.place))

    def test_create_accepted_without_accepted_by_does_not_grant(self):
        self._create_invitation(status=PlaceInvitationStatus.ACCEPTED)
        self.assertFalse(self.invitee.has_perm("booking.can_see", self.place))
