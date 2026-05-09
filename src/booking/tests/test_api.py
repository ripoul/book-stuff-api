from django.contrib.auth.models import User
from django.urls import reverse
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.test import APITestCase

from booking.models import Place, Resource


def list_results(response):
    return response.data["results"]


class PlaceAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.other = User.objects.create_user(username="other", password="pw")
        self.viewer = User.objects.create_user(username="viewer", password="pw")

    def test_anonymous_list_only_public_places(self):
        Place.objects.create(name="Pub", public=True)
        Place.objects.create(name="Prv", public=False)
        response = self.client.get(reverse("place-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in list_results(response)}
        self.assertIn("Pub", names)
        self.assertNotIn("Prv", names)

    def test_anonymous_list_places_filter_by_name(self):
        Place.objects.create(name="Cafe Alpha", public=True)
        Place.objects.create(name="Shop Beta", public=True)
        response = self.client.get(reverse("place-list"), {"name": "alpha"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in list_results(response)}
        self.assertEqual(names, {"Cafe Alpha"})

    def test_anonymous_retrieve_public_place(self):
        place = Place.objects.create(name="Pub", public=True)
        url = reverse("place-detail", kwargs={"pk": place.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Pub")

    def test_anonymous_retrieve_private_place_404(self):
        place = Place.objects.create(name="Prv", public=False)
        url = reverse("place-detail", kwargs={"pk": place.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_create_place_403(self):
        response = self.client.post(
            reverse("place-list"),
            {"name": "N", "public": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_create_place_assigns_manage(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("place-list"),
            {"name": "Mine", "public": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        place = Place.objects.get(pk=response.data["id"])
        self.assertTrue(self.owner.has_perm("booking.manage_place", place))

    def test_other_user_cannot_see_private_place_detail(self):
        self.client.force_authenticate(user=self.owner)
        r = self.client.post(
            reverse("place-list"),
            {"name": "Mine", "public": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        place_id = r.data["id"]
        self.client.force_authenticate(user=self.other)
        response = self.client.get(reverse("place-detail", kwargs={"pk": place_id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_with_can_see_can_retrieve_private_not_update(self):
        self.client.force_authenticate(user=self.owner)
        r = self.client.post(
            reverse("place-list"),
            {"name": "Shared", "public": False},
            format="json",
        )
        place_id = r.data["id"]
        place = Place.objects.get(pk=place_id)
        assign_perm("booking.can_see", self.viewer, place)
        self.client.force_authenticate(user=self.viewer)
        get_r = self.client.get(reverse("place-detail", kwargs={"pk": place_id}))
        self.assertEqual(get_r.status_code, status.HTTP_200_OK)
        patch_r = self.client.patch(
            reverse("place-detail", kwargs={"pk": place_id}),
            {"name": "Hacked"},
            format="json",
        )
        self.assertEqual(patch_r.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update_private_place(self):
        self.client.force_authenticate(user=self.owner)
        r = self.client.post(
            reverse("place-list"),
            {"name": "O", "public": False},
            format="json",
        )
        place_id = r.data["id"]
        patch_r = self.client.patch(
            reverse("place-detail", kwargs={"pk": place_id}),
            {"name": "Updated"},
            format="json",
        )
        self.assertEqual(patch_r.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_r.data["name"], "Updated")

    def test_anonymous_list_places_ordering_by_name(self):
        Place.objects.create(name="Zed", public=True)
        Place.objects.create(name="Ann", public=True)
        response = self.client.get(reverse("place-list"), {"ordering": "name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [row["name"] for row in list_results(response)]
        self.assertEqual(names, ["Ann", "Zed"])

    def test_anonymous_list_places_limit_offset_pagination(self):
        for i in range(5):
            Place.objects.create(
                name=f"Px{i}",
                public=True,
            )
        response = self.client.get(reverse("place-list"), {"limit": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(list_results(response)), 2)
        self.assertEqual(response.data["count"], 5)
        self.assertIsNotNone(response.data.get("next"))


class ResourceAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="res-owner", password="pw")
        self.viewer = User.objects.create_user(username="res-viewer", password="pw")
        self.client.force_authenticate(user=self.owner)
        pr = self.client.post(
            reverse("place-list"),
            {"name": "P", "public": False},
            format="json",
        )
        self.assertEqual(pr.status_code, status.HTTP_201_CREATED)
        self.place_id = pr.data["id"]
        self.place = Place.objects.get(pk=self.place_id)

    def test_anonymous_lists_only_resources_on_public_places(self):
        pub = Place.objects.create(name="PubPl", public=True)
        Resource.objects.create(place=pub, name="Rpub")
        Resource.objects.create(place=self.place, name="Rpriv")
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("resource-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in list_results(response)}
        self.assertIn("Rpub", names)
        self.assertNotIn("Rpriv", names)

    def test_anonymous_list_resources_filter_by_name(self):
        pub = Place.objects.create(name="PubFl", public=True)
        Resource.objects.create(place=pub, name="Meeting room A")
        Resource.objects.create(place=pub, name="Parking B")
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("resource-list"), {"name": "meeting"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in list_results(response)}
        self.assertEqual(names, {"Meeting room A"})

    def test_anonymous_list_resources_ordering_by_name(self):
        pub = Place.objects.create(name="Ord", public=True)
        Resource.objects.create(place=pub, name="Zebra")
        Resource.objects.create(place=pub, name="Alpha")
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("resource-list"), {"ordering": "name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [
            row["name"] for row in list_results(response) if row["place"] == pub.pk
        ]
        self.assertEqual(names, ["Alpha", "Zebra"])

    def test_anonymous_list_resources_limit_offset_pagination(self):
        pub = Place.objects.create(name="Cur", public=True)
        self.client.force_authenticate(user=None)
        for i in range(5):
            Resource.objects.create(place=pub, name=f"Rcur{i}")
        response = self.client.get(reverse("resource-list"), {"limit": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_results(response)), 2)
        self.assertEqual(response.data["count"], 5)
        self.assertIsNotNone(response.data.get("next"))

    def test_anonymous_retrieve_resource_public_place(self):
        pub = Place.objects.create(name="PubPl", public=True)
        res = Resource.objects.create(place=pub, name="R1")
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("resource-detail", kwargs={"pk": res.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_creates_resource(self):
        response = self.client.post(
            reverse("resource-list"),
            {"place": self.place_id, "name": "Desk"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Resource.objects.filter(place=self.place).count(), 1)

    def test_viewer_with_can_see_cannot_create_resource(self):
        assign_perm("booking.can_see", self.viewer, self.place)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(
            reverse("resource-list"),
            {"place": self.place_id, "name": "No"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_viewer_with_can_see_can_list_and_retrieve(self):
        res = Resource.objects.create(place=self.place, name="Chair")
        assign_perm("booking.can_see", self.viewer, self.place)
        self.client.force_authenticate(user=self.viewer)
        lr = self.client.get(reverse("resource-list"))
        self.assertEqual(lr.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in list_results(lr)}
        self.assertIn(res.pk, ids)
        gr = self.client.get(reverse("resource-detail", kwargs={"pk": res.pk}))
        self.assertEqual(gr.status_code, status.HTTP_200_OK)

    def test_viewer_cannot_patch_resource(self):
        res = Resource.objects.create(place=self.place, name="T")
        assign_perm("booking.can_see", self.viewer, self.place)
        self.client.force_authenticate(user=self.viewer)
        response = self.client.patch(
            reverse("resource-detail", kwargs={"pk": res.pk}),
            {"name": "X"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_patch_and_delete_resource(self):
        res = Resource.objects.create(place=self.place, name="M")
        self.client.force_authenticate(user=self.owner)
        patch_r = self.client.patch(
            reverse("resource-detail", kwargs={"pk": res.pk}),
            {"name": "Renamed"},
            format="json",
        )
        self.assertEqual(patch_r.status_code, status.HTTP_200_OK)
        del_r = self.client.delete(
            reverse("resource-detail", kwargs={"pk": res.pk}),
        )
        self.assertEqual(del_r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Resource.objects.filter(pk=res.pk).exists())
