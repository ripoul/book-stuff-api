from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase
from guardian.shortcuts import assign_perm

from booking.models import Place
from booking.permissions import user_can_see_place


class UserCanSeePlaceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="x")

    def test_public_place_anonymous(self):
        place = Place.objects.create(name="Pub", public=True)
        self.assertTrue(user_can_see_place(AnonymousUser(), place))

    def test_public_place_authenticated(self):
        place = Place.objects.create(name="Pub", public=True)
        self.assertTrue(user_can_see_place(self.user, place))

    def test_private_place_anonymous(self):
        place = Place.objects.create(name="Prv", public=False)
        self.assertFalse(user_can_see_place(AnonymousUser(), place))

    def test_private_place_no_permission(self):
        place = Place.objects.create(name="Prv", public=False)
        self.assertFalse(user_can_see_place(self.user, place))

    def test_private_place_with_can_see(self):
        place = Place.objects.create(name="Prv", public=False)
        assign_perm("booking.can_see", self.user, place)
        self.assertTrue(user_can_see_place(self.user, place))

    def test_private_place_with_manage_place(self):
        place = Place.objects.create(name="Prv", public=False)
        assign_perm("booking.manage_place", self.user, place)
        self.assertTrue(user_can_see_place(self.user, place))
