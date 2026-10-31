"""External media transport replacements shared by every Product browser server."""

import httpx

from backend.app.product.media import MediaProviders, get_media_providers


def media_transport(request):
    if request.url.host == "api.unsplash.com":
        if request.url.path == "/search/photos":
            query = request.url.params.get("query", "")
            if query in {
                "No photo venue Melbourne",
                "Chicamocha Melbourne",
                "Photo-empty city",
            } or query.endswith(" Photo-empty city"):
                return httpx.Response(200, json={"results": []})
            identity = {
                "Federation Square Melbourne": "square-fallback",
                "Melbourne": "city-fallback",
            }.get(query, "supporting-first")
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": identity,
                            "urls": {
                                "raw": f"https://images.unsplash.com/{identity}?ixid=controlled"
                            },
                            "links": {
                                "html": f"https://unsplash.com/photos/{identity}",
                                "download_location": f"https://api.unsplash.com/photos/{identity}/download?ixid=controlled",
                            },
                            "user": {
                                "name": "Supporting Photographer",
                                "links": {"html": "https://unsplash.com/@supporting"},
                            },
                        }
                    ]
                },
            )
        if request.url.path.endswith("/download"):
            return httpx.Response(
                200, json={"url": "https://images.unsplash.com/controlled-supporting"}
            )
        photo_id = request.url.path.rsplit("/", 1)[-1]
        sydney = photo_id == "7Zb7kUyQg1E"
        return httpx.Response(
            200,
            json={
                "id": photo_id,
                "urls": {
                    "raw": f"https://images.unsplash.com/controlled-{photo_id}?ixid=controlled-tracking"
                },
                "links": {"html": f"https://unsplash.com/photos/{photo_id}"},
                "user": {
                    "name": "Dan Freeman" if sydney else "Urban Vintage",
                    "links": {
                        "html": "https://unsplash.com/@danfreemanphoto"
                        if sydney
                        else "https://unsplash.com/@urban_vintage"
                    },
                },
            },
        )
    if request.url.host == "places.googleapis.com":
        if request.url.path.endswith("/media"):
            return httpx.Response(
                200, json={"photoUri": "https://lh3.googleusercontent.com/controlled-place"}
            )
        place = request.url.path.rsplit("/", 1)[-1]
        if place in {"no-photo-square", "no-photo-cafe", "no-photo-empty"}:
            return httpx.Response(200, json={"photos": []})
        return httpx.Response(
            200,
            json={
                "photos": [
                    {
                        "name": f"places/{place}/photos/controlled",
                        "googleMapsUri": "https://www.google.com/maps/place/?q=controlled-photo",
                        "authorAttributions": [
                            {
                                "displayName": "Controlled Photographer",
                                "uri": "https://www.google.com/maps/contrib/123",
                            }
                        ],
                    }
                ]
            },
        )
    raise AssertionError("Unexpected external media destination")


def replace_media(application):
    # The actual adapter remains under test; only its external HTTP transport changes.
    application.dependency_overrides[get_media_providers] = lambda: MediaProviders(
        google_key="controlled-google-key",
        unsplash_key="controlled-unsplash-key",
        transport=httpx.MockTransport(media_transport),
    )
