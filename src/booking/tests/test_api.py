import uuid

from django.contrib.auth.models import User
from django.urls import reverse
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.test import APITestCase

from booking.models import Place, Resource


def unique_slug(prefix: str = "p") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class PlaceAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.other = User.objects.create_user(username="other", password="pw")
        self.viewer = User.objects.create_user(username="viewer", password="pw")

    def test_anonymous_list_only_public_places(self):
        Place.objects.create(name="Pub", slug=unique_slug("pub"), public=True)
        Place.objects.create(name="Prv", slug=unique_slug("prv"), public=False)
        response = self.client.get(reverse("place-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in response.data}
        self.assertIn("Pub", names)
        self.assertNotIn("Prv", names)

    def test_anonymous_retrieve_public_place(self):
        place = Place.objects.create(name="Pub", slug=unique_slug("pub"), public=True)
        url = reverse("place-detail", kwargs={"pk": place.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Pub")

    def test_anonymous_retrieve_private_place_404(self):
        place = Place.objects.create(name="Prv", slug=unique_slug("prv"), public=False)
        url = reverse("place-detail", kwargs={"pk": place.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_create_place_403(self):
        response = self.client.post(
            reverse("place-list"),
            {"name": "N", "slug": unique_slug("n"), "public": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_create_place_assigns_manage(self):
        self.client.force_authenticate(user=self.owner)
        slug = unique_slug("new")
        response = self.client.post(
            reverse("place-list"),
            {"name": "Mine", "slug": slug, "public": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        place = Place.objects.get(slug=slug)
        self.assertTrue(self.owner.has_perm("booking.manage_place", place))

    def test_other_user_cannot_see_private_place_detail(self):
        self.client.force_authenticate(user=self.owner)
        slug = unique_slug("mine")
        r = self.client.post(
            reverse("place-list"),
            {"name": "Mine", "slug": slug, "public": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        place_id = r.data["id"]
        self.client.force_authenticate(user=self.other)
        response = self.client.get(reverse("place-detail", kwargs={"pk": place_id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_with_can_see_can_retrieve_private_not_update(self):
        self.client.force_authenticate(user=self.owner)
        slug = unique_slug("share")
        r = self.client.post(
            reverse("place-list"),
            {"name": "Shared", "slug": slug, "public": False},
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
        slug = unique_slug("own")
        r = self.client.post(
            reverse("place-list"),
            {"name": "O", "slug": slug, "public": False},
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


class ResourceAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="res-owner", password="pw")
        self.viewer = User.objects.create_user(username="res-viewer", password="pw")
        self.slug = unique_slug("pl")
        self.client.force_authenticate(user=self.owner)
        pr = self.client.post(
            reverse("place-list"),
            {"name": "P", "slug": self.slug, "public": False},
            format="json",
        )
        self.assertEqual(pr.status_code, status.HTTP_201_CREATED)
        self.place_id = pr.data["id"]
        self.place = Place.objects.get(pk=self.place_id)

    def test_anonymous_lists_only_resources_on_public_places(self):
        pub_slug = unique_slug("pubpl")
        Place.objects.create(name="PubPl", slug=pub_slug, public=True)
        pub = Place.objects.get(slug=pub_slug)
        Resource.objects.create(place=pub, name="Rpub")
        Resource.objects.create(place=self.place, name="Rpriv")
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("resource-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in response.data}
        self.assertIn("Rpub", names)
        self.assertNotIn("Rpriv", names)

    def test_anonymous_retrieve_resource_public_place(self):
        pub_slug = unique_slug("pubpl2")
        Place.objects.create(name="PubPl", slug=pub_slug, public=True)
        pub = Place.objects.get(slug=pub_slug)
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
        ids = {row["id"] for row in lr.data}
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
