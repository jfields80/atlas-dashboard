from services.connectors.base_connector import BaseConnector


class YelpConnector(BaseConnector):

    def search(
        self,
        search_term,
        location,
        max_results=100
    ):

        print(f"[YELP] Searching {search_term} in {location}")

        businesses = []

        for i in range(1, 6):

            businesses.append({

                "name": f"{search_term} Yelp {i}",
                "category": search_term,
                "city": location,
                "state": "",
                "phone": "",
                "website": "",
                "status": "Found via Yelp"

            })

        return businesses