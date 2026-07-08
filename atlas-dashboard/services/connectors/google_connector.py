import json
import os
import urllib.error
import urllib.request

from services.connectors.base_connector import BaseConnector


class GoogleConnector(BaseConnector):

    SEARCH_URL = (
        "https://places.googleapis.com/v1/"
        "places:searchText"
    )

    def __init__(self):
        super().__init__()

        self.api_key = os.environ.get(
            "GOOGLE_PLACES_API_KEY",
            ""
        ).strip()

    @staticmethod
    def clean_text(value):
        if value is None:
            return ""

        return " ".join(
            str(value).strip().split()
        )

    @staticmethod
    def extract_location(place, fallback_location):
        address_components = place.get(
            "addressComponents",
            []
        )

        city = ""
        state = ""

        city_types = {
            "locality",
            "postal_town",
            "administrative_area_level_2"
        }

        for component in address_components:
            types = set(
                component.get("types", [])
            )

            if not city and types.intersection(
                city_types
            ):
                city = component.get(
                    "longText",
                    ""
                )

            if (
                "administrative_area_level_1"
                in types
            ):
                state = component.get(
                    "shortText",
                    ""
                )

        if not city:
            city = fallback_location

        return city, state

    def build_request(
        self,
        search_term,
        location,
        max_results
    ):
        text_query = (
            f"{search_term} in {location}"
        )

        payload = {
            "textQuery": text_query,
            "pageSize": min(
                max(int(max_results), 1),
                20
            )
        }

        request_data = json.dumps(
            payload
        ).encode("utf-8")

        field_mask = ",".join(
            [
                "places.id",
                "places.displayName",
                "places.formattedAddress",
                "places.addressComponents",
                "places.nationalPhoneNumber",
                "places.websiteUri",
                "places.googleMapsUri",
                "places.businessStatus"
            ]
        )

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask
        }

        return urllib.request.Request(
            self.SEARCH_URL,
            data=request_data,
            headers=headers,
            method="POST"
        )

    def search(
        self,
        search_term,
        location,
        max_results=20
    ):
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_PLACES_API_KEY is not loaded."
            )

        search_term = self.clean_text(
            search_term
        )

        location = self.clean_text(
            location
        )

        if not search_term:
            raise ValueError(
                "A search term is required."
            )

        if not location:
            raise ValueError(
                "A location is required."
            )

        print(
            f"[GOOGLE] Searching "
            f"{search_term} in {location}"
        )

        request = self.build_request(
            search_term,
            location,
            max_results
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:
                response_body = (
                    response
                    .read()
                    .decode("utf-8")
                )

        except urllib.error.HTTPError as error:
            error_body = (
                error.read().decode(
                    "utf-8",
                    errors="replace"
                )
            )

            raise RuntimeError(
                f"Google Places returned "
                f"HTTP {error.code}: "
                f"{error_body}"
            ) from error

        except urllib.error.URLError as error:
            raise RuntimeError(
                "Google Places could not be reached: "
                f"{error.reason}"
            ) from error

        result = json.loads(
            response_body
        )

        businesses = []

        for place in result.get(
            "places",
            []
        ):
            display_name = place.get(
                "displayName",
                {}
            )

            business_name = (
                display_name.get(
                    "text",
                    ""
                )
            )

            business_name = self.clean_text(
                business_name
            )

            if not business_name:
                continue

            city, state = (
                self.extract_location(
                    place,
                    location
                )
            )

            phone = self.clean_text(
                place.get(
                    "nationalPhoneNumber",
                    ""
                )
            )

            website = self.clean_text(
                place.get(
                    "websiteUri",
                    ""
                )
            )

            if not website:
                website = self.clean_text(
                    place.get(
                        "googleMapsUri",
                        ""
                    )
                )

            business_status = place.get(
                "businessStatus",
                ""
            )

            if business_status:
                status = (
                    "Found via Google - "
                    f"{business_status}"
                )
            else:
                status = "Found via Google"

            businesses.append(
                {
                    "name": business_name,
                    "category": search_term,
                    "city": self.clean_text(
                        city
                    ),
                    "state": self.clean_text(
                        state
                    ),
                    "phone": phone,
                    "website": website,
                    "status": status
                }
            )

        print(
            f"[GOOGLE] Found "
            f"{len(businesses)} businesses"
        )

        return businesses