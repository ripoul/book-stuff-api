from datetime import datetime, timezone as dt_timezone

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
        self.assertFalse(response.data["can_manage"])

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
        self.assertTrue(response.data["can_manage"])
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
        self.assertFalse(get_r.data["can_manage"])
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
        self.assertTrue(patch_r.data["can_manage"])

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

    def test_anonymous_list_places_managed_by_me_empty(self):
        Place.objects.create(name="Pub", public=True)
        response = self.client.get(reverse("place-list"), {"managed_by_me": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_results(response), [])

    def test_authenticated_list_places_managed_by_me(self):
        self.client.force_authenticate(user=self.owner)
        self.client.post(
            reverse("place-list"),
            {"name": "Mine", "public": False},
            format="json",
        )
        self.client.force_authenticate(user=self.other)
        self.client.post(
            reverse("place-list"),
            {"name": "Theirs", "public": True},
            format="json",
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse("place-list"), {"managed_by_me": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in list_results(response)}
        self.assertEqual(names, {"Mine"})


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

    def test_anonymous_list_resources_filter_by_place_list(self):
        pub1 = Place.objects.create(name="F1", public=True)
        pub2 = Place.objects.create(name="F2", public=True)
        Resource.objects.create(place=pub1, name="Rf1a")
        Resource.objects.create(place=pub1, name="Rf1b")
        Resource.objects.create(place=pub2, name="Rf2")
        self.client.force_authenticate(user=None)
        one = self.client.get(
            reverse("resource-list"),
            {"place": [str(pub1.pk)]},
        )
        self.assertEqual(one.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {row["name"] for row in list_results(one)},
            {"Rf1a", "Rf1b"},
        )
        both = self.client.get(
            reverse("resource-list"),
            {"place": [str(pub1.pk), str(pub2.pk)]},
        )
        self.assertEqual(both.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {row["name"] for row in list_results(both)},
            {"Rf1a", "Rf1b", "Rf2"},
        )

    def test_anonymous_list_resources_ordering_by_name(self):
        pub = Place.objects.create(name="Ord", public=True)
        Resource.objects.create(place=pub, name="Zebra")
        Resource.objects.create(place=pub, name="Alpha")
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("resource-list"), {"ordering": "name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [
            row["name"]
            for row in list_results(response)
            if str(row["place"]) == str(pub.pk)
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
        ids = {str(row["id"]) for row in list_results(lr)}
        self.assertIn(str(res.pk), ids)
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


class ReservationAPITests(APITestCase):
    def _iso_utc(self, year, month, day, hour, minute=0):
        return (
            datetime(year, month, day, hour, minute, 0, tzinfo=dt_timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def setUp(self):
        self.owner = User.objects.create_user(username="rsv-owner", password="pw")
        self.viewer = User.objects.create_user(username="rsv-viewer", password="pw")
        self.other = User.objects.create_user(username="rsv-other", password="pw")
        self.client.force_authenticate(user=self.owner)
        pr = self.client.post(
            reverse("place-list"),
            {"name": "RsvPlace", "public": False},
            format="json",
        )
        self.assertEqual(pr.status_code, status.HTTP_201_CREATED)
        self.place = Place.objects.get(pk=pr.data["id"])
        rr = self.client.post(
            reverse("resource-list"),
            {"place": str(self.place.pk), "name": "Room"},
            format="json",
        )
        self.assertEqual(rr.status_code, status.HTTP_201_CREATED)
        self.resource = Resource.objects.get(pk=rr.data["id"])
        assign_perm("booking.can_see", self.viewer, self.place)

    def test_viewer_with_can_see_creates_reservation(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 6, 1, 10),
                "ends_at": self._iso_utc(2026, 6, 1, 11),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["created_by"]), str(self.viewer.pk))

    def test_rejects_overlapping_reservation(self):
        self.client.force_authenticate(user=self.viewer)
        first = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 6, 1, 10),
                "ends_at": self._iso_utc(2026, 6, 1, 12),
            },
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 6, 1, 11),
                "ends_at": self._iso_utc(2026, 6, 1, 13),
            },
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_allows_back_to_back_reservations(self):
        self.client.force_authenticate(user=self.viewer)
        a = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 6, 2, 10),
                "ends_at": self._iso_utc(2026, 6, 2, 11),
            },
            format="json",
        )
        self.assertEqual(a.status_code, status.HTTP_201_CREATED)
        b = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 6, 2, 11),
                "ends_at": self._iso_utc(2026, 6, 2, 12),
            },
            format="json",
        )
        self.assertEqual(b.status_code, status.HTTP_201_CREATED)

    def test_creator_can_patch_not_other_viewer(self):
        self.client.force_authenticate(user=self.viewer)
        created = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 6, 3, 9),
                "ends_at": self._iso_utc(2026, 6, 3, 10),
            },
            format="json",
        )
        rid = created.data["id"]
        self.client.force_authenticate(user=self.viewer)
        ok = self.client.patch(
            reverse("reservation-detail", kwargs={"pk": rid}),
            {"ends_at": self._iso_utc(2026, 6, 3, 10, 30)},
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(user=self.other)
        denied = self.client.patch(
            reverse("reservation-detail", kwargs={"pk": rid}),
            {"ends_at": self._iso_utc(2026, 6, 3, 11)},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_patch_any_reservation(self):
        self.client.force_authenticate(user=self.viewer)
        created = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 6, 4, 9),
                "ends_at": self._iso_utc(2026, 6, 4, 10),
            },
            format="json",
        )
        rid = created.data["id"]
        self.client.force_authenticate(user=self.owner)
        ok = self.client.patch(
            reverse("reservation-detail", kwargs={"pk": rid}),
            {"ends_at": self._iso_utc(2026, 6, 4, 11)},
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)

    def test_rejects_naive_datetimes_on_create(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": "2026-06-05T10:00:00",
                "ends_at": "2026-06-05T11:00:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_overlap_window_filter(self):
        self.client.force_authenticate(user=self.viewer)
        self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 7, 1, 8),
                "ends_at": self._iso_utc(2026, 7, 1, 9),
            },
            format="json",
        )
        mid = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 7, 1, 10),
                "ends_at": self._iso_utc(2026, 7, 1, 12),
            },
            format="json",
        )
        self.assertEqual(mid.status_code, status.HTTP_201_CREATED)
        mid_id = mid.data["id"]
        response = self.client.get(
            reverse("reservation-list"),
            {
                "overlap_start": self._iso_utc(2026, 7, 1, 10, 30),
                "overlap_end": self._iso_utc(2026, 7, 1, 11, 30),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {str(r["id"]) for r in list_results(response)}
        self.assertEqual(ids, {mid_id})

    def test_overlap_filter_with_only_overlap_start_returns_200(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(
            reverse("reservation-list"),
            {"overlap_start": self._iso_utc(2026, 7, 1, 0)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_overlap_query_accepts_naive_datetime(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(
            reverse("reservation-list"),
            {
                "overlap_start": "2026-07-01T10:30:00",
                "overlap_end": self._iso_utc(2026, 7, 1, 11, 30),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_create_reservation(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 8, 1, 10),
                "ends_at": self._iso_utc(2026, 8, 1, 11),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_lists_reservations_on_public_place_only(self):
        pub = Place.objects.create(name="PubRsv", public=True)
        res_pub = Resource.objects.create(place=pub, name="PubRes")
        self.client.force_authenticate(user=self.owner)
        self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(res_pub.pk),
                "starts_at": self._iso_utc(2026, 9, 1, 10),
                "ends_at": self._iso_utc(2026, 9, 1, 11),
            },
            format="json",
        )
        self.client.post(
            reverse("reservation-list"),
            {
                "resource": str(self.resource.pk),
                "starts_at": self._iso_utc(2026, 9, 2, 10),
                "ends_at": self._iso_utc(2026, 9, 2, 11),
            },
            format="json",
        )
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("reservation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {str(r["resource"]) for r in list_results(response)}
        self.assertIn(str(res_pub.pk), ids)
        self.assertNotIn(str(self.resource.pk), ids)
